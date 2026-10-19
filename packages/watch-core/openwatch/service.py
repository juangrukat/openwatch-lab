"""Validated desktop commands, explicit device selection and local history."""

import asyncio
import base64
import binascii
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bleak import BleakScanner
from bleak.backends.device import BLEDevice

from . import protocol as p
from .adapters.moyoung import MoyoungAdapter
from .background import IMAGE_BYTES, upload
from .capabilities import CAPABILITIES, match_adapter
from .errors import WatchError
from .store import Store
from .transport import BleTransport

Emitter = Callable[[str, dict[str, Any]], None]


def integer(args: dict[str, Any], key: str) -> int:
    """Reject booleans/floats/strings at the command boundary."""
    value = args.get(key)
    if type(value) is not int:
        raise ValueError(f"{key} must be an integer")
    return value


def text(args: dict[str, Any], key: str) -> str:
    """Accept only bounded strings from the desktop bridge."""
    value = args.get(key)
    if not isinstance(value, str) or len(value) > 1000:
        raise ValueError(f"{key} must be a string of at most 1000 characters")
    return value


class Service:
    """One selected watch and one isolated database; no account or networking."""

    def __init__(self, path: Path, emit: Emitter) -> None:
        self.store = Store(path)
        self.emit = emit
        self.transport: BleTransport | None = None
        self.adapter: MoyoungAdapter | None = None
        self.scanned: dict[str, BLEDevice] = {}
        self.state: dict[str, Any] = {
            "connected": False,
            "demo": False,
            "device": None,
            "info": {},
            "settings": {},
            "alarms": [],
            "capabilities": [],
            "services": [],
        }
        self.logs: list[dict[str, Any]] = []
        self.device_id: str | None = None
        self.lifecycle = asyncio.Lock()
        self.closed = False
        self.background_task: asyncio.Task[None] | None = None
        self.background_bytes = bytearray()
        self.background_part = 0

    def snapshot(self) -> dict[str, Any]:
        """Return state through serialization, not shared mutable objects."""
        return {
            **self.state,
            "known_devices": self.store.devices(),
            "storage_path": str(self.store.path),
        }

    def publish(self) -> None:
        """Push the latest state to every local UI subscriber."""
        self.emit("state", self.snapshot())

    def event(self, kind: str, data: dict[str, Any]) -> None:
        """Process adapter events without attributing history as live data."""
        if kind == "packet":
            entry = {**data, "time": datetime.now(UTC).isoformat()}
            self.logs.append(entry)
            del self.logs[:-200]
        elif kind == "disconnected":
            self.state.update(connected=False, measurement=None, heart_rate=None)
            self.publish()
        elif kind == "heart_rate":
            self.state["heart_rate"] = {
                **data,
                "received_at": datetime.now(UTC).isoformat(),
            }
            self.publish()
        elif kind == "activity":
            self.state["activity"] = data
            self.publish()
        elif kind == "background":
            self.state["background"] = data
            self.publish()
        elif kind == "measurement":
            self.state["measurement"] = data.get("kind")
            self.publish()
        elif kind == "warning":
            self.state["warning"] = data.get("message")
        self.emit(kind, data)

    async def scan(self) -> list[dict[str, Any]]:
        """Scan without selecting or connecting to anything automatically."""
        found = await BleakScanner.discover(timeout=5, return_adv=True)
        result: list[dict[str, Any]] = []
        self.scanned.clear()
        for device, adv in found.values():
            name = adv.local_name or device.name or "Unnamed Bluetooth device"
            adapter = match_adapter(name, adv.service_uuids, adv.manufacturer_data)
            self.scanned[device.address] = device
            result.append(
                {
                    "id": device.address,
                    "name": name,
                    "rssi": adv.rssi,
                    "adapter": adapter,
                    "supported": adapter is not None,
                }
            )
        return sorted(result, key=lambda item: (not item["supported"], -item["rssi"]))

    async def disconnect(self) -> None:
        """Close the current session and clear ephemeral connection state."""
        await self.cancel_background()
        self.background_bytes.clear()
        adapter, transport = self.adapter, self.transport
        self.adapter = None
        self.transport = None
        try:
            if adapter:
                await adapter.close()
            elif transport:
                await transport.close()
        finally:
            self.state.update(
                connected=False, demo=False, measurement=None, heart_rate=None
            )
            self.publish()

    async def connect(self, address: str) -> dict[str, Any]:
        """Connect only to a scan result or a previously explicitly chosen device."""
        async with self.lifecycle:
            known = {item["id"]: item for item in self.store.devices()}
            if address not in self.scanned and address not in known:
                raise ValueError("Scan and select a device before connecting")
            await self.disconnect()
            self.state = {
                "connected": False,
                "demo": False,
                "device": None,
                "info": {},
                "settings": {},
                "alarms": [],
                "capabilities": [],
                "services": [],
            }
            device = self.scanned.get(address)
            name = (
                device.name if device else known[address]["name"]
            ) or "Selected watch"
            loop = asyncio.get_running_loop()

            def disconnected() -> None:
                loop.call_soon_threadsafe(self.on_disconnect)

            transport = BleTransport(device or address, disconnected)
            self.transport = transport
            try:
                await transport.connect()
                try:
                    manufacturer = (
                        (await transport.read(p.uuid("2a29")))
                        .decode(errors="replace")
                        .strip("\0")
                    )
                except Exception:
                    manufacturer = "Unavailable"
                services = [
                    {
                        "uuid": service.uuid,
                        "characteristics": [
                            {"uuid": char.uuid, "properties": char.properties}
                            for char in service.characteristics
                        ],
                    }
                    for service in transport.client.services
                ]
                self.state.update(
                    info={"manufacturer": manufacturer},
                    services=services,
                    device={"id": address, "name": name},
                )
                # Manufacturer alone cannot grant writes to an unknown model.
                recognized = "o20" in name.lower() and manufacturer == "MOYOUNG-V2"
                if recognized:
                    self.adapter = MoyoungAdapter(transport, self.event)
                    self.state["info"] = await self.adapter.initialize()
                    self.state["adapter"] = self.adapter.id
                    self.state["capabilities"] = CAPABILITIES
                    self.state["profile_verified"] = (
                        self.adapter.info.get("software") == "O20-7LH2-2.1.12"
                    )
                    self.store.remember(address, name, self.adapter.id)
                else:
                    self.state["adapter"] = None
                    self.state["profile_verified"] = False
                self.device_id = address
                self.state["connected"] = True
                self.publish()
                if self.adapter:
                    await self.refresh()
                return self.snapshot()
            except Exception:
                await self.disconnect()
                raise

    def on_disconnect(self) -> None:
        """Handle OS callbacks on the asyncio owner thread."""
        if self.adapter:
            self.adapter.disconnected()
        else:
            self.state.update(connected=False, measurement=None, heart_rate=None)
            self.publish()

    def require_adapter(self, write: bool = False) -> MoyoungAdapter:
        """Fail closed for demo, unknown models and unvalidated firmware writes."""
        if self.state.get("demo"):
            raise WatchError("Demo is read-only. Connect your watch to use controls")
        if not self.adapter or not self.state.get("connected"):
            raise WatchError("Connect a supported O20 first")
        if write and not self.state.get("profile_verified"):
            raise WatchError(
                "Unvalidated firmware: writes disabled. Inspect it in Device lab"
            )
        return self.adapter

    async def refresh(self) -> dict[str, Any]:
        """Refresh real watch state; no settings are automatically written."""
        adapter = self.require_adapter()
        values = await adapter.refresh()
        self.state.update(values)
        self.publish()
        return self.snapshot()

    async def sync(self) -> dict[str, Any]:
        """Fetch history and deduplicate by device/source identity, not sample value."""
        adapter = self.require_adapter()
        result = await adapter.history()
        assert self.device_id is not None
        for record in result["records"]:
            kind = str(record["kind"])
            key = f"{record['source_time']}:{record.get('slot', '')}"
            self.store.put(self.device_id, kind, key, record)
        self.emit("history_changed", {})
        return {"fetched": len(result["records"]), "warnings": result["warnings"]}

    async def demo(self) -> dict[str, Any]:
        """Explicit synthetic preview. Nothing is inserted into the real database."""
        await self.disconnect()
        self.device_id = None
        self.state = {
            "connected": False,
            "demo": True,
            "device": {"id": "synthetic-preview", "name": "Synthetic O20 preview"},
            "info": {"manufacturer": "Synthetic", "software": "Preview only"},
            "adapter": "moyoung-o20",
            "profile_verified": False,
            "battery": {"percent": 76, "charging": False},
            "activity": {"steps": 2846, "distance_raw": 1900, "calories_raw": 92},
            "heart_rate": {"bpm": 72, "origin": "synthetic"},
            "settings": {
                "goal": 6000,
                "language": 0,
                "time_format": 1,
                "units": 0,
                "raise_wrist": 1,
                "sedentary": 0,
                "watch_face": 2,
            },
            "alarms": [],
            "services": [],
            "capabilities": CAPABILITIES,
        }
        self.publish()
        return self.snapshot()

    def history(self) -> list[dict[str, Any]]:
        """Return explicit synthetic records only while preview mode is active."""
        if self.state.get("demo"):
            return [
                {
                    "id": index,
                    "kind": kind,
                    "received_at": "2024-01-02T08:00:00Z",
                    "data": {
                        "kind": kind,
                        "value": value,
                        "time": "2024-01-02T16:00:00+08:00",
                        "origin": "synthetic",
                    },
                    "device": "synthetic-preview",
                }
                for index, (kind, value) in enumerate((("oxygen", 98), ("stress", 31)))
            ]
        return self.store.history(self.device_id)

    def background_active(self) -> bool:
        """Keep other watch operations out of the transfer channel."""
        return self.background_task is not None and not self.background_task.done()

    async def cancel_background(self) -> None:
        """Cancel cooperatively and wait for the protocol abort/cleanup."""
        if self.background_active():
            assert self.background_task is not None
            self.background_task.cancel()
            try:
                await self.background_task
            except asyncio.CancelledError:
                self.event(
                    "background",
                    {"status": "cancelled", "message": "Background upload cancelled."},
                )
        self.background_bytes.clear()
        self.background_part = 0

    async def run_background(self, adapter: MoyoungAdapter, image: bytes) -> None:
        """Publish terminal status without leaking task exceptions."""
        try:
            await upload(adapter, image)
        except asyncio.CancelledError:
            self.event(
                "background",
                {"status": "cancelled", "message": "Background upload cancelled."},
            )
        except Exception as exc:
            self.event(
                "background",
                {
                    "status": "error",
                    "message": str(exc) or "Background upload timed out.",
                },
            )

    async def command(self, name: str, args: dict[str, Any]) -> Any:
        """Dispatch a narrow, explicit RPC surface; no raw write or filesystem paths."""
        if self.closed:
            raise WatchError("Backend is shutting down")
        if self.background_active() and name not in (
            "state",
            "history",
            "packets",
            "export",
            "background_cancel",
            "disconnect",
        ):
            raise WatchError("Finish or cancel the background upload first")
        if name == "background_cancel":
            await self.cancel_background()
            return {"cancelled": True}
        if name == "background_stage":
            self.require_adapter(True)
            part = integer(args, "part")
            raw = args.get("data")
            if not isinstance(raw, str) or len(raw) > 5500:
                raise ValueError("Invalid background piece")
            try:
                decoded = base64.b64decode(raw, validate=True)
            except (ValueError, binascii.Error) as exc:
                raise ValueError("Invalid background encoding") from exc
            if not decoded or len(decoded) > 4096:
                raise ValueError("Invalid background piece size")
            if part == 0:
                self.background_bytes.clear()
                self.background_part = 0
            if (
                part != self.background_part
                or len(self.background_bytes) + len(decoded) > IMAGE_BYTES
            ):
                raise ValueError("Background pieces are out of order or too large")
            self.background_bytes.extend(decoded)
            self.background_part += 1
            return {"received": len(self.background_bytes)}
        if name == "background_start":
            adapter = self.require_adapter(True)
            if len(self.background_bytes) != IMAGE_BYTES:
                raise ValueError("Incomplete background image")
            image = bytes(self.background_bytes)
            self.background_bytes.clear()
            self.background_part = 0
            self.state["background"] = {
                "status": "uploading",
                "transferred": 0,
                "total": IMAGE_BYTES,
                "message": "Preparing watch…",
            }
            self.publish()
            self.background_task = asyncio.create_task(
                self.run_background(adapter, image)
            )
            return {"started": True}
        if name == "state":
            return self.snapshot()
        if name == "scan":
            return await self.scan()
        if name == "connect":
            return await self.connect(text(args, "id"))
        if name == "disconnect":
            await self.disconnect()
            return self.snapshot()
        if name == "demo":
            return await self.demo()
        if name == "refresh":
            return await self.refresh()
        if name == "sync":
            return await self.sync()
        if name == "history":
            return self.history()
        if name == "packets":
            return self.logs
        if name == "export":
            return {"schema": "openwatch.observations.v1", "records": self.history()}
        if name == "set_setting":
            result = await self.require_adapter(True).set_setting(
                text(args, "name"), integer(args, "value")
            )
            await self.refresh()
            return result
        if name == "set_alarm":
            enabled = args.get("enabled")
            clear = args.get("clear", False)
            if not isinstance(enabled, bool) or not isinstance(clear, bool):
                raise ValueError("Alarm enabled/clear must be booleans")
            result = await self.require_adapter(True).set_alarm(
                integer(args, "slot"),
                enabled,
                integer(args, "hour"),
                integer(args, "minute"),
                integer(args, "weekdays"),
                clear,
            )
            self.state["alarms"] = result["alarms"]
            self.publish()
            return result
        if name == "measure":
            kind = args.get("kind")
            if kind is not None and not isinstance(kind, str):
                raise ValueError("Invalid measurement")
            return await self.require_adapter(True).measure(kind)
        if name == "notify":
            return await self.require_adapter(True).notify(text(args, "text"))
        if name == "find":
            return await self.require_adapter(True).find()
        raise ValueError(f"Unknown command: {name}")

    async def close(self) -> None:
        """Stop measurements and close the database exactly once."""
        if not self.closed:
            self.closed = True
            await self.disconnect()
            self.store.close()

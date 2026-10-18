"""Moyoung V2 adapter: bounded, verified O20 operations and explicit gaps."""

import asyncio
from collections.abc import Callable
from dataclasses import replace
from typing import Any

from .. import protocol as p
from ..capabilities import CAPABILITIES
from ..errors import ProtocolError, WatchError
from ..transport import Transport

Event = Callable[[str, dict[str, Any]], None]
Matcher = Callable[[bytes], bool]


def slot_match(subtype: int, slot: int) -> Matcher:
    """Bind a slot before asynchronous replies arrive."""

    def matches(data: bytes) -> bool:
        return data[:2] == bytes((subtype, slot))

    return matches


class MoyoungAdapter:
    """Map device bytes to common state without importing any vendor SDK."""

    id = "moyoung-o20"

    def __init__(self, transport: Transport, event: Event) -> None:
        self.transport = transport
        self.event = event
        self.decoder = p.FrameDecoder()
        self.lock = asyncio.Lock()
        self.operation_lock = asyncio.Lock()
        self.pending: tuple[int, Matcher, asyncio.Future[bytes]] | None = None
        self.measurement: str | None = None
        self.closed = False
        self.info: dict[str, str] = {}

    async def initialize(self) -> dict[str, str]:
        """Validate the manufacturer before enabling vendor operations."""
        self.info["manufacturer"] = (
            (await self.transport.read(p.uuid("2a29")))
            .decode(errors="replace")
            .strip("\0")
        )
        if self.info["manufacturer"] != "MOYOUNG-V2":
            raise WatchError(
                "This is not a validated MOYOUNG-V2 profile; writes disabled"
            )
        for short, field in (("2a26", "firmware"), ("2a28", "software")):
            self.info[field] = (
                (await self.transport.read(p.uuid(short)))
                .decode(errors="replace")
                .strip("\0")
            )
        await self.transport.subscribe(p.uuid("fee3"), self.receive)
        await self.transport.subscribe(p.uuid("2a37"), self.receive_heart)
        await self.transport.subscribe(p.uuid("fee1"), self.receive_activity)
        return self.info

    def disconnected(self) -> None:
        """Fail outstanding work immediately when a device disappears."""
        self.closed = True
        self.measurement = None
        self.decoder.clear()
        if self.pending and not self.pending[2].done():
            self.pending[2].set_exception(
                WatchError("Watch disconnected during operation")
            )
        self.event("disconnected", {})

    def receive_heart(self, data: bytes) -> None:
        """Decode live values separately from stored history."""
        try:
            value = p.heart_rate(data)
            if value is not None:
                self.event("heart_rate", {"bpm": value, "origin": "live"})
        except ProtocolError as exc:
            self.event("warning", {"message": str(exc)})

    def receive_activity(self, data: bytes) -> None:
        """Publish current totals without treating them as workout totals."""
        try:
            self.event("activity", p.activity(data))
        except ProtocolError as exc:
            self.event("warning", {"message": str(exc)})

    def receive(self, data: bytes) -> None:
        """Feed notifications to the pending request and independent events."""
        self.event("packet", {"direction": "rx", "hex": data.hex()})
        for frame in self.decoder.feed(data):
            if self.pending:
                command, matcher, future = self.pending
                if (
                    frame.command == command
                    and matcher(frame.payload)
                    and not future.done()
                ):
                    future.set_result(frame.payload)
            if frame.command == 0x6B and len(frame.payload) == 1:
                value = frame.payload[0]
                if 0 < value <= 100:
                    self.event(
                        "oxygen_live", {"value": value, "origin": "live-unverified"}
                    )
                elif value == 255:
                    self.measurement = None
                    self.event(
                        "measurement",
                        {
                            "kind": None,
                            "message": "Oxygen ended; fresh numeric value unverified",
                        },
                    )
            if frame.command == 0x62:
                self.event("find_phone", {"message": "Watch requested this computer"})

    async def send(self, command: int, payload: bytes = b"") -> None:
        """Send only commands selected by validated public operations."""
        if self.closed or not self.transport.connected:
            raise WatchError("Connect a watch first")
        value = p.encode(command, payload)
        self.event("packet", {"direction": "tx", "hex": value.hex()})
        await self.transport.write(p.uuid("fee2"), value)

    async def query(
        self,
        command: int,
        payload: bytes = b"",
        matcher: Matcher | None = None,
        response_seconds: float = 5,
    ) -> bytes:
        """Single-flight requests with subtype/slot correlation and bounded timeout."""
        async with self.lock:
            if self.closed:
                raise WatchError("Watch disconnected")
            future: asyncio.Future[bytes] = asyncio.get_running_loop().create_future()
            self.pending = (command, matcher or (lambda _: True), future)
            try:
                await self.send(command, payload)
                return await asyncio.wait_for(future, response_seconds)
            except TimeoutError as exc:
                # No transaction IDs exist. Drain late replies before the next query.
                self.pending = None
                await asyncio.sleep(0.25)
                raise WatchError(
                    f"Watch did not answer command 0x{command:02X}"
                ) from exc
            finally:
                self.pending = None

    async def read_settings(self) -> dict[str, Any]:
        """Read supported settings individually, retaining incomplete capabilities."""
        result: dict[str, Any] = {"errors": []}
        queries = (
            ("goal", 0x26),
            ("time_format", 0x27),
            ("units", 0x2A),
            ("language", 0x2B),
            ("raise_wrist", 0x28),
            ("sedentary", 0x2D),
            ("watch_face", 0x29),
        )
        for name, command in queries:
            try:
                value = await self.query(command)
                if name == "goal":
                    p.require_size(value, 4, "Step goal")
                    result[name] = int.from_bytes(value, "little")
                elif name == "language":
                    if not value:
                        raise ProtocolError("Missing language value")
                    result[name] = value[0]
                    result["language_extension_raw"] = value[1:].hex()
                else:
                    p.require_size(value, 1, name)
                    result[name] = value[0]
            except WatchError as exc:
                result["errors"].append(str(exc))
        return result

    async def read_alarms(self) -> list[dict[str, Any]]:
        """Read all slots so writes can preserve unrelated alarms."""
        return [
            alarm.public(i) for i, alarm in enumerate(p.alarms(await self.query(0x21)))
        ]

    async def refresh(self) -> dict[str, Any]:
        """Read actual values without applying companion-app initialization writes."""
        async with self.operation_lock:
            result: dict[str, Any] = {"info": self.info, "capabilities": CAPABILITIES}
            result["battery"] = p.battery(await self.transport.read(p.uuid("2a19")))
            result["activity"] = p.activity(await self.transport.read(p.uuid("fee1")))
            result["settings"] = await self.read_settings()
            result["alarms"] = await self.read_alarms()
            return result

    async def set_setting(self, name: str, value: int) -> dict[str, Any]:
        """Snapshot, change, read back, and attempt rollback on a mismatch."""
        commands = {
            "goal": (0x26, 0x16),
            "time_format": (0x27, 0x17),
            "units": (0x2A, 0x1A),
            "language": (0x2B, 0x1B),
            "raise_wrist": (0x28, 0x18),
            "sedentary": (0x2D, 0x1D),
            "watch_face": (0x29, 0x19),
        }
        if name not in commands:
            raise ValueError("Unsupported setting")
        if name == "goal" and not 100 <= value <= 100000:
            raise ValueError("Step goal must be 100–100,000")
        if name == "language" and not 0 <= value <= 24:
            raise ValueError("Unsupported language code")
        if name == "watch_face" and value not in (2, 3):
            raise ValueError("Only built-in faces 2 and 3 have been validated")
        if name not in ("goal", "language", "watch_face") and value not in (0, 1):
            raise ValueError("Setting must be 0 or 1")
        query, setter = commands[name]
        async with self.operation_lock:
            before = await self.query(query)
            if not before or (name == "goal" and len(before) != 4):
                raise ProtocolError("Cannot snapshot setting; no write was sent")
            old = int.from_bytes(before, "little") if name == "goal" else before[0]
            payload = value.to_bytes(4, "big") if name == "goal" else bytes((value,))
            await self.send(setter, payload)
            await asyncio.sleep(0.2)
            try:
                after = await self.query(query)
                actual = (
                    int.from_bytes(after, "little")
                    if name == "goal"
                    else after[0] if after else None
                )
                if actual != value:
                    raise WatchError(
                        f"Readback mismatch: requested {value}, received {actual}"
                    )
            except (WatchError, IndexError) as exc:
                restore = old.to_bytes(4, "big") if name == "goal" else bytes((old,))
                try:
                    await self.send(setter, restore)
                    restored = await self.query(query)
                    if (restored if name == "goal" else restored[:1]) != (
                        before if name == "goal" else before[:1]
                    ):
                        raise WatchError(
                            "Rollback readback did not match the original value"
                        )
                except WatchError as rollback:
                    raise WatchError(
                        f"{exc}. Restore could not be verified: {rollback}"
                    ) from exc
                raise WatchError(f"{exc}. Original value restored") from exc
            return {"name": name, "value": value, "previous": old, "verified": True}

    async def set_alarm(
        self,
        slot: int,
        enabled: bool,
        hour: int,
        minute: int,
        weekdays: int,
        clear: bool = False,
    ) -> dict[str, Any]:
        """Edit/clear only one legacy slot, verifying the whole list afterward."""
        if slot not in (0, 1, 2):
            raise ValueError("Choose alarm slot 0–2")
        if not clear and weekdays == 0:
            raise ValueError(
                "Choose at least one repeat day; dated one-shot alarms are unverified"
            )
        async with self.operation_lock:
            original = await self.query(0x21)
            slots = p.alarms(original)
            old = original[slot * 8 : slot * 8 + 8]
            target = (
                p.Alarm(slot, False, 0, 0, 0, b"\0\0", 0)
                if clear
                else replace(
                    slots[slot],
                    slot=slot,
                    enabled=enabled,
                    hour=hour,
                    minute=minute,
                    weekdays=weekdays,
                    repeat_mode=1 if weekdays == 127 else 2,
                )
            )
            payload = target.encode()
            await self.send(0x11, payload)
            await asyncio.sleep(0.2)
            try:
                current = await self.query(0x21)
                p.alarms(current)
                if (
                    current[: slot * 8] != original[: slot * 8]
                    or current[(slot + 1) * 8 :] != original[(slot + 1) * 8 :]
                ):
                    raise WatchError(
                        "An unrelated alarm slot changed; inspect the device"
                    )
                actual = p.Alarm.decode(current[slot * 8 : slot * 8 + 8])
                if (actual.enabled, actual.hour, actual.minute, actual.weekdays) != (
                    target.enabled,
                    target.hour,
                    target.minute,
                    target.weekdays,
                ):
                    raise WatchError(
                        "Alarm readback did not match the requested values"
                    )
            except WatchError as exc:
                await self.send(0x11, old)
                restored = await self.query(0x21)
                if restored != original:
                    raise WatchError(
                        f"{exc}; original alarm list restoration could not be verified"
                    ) from exc
                raise WatchError(f"{exc}; original alarm restored") from exc
            return {"slot": slot, "verified": True, "alarms": await self.read_alarms()}

    async def history(self) -> dict[str, Any]:
        """Fetch validated manual records and candidate workout layouts."""
        async with self.operation_lock:
            oxygen = p.manual_records(
                "oxygen",
                await self.query(0xAB, b"\x02", lambda b: b.startswith(b"\x02")),
            )
            stress = p.manual_records(
                "stress",
                await self.query(
                    0xB9, b"\x11\x02", lambda b: b.startswith(b"\x11\x02")
                ),
            )
            records = oxygen + stress
            warnings: list[str] = []
            try:
                ids = p.workout_list(
                    await self.query(0xB2, b"\0", lambda b: b.startswith(b"\x01"))
                )
                for slot in ids:
                    detail = p.workout(
                        await self.query(
                            0xB2,
                            bytes((2, slot)),
                            slot_match(3, slot),
                        )
                    )
                    if detail:
                        try:
                            detail["heart_rate_page"] = p.workout_hr(
                                await self.query(
                                    0xB2,
                                    bytes((4, slot, 0, 0)),
                                    slot_match(5, slot),
                                ),
                                slot,
                            )
                        except WatchError as exc:
                            warnings.append(str(exc))
                        records.append(detail)
            except WatchError as exc:
                warnings.append(str(exc))
            return {"records": records, "warnings": warnings}

    async def measure(self, kind: str | None) -> dict[str, Any]:
        """Start/stop measurement; never relabel stored oxygen as a live result."""
        if kind not in (None, "heart_rate", "oxygen"):
            raise ValueError("Unsupported measurement")
        async with self.operation_lock:
            if self.measurement:
                await self.send(
                    0x6D if self.measurement == "heart_rate" else 0x6B, b"\xff"
                )
            self.measurement = kind
            if kind:
                await self.send(0x6D if kind == "heart_rate" else 0x6B, b"\0")
            self.event("measurement", {"kind": kind})
            return {"kind": kind}

    async def notify(self, text: str) -> dict[str, bool]:
        """Send a local watch message, not a real SMS or external communication."""
        raw = text.encode("utf-8")
        if not raw or len(raw) > 120:
            raise ValueError("Message must contain 1–120 UTF-8 bytes")
        async with self.operation_lock:
            await self.send(0x41, b"\x01" + raw)
        return {"sent": True, "delivery_verified": False}

    async def find(self) -> dict[str, bool]:
        """Trigger the user-validated audible signal; no acknowledgment is promised."""
        async with self.operation_lock:
            await self.send(0x61)
        return {"sent": True, "delivery_verified": False}

    async def close(self) -> None:
        """Best-effort measurement stop before disconnecting."""
        try:
            if self.measurement and self.transport.connected:
                await self.measure(None)
        finally:
            self.disconnected()
            await self.transport.close()

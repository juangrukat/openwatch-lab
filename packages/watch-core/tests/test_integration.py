"""Exercise the service boundary and sidecar using synthetic I/O only."""

import io
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from openwatch import server
from openwatch.errors import WatchError
from openwatch.service import Service
from openwatch.transport import BleTransport
from test_adapter import FakeTransport


async def test_service_routes_and_identity(tmp_path, monkeypatch):
    import openwatch.service as module

    fake = FakeTransport()
    fake.client = SimpleNamespace(services=[])
    fake.connect = AsyncMock()
    monkeypatch.setattr(module, "BleTransport", lambda *_: fake)
    device = SimpleNamespace(address="synthetic-id", name="itel ISW-O20")
    adv = SimpleNamespace(
        local_name=device.name,
        service_uuids=["0000fd35-0000-1000-8000-00805f9b34fb"],
        manufacturer_data={},
        rssi=-40,
    )
    monkeypatch.setattr(
        module.BleakScanner, "discover", AsyncMock(return_value={"x": (device, adv)})
    )
    s = Service(tmp_path / "local.sqlite3", lambda *_: None)
    assert (await s.command("scan", {}))[0]["supported"]
    assert (await s.command("connect", {"id": device.address}))["profile_verified"]
    assert (await s.command("refresh", {}))["connected"]
    assert (await s.command("sync", {}))["fetched"] == 3
    assert len(s.history()) == 3
    await s.command("sync", {})
    assert len(s.history()) == 3
    await s.command("set_setting", {"name": "goal", "value": 4500})
    await s.command(
        "set_alarm",
        {"slot": 0, "enabled": True, "hour": 1, "minute": 20, "weekdays": 1},
    )
    await s.command("measure", {"kind": "heart_rate"})
    await s.command("measure", {"kind": None})
    await s.command("notify", {"text": "Synthetic"})
    await s.command("find", {})
    s.state["profile_verified"] = False
    with pytest.raises(WatchError, match="Unvalidated"):
        await s.command("find", {})
    s.on_disconnect()
    await s.close()


async def test_unknown_device_inspection_and_connect_failure(tmp_path, monkeypatch):
    import openwatch.service as module

    fake = FakeTransport()
    fake.client = SimpleNamespace(
        services=[
            SimpleNamespace(
                uuid="synthetic-service",
                characteristics=[
                    SimpleNamespace(uuid="synthetic-char", properties=["read"])
                ],
            )
        ]
    )
    fake.connect = AsyncMock()
    fake.read = AsyncMock(side_effect=RuntimeError("No manufacturer"))
    monkeypatch.setattr(module, "BleTransport", lambda *_: fake)
    s = Service(tmp_path / "local.sqlite3", lambda *_: None)
    s.scanned["a"] = SimpleNamespace(name="Unknown")
    state = await s.connect("a")
    assert state["connected"] and state["adapter"] is None
    assert state["services"][0]["characteristics"][0]["properties"] == ["read"]
    with pytest.raises(WatchError):
        s.require_adapter()
    fake.connect = AsyncMock(side_effect=RuntimeError("Disconnected"))
    with pytest.raises(RuntimeError):
        await s.connect("a")
    assert not s.state["connected"]
    await s.close()


async def test_ble_transport_chunking_and_callbacks(monkeypatch):
    import openwatch.transport as module

    char = SimpleNamespace(max_write_without_response_size=3)
    client = SimpleNamespace(
        is_connected=True,
        connect=AsyncMock(),
        disconnect=AsyncMock(),
        read_gatt_char=AsyncMock(return_value=bytearray(b"abc")),
        start_notify=AsyncMock(),
        write_gatt_char=AsyncMock(),
        services=SimpleNamespace(get_characteristic=lambda _: char),
    )
    callbacks = []

    def factory(device, disconnected_callback):
        callbacks.append(disconnected_callback)
        return client

    monkeypatch.setattr(module, "BleakClient", factory)
    disconnected = []
    t = BleTransport("synthetic", lambda: disconnected.append(True))
    await t.connect()
    assert t.connected
    assert await t.read("x") == b"abc"
    received = []
    await t.subscribe("x", received.append)
    client.start_notify.call_args.args[1](None, bytearray(b"z"))
    assert received == [b"z"]
    await t.write("x", b"abcdefgh")
    assert [c.args[1] for c in client.write_gatt_char.call_args_list] == [
        b"abc",
        b"def",
        b"gh",
    ]
    callbacks[0](None)
    assert disconnected
    client.services.get_characteristic = lambda _: None
    with pytest.raises(WatchError):
        await t.write("x", b"abc")
    await t.close()
    client.disconnect.assert_awaited_once()
    client.is_connected = False
    await t.close()


async def test_sidecar_rejects_invalid_requests_and_closes(
    tmp_path, monkeypatch, capsys
):
    requests = [
        [],
        {"id": True, "command": "state"},
        {"id": 1, "command": 2},
        {"id": 2, "command": "unknown"},
        {"id": 3, "command": "demo"},
        {"id": 4, "command": "history"},
    ]
    source = "".join(json.dumps(x) + "\n" for x in requests) + "x" * 65537 + "\n"
    monkeypatch.setattr(server.sys, "stdin", io.StringIO(source))
    await server.run(tmp_path / "local.sqlite3")
    messages = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert messages[0]["event"] == "ready"
    assert len([x for x in messages if "error" in x]) >= 5
    assert (
        next(x for x in messages if x.get("id") == 4)["result"][0]["data"]["origin"]
        == "synthetic"
    )

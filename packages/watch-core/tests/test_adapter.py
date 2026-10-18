"""Fake BLE verifies command correlation, reversibility and missing values."""

import asyncio
import struct

import pytest

from openwatch.adapters.moyoung import MoyoungAdapter
from openwatch import protocol as p
from openwatch.errors import ProtocolError, WatchError


class FakeTransport:
    def __init__(self):
        self.connected = True
        self.receivers = {}
        self.settings = {
            0x26: (4000).to_bytes(4, "little"),
            0x27: b"\1",
            0x2A: b"\0",
            0x2B: b"\0\2",
            0x28: b"\1",
            0x2D: b"\0",
            0x29: b"\2",
        }
        self.slots = bytes(24)
        self.writes = []
        self.ignore = set()
        self.no_reply = set()
        self.manual_bad = False
        self.bad_workout = False
        self.manufacturer = b"MOYOUNG-V2"

    async def read(self, char):
        return {
            p.uuid("2a29"): self.manufacturer,
            p.uuid("2a26"): b"synthetic-firmware",
            p.uuid("2a28"): b"O20-7LH2-2.1.12",
            p.uuid("2a19"): bytes([70]),
            p.uuid("fee1"): bytes(9),
        }[char]

    async def subscribe(self, char, receiver):
        self.receivers[char] = receiver

    async def write(self, char, data):
        self.writes.append(data)
        cmd = data[4]
        body = data[5:]
        setters = {
            0x16: 0x26,
            0x17: 0x27,
            0x1A: 0x2A,
            0x1B: 0x2B,
            0x18: 0x28,
            0x1D: 0x2D,
            0x19: 0x29,
        }
        if cmd in self.ignore:
            return
        if cmd in setters:
            self.settings[setters[cmd]] = body[::-1] if cmd == 0x16 else body
            return
        if cmd == 0x11:
            i = body[0]
            self.slots = self.slots[: i * 8] + body + self.slots[(i + 1) * 8 :]
            return
        if cmd in self.no_reply:
            return
        response = None
        if cmd in self.settings:
            response = self.settings[cmd]
        elif cmd == 0x21:
            response = self.slots
        elif cmd == 0xAB:
            response = b"\x02\x01" + bytes([98]) + (1704153600).to_bytes(4, "little")
        elif cmd == 0xB9:
            response = (
                b"\x11\x02\x01" + bytes([32]) + (1704153600).to_bytes(4, "little")
            )
        elif cmd == 0xB2:
            if self.bad_workout:
                response = b"\x01"
            elif body == b"\0":
                a = bytearray(31)
                a[0] = 1
                a[1:5] = (1704153600).to_bytes(4, "little")
                response = bytes(a)
            elif body[0] == 2:
                a = bytearray(30)
                a[:2] = bytes([3, body[1]])
                struct.pack_into("<IIH", a, 2, 1704153600, 1704153720, 115)
                struct.pack_into("<I", a, 14, 123)
                response = bytes(a)
            else:
                response = bytes([5, body[1], 255, 255, 72, 74])
        if response is not None:
            # Wrong subtypes must not satisfy a request with a stricter matcher.
            if cmd == 0xB9:
                self.receivers[p.uuid("fee3")](p.encode(cmd, b"\x11\1\0"))
            self.receivers[p.uuid("fee3")](p.encode(cmd, response))

    async def close(self):
        self.connected = False


async def setup_adapter():
    transport = FakeTransport()
    events = []
    adapter = MoyoungAdapter(transport, lambda kind, data: events.append((kind, data)))
    await adapter.initialize()
    return adapter, transport, events


async def test_reads_settings_writes_and_alarms():
    a, t, _ = await setup_adapter()
    state = await a.refresh()
    assert state["settings"]["goal"] == 4000
    for name, value in [
        ("goal", 4100),
        ("language", 0),
        ("time_format", 0),
        ("units", 1),
        ("raise_wrist", 0),
        ("sedentary", 1),
        ("watch_face", 3),
    ]:
        result = await a.set_setting(name, value)
        assert result["verified"]
    assert (await a.set_alarm(1, True, 7, 35, 62))["alarms"][1]["minute"] == 35
    assert t.slots[:8] == bytes(8) and t.slots[16:] == bytes(8)
    assert (await a.set_alarm(1, False, 0, 0, 0, True))["alarms"][1]["empty"]
    for name, value in [
        ("unknown", 1),
        ("goal", 0),
        ("language", 255),
        ("watch_face", 7),
        ("units", 2),
    ]:
        with pytest.raises(ValueError):
            await a.set_setting(name, value)
    with pytest.raises(ValueError):
        await a.set_alarm(3, True, 7, 0, 1)
    with pytest.raises(ValueError):
        await a.set_alarm(0, True, 7, 0, 0)
    await a.close()
    assert not t.connected


async def test_history_events_and_measurement_boundaries():
    a, t, events = await setup_adapter()
    result = await a.history()
    assert [r["kind"] for r in result["records"]] == ["oxygen", "stress", "workout"]
    t.bad_workout = True
    assert (await a.history())["warnings"]
    a.receive_heart(b"\x06\x48")
    a.receive_heart(b"")
    a.receive_activity(bytes(9))
    a.receive_activity(b"")
    a.receive(p.encode(0x6B, b"\xff"))
    assert not any(kind == "oxygen_live" for kind, _ in events)
    a.receive(p.encode(0x6B, bytes([98])))
    assert any(kind == "oxygen_live" for kind, _ in events)
    a.receive(p.encode(0x62, b"\0"))
    assert events[-1][0] == "find_phone"
    await a.measure("heart_rate")
    await a.measure("oxygen")
    await a.measure(None)
    await a.notify("Synthetic test")
    await a.find()
    for value in ["", "x" * 121]:
        with pytest.raises(ValueError):
            await a.notify(value)
    with pytest.raises(ValueError):
        await a.measure("unsupported")
    await a.measure("heart_rate")
    await a.close()
    assert any(data[4:] == b"\x6d\xff" for data in t.writes)
    with pytest.raises(WatchError):
        await a.send(0x26)


async def test_timeout_disconnect_and_rollback():
    a, t, _ = await setup_adapter()
    t.no_reply.add(0x26)
    with pytest.raises(WatchError, match="did not answer"):
        await a.query(0x26, response_seconds=0.01)
    t.no_reply.clear()
    t.ignore.add(0x16)
    with pytest.raises(WatchError, match="Original value restored"):
        await a.set_setting("goal", 4100)
    assert t.settings[0x26] == (4000).to_bytes(4, "little")
    t.settings[0x26] = b""
    with pytest.raises(ProtocolError, match="snapshot"):
        await a.set_setting("goal", 4100)
    t.no_reply.add(0x26)
    task = asyncio.create_task(a.query(0x26))
    await asyncio.sleep(0)
    a.disconnected()
    with pytest.raises(WatchError, match="disconnected"):
        await task
    with pytest.raises(WatchError):
        await a.query(0x26)
    t2 = FakeTransport()
    t2.manufacturer = b"OTHER"
    with pytest.raises(WatchError):
        await MoyoungAdapter(t2, lambda *_: None).initialize()


async def test_invalid_settings_collected_not_invented():
    a, t, _ = await setup_adapter()
    t.settings[0x2B] = b""
    t.settings[0x27] = b"\0\1"
    result = await a.read_settings()
    assert len(result["errors"]) == 2 and "language" not in result

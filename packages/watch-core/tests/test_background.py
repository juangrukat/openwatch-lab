"""Negotiated background transfer, CRC commit, failure and lifecycle tests."""

import asyncio
import base64
import binascii
from unittest.mock import AsyncMock

import pytest

from openwatch import protocol as p
from openwatch.adapters.moyoung import MoyoungAdapter
from openwatch.background import DIMENSIONS, IMAGE_BYTES, upload
from openwatch.errors import WatchError
from openwatch.service import Service
from test_adapter import FakeTransport

IMAGE = bytes(range(256)) * (IMAGE_BYTES // 256) + bytes(range(IMAGE_BYTES % 256))


class ImageTransport(FakeTransport):
    def __init__(self, mode="success"):
        super().__init__()
        self.mode = mode
        self.data = bytearray()
        self.committed = False
        self.aborted = False
        self.first_write = asyncio.Event()
        self.block = asyncio.Event()

    def emit(self, command, payload):
        self.receivers[p.uuid("fee3")](p.encode(command, payload))

    async def write(self, char, data):
        if char == p.uuid("fee6"):
            if self.mode == "block":
                self.first_write.set()
                await self.block.wait()
            if self.mode == "disconnect":
                self.connected = False
                self.adapter.disconnected()
                raise WatchError("Disconnected")
            self.data.extend(data)
            if len(self.data) % 10240 == 0 or len(self.data) == IMAGE_BYTES:
                if len(self.data) == IMAGE_BYTES:
                    crc = binascii.crc_hqx(self.data, 0xFEEA) ^ (
                        1 if self.mode == "crc" else 0
                    )
                    self.emit(0x6E, b"\xff\xff" + crc.to_bytes(2, "big"))
                else:
                    self.emit(0x6E, (len(self.data) // 10240).to_bytes(2, "big"))
            return
        command = data[4]
        body = data[5:]
        if command == 0x39:
            self.emit(command, bytes(37) + DIMENSIONS + b"\xff")
            return
        if command == 0x5A:
            self.emit(command, b"\x08" + (512000).to_bytes(4, "little"))
            return
        if command == 0x6E:
            if body == bytes(4):
                self.committed = True
            elif body == b"\xff" * 4:
                self.aborted = True
            else:
                if self.mode != "missing":
                    self.emit(
                        0xBA,
                        b"\x01"
                        + (0 if self.mode == "size" else 10240).to_bytes(2, "little"),
                    )
                self.emit(0x6E, b"\xff\x00" if self.mode == "index" else b"\0\0")
            return
        await super().write(char, data)


async def make(mode):
    t = ImageTransport(mode)
    events = []
    a = MoyoungAdapter(t, lambda kind, data: events.append((kind, data)))
    t.adapter = a
    await a.initialize()
    return a, t, events


async def test_background_verified_full_transfer(monkeypatch):
    monkeypatch.setattr("openwatch.background.asyncio.sleep", AsyncMock())
    a, t, events = await make("success")
    await upload(a, IMAGE)
    assert bytes(t.data) == IMAGE and t.committed and not t.aborted
    assert events[-1][1]["status"] == "success"
    assert a.image_receiver is None
    await a.close()


@pytest.mark.parametrize("mode", ["crc", "size", "missing", "index", "disconnect"])
async def test_background_failures_do_not_commit(mode, monkeypatch):
    monkeypatch.setattr("openwatch.background.asyncio.sleep", AsyncMock())
    a, t, _ = await make(mode)
    with pytest.raises(WatchError):
        await upload(a, IMAGE)
    assert not t.committed and (t.aborted or not t.connected)
    assert a.image_receiver is None
    await a.close()


async def test_background_cancellation_restores_selection():
    a, t, _ = await make("block")
    task = asyncio.create_task(upload(a, IMAGE))
    await asyncio.wait_for(t.first_write.wait(), 2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert t.aborted and t.settings[0x29] == b"\2" and not t.committed
    assert a.image_receiver is None
    await a.close()


async def test_background_rejects_bad_shape_and_limits(monkeypatch):
    a, t, _ = await make("success")
    with pytest.raises(ValueError):
        await upload(a, b"bad")
    original = t.write

    async def small_limit(char, data):
        if char == p.uuid("fee2") and data[4] == 0x5A:
            t.emit(0x5A, b"\x08" + (100).to_bytes(4, "little"))
        else:
            await original(char, data)

    monkeypatch.setattr(t, "write", small_limit)
    with pytest.raises(WatchError, match="limit"):
        await upload(a, IMAGE)
    assert not t.committed and not t.aborted
    await a.close()


async def test_service_staging_start_gating_cancel(tmp_path, monkeypatch):
    a, t, _ = await make("block")
    s = Service(tmp_path / "db.sqlite3", lambda *_: None)
    s.adapter = a
    s.transport = t
    s.state.update(connected=True, profile_verified=True)
    for args in [
        {"part": True, "data": "AA=="},
        {"part": 0, "data": "!!"},
        {"part": 0, "data": ""},
        {"part": 0, "data": 3},
        {"part": 1, "data": "AA=="},
    ]:
        with pytest.raises(ValueError):
            await s.command("background_stage", args)
    with pytest.raises(ValueError):
        await s.command("background_start", {})
    for part, offset in enumerate(range(0, len(IMAGE), 4096)):
        await s.command(
            "background_stage",
            {
                "part": part,
                "data": base64.b64encode(IMAGE[offset : offset + 4096]).decode(),
            },
        )
    assert (await s.command("background_start", {}))["started"]
    with pytest.raises(WatchError, match="cancel"):
        await s.command("refresh", {})
    await asyncio.wait_for(t.first_write.wait(), 2)
    await s.command("background_cancel", {})
    assert s.state["background"]["status"] == "cancelled" and t.aborted
    assert not s.background_active() and not s.background_bytes
    await s.close()


async def test_service_close_cancels_before_task_runs(tmp_path):
    a, t, _ = await make("block")
    s = Service(tmp_path / "db.sqlite3", lambda *_: None)
    s.adapter = a
    s.transport = t
    s.state.update(connected=True, profile_verified=True)
    s.background_bytes.extend(IMAGE)
    await s.command("background_start", {})
    await s.close()
    assert not s.background_active() and not t.connected

"""Device scoping, deduplication and strict command boundary tests."""

from pathlib import Path

import pytest

from openwatch.capabilities import match_adapter
from openwatch.errors import WatchError
from openwatch.service import Service, integer, text
from openwatch.store import Store


def test_store(tmp_path):
    s = Store(tmp_path / "data" / "observations.sqlite3")
    s.remember("a", "Synthetic", "moyoung-o20")
    assert s.devices() == [{"id": "a", "name": "Synthetic", "adapter": "moyoung-o20"}]
    s.put("a", "oxygen", "1", {"value": 98})
    s.put("a", "oxygen", "1", {"value": 97})
    s.put("b", "oxygen", "1", {"value": 99})
    assert len(s.history()) == 2 and len(s.history("a")) == 1
    assert s.history("a")[0]["data"]["value"] == 97
    assert len(s.history(limit=0)) == 1
    s.close()


def test_matching_and_input_types():
    assert (
        match_adapter("itel ISW-O20", ["0000fd35-0000-1000-8000-00805f9b34fb"], {})
        == "moyoung-o20"
    )
    assert (
        match_adapter("itel O20", [], {0x0942: bytes.fromhex("000210231000")})
        == "moyoung-o20"
    )
    assert match_adapter("Unknown", [], {}) is None
    assert integer({"value": 1}, "value") == 1 and text({"name": "x"}, "name") == "x"
    for value in [True, 1.5, "1", None]:
        with pytest.raises(ValueError):
            integer({"value": value}, "value")
    with pytest.raises(ValueError):
        text({"name": "x" * 1001}, "name")
    with pytest.raises(ValueError):
        text({}, "missing")


async def test_demo_is_explicit_read_only_and_not_persisted(tmp_path):
    events = []
    s = Service(tmp_path / "local.sqlite3", lambda *event: events.append(event))
    assert not (await s.command("state", {}))["demo"]
    assert await s.command("history", {}) == []
    result = await s.command("demo", {})
    assert result["demo"] and not result["connected"]
    assert len(await s.command("history", {})) == 2
    assert s.store.history() == []
    assert (await s.command("export", {}))["schema"] == "openwatch.observations.v1"
    assert await s.command("packets", {}) == []
    with pytest.raises(WatchError, match="read-only"):
        await s.command("find", {})
    await s.command("disconnect", {})
    await s.close()
    await s.close()
    with pytest.raises(WatchError):
        await s.command("state", {})


async def test_command_rejections_and_disconnect_events(tmp_path):
    s = Service(tmp_path / "local.sqlite3", lambda *_: None)
    with pytest.raises(ValueError, match="select"):
        await s.command("connect", {"id": "not-scanned"})
    for command, args in [
        ("unknown", {}),
        ("set_alarm", {"enabled": 1}),
        ("measure", {"kind": 1}),
    ]:
        with pytest.raises(ValueError):
            await s.command(command, args)
    with pytest.raises(WatchError):
        s.require_adapter()
    s.event("heart_rate", {"bpm": 72})
    assert s.state["heart_rate"]["bpm"] == 72
    s.event("activity", {"steps": 100})
    assert s.state["activity"]["steps"] == 100
    s.event("measurement", {"kind": "oxygen"})
    assert s.state["measurement"] == "oxygen"
    s.event("warning", {"message": "synthetic warning"})
    assert s.state["warning"] == "synthetic warning"
    for _ in range(205):
        s.event("packet", {"hex": "feea200521", "direction": "tx"})
    assert len(s.logs) == 200
    s.on_disconnect()
    assert s.state["heart_rate"] is None
    await s.close()

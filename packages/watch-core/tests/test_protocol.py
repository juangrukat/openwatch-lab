"""Synthetic protocol fixtures. None of these samples comes from personal captures."""

import struct

import pytest

from openwatch import protocol as p
from openwatch.errors import ProtocolError


def test_fragmented_joined_and_noise_frames():
    decoder = p.FrameDecoder()
    a, b = p.encode(0x26, bytes.fromhex("d2040000")), p.encode(0x2B, b"\0")
    assert decoder.feed(b"noise\xfe") == []
    assert decoder.feed(a[1:4]) == []
    assert decoder.feed(a[4:] + b + b"\0\0") == [
        p.Frame(0x26, bytes.fromhex("d2040000")),
        p.Frame(0x2B, b"\0"),
    ]
    assert decoder.feed(bytes.fromhex("feea200100") + b) == [p.Frame(0x2B, b"\0")]
    assert decoder.feed(bytes.fromhex("feea30052b") + b) == [p.Frame(0x2B, b"\0")]
    assert decoder.feed(bytes.fromhex("feea10062b01")) == [p.Frame(0x2B, b"\1")]
    decoder.feed(b"\xfe\xea\x20")
    decoder.clear()
    assert decoder.buffer == b""
    big = p.encode(0xB2, bytes(300))
    assert p.FrameDecoder().feed(big)[0].payload == bytes(300)
    for command, data in [(256, b""), (-1, b""), (1, bytes(4091))]:
        with pytest.raises(ValueError):
            p.encode(command, data)


def test_measurements():
    assert p.uuid("FEE3") == "0000fee3-0000-1000-8000-00805f9b34fb"
    assert p.activity(bytes.fromhex("d20400370000060000")) == {
        "steps": 1234,
        "distance_raw": 55,
        "calories_raw": 6,
    }
    assert p.heart_rate(bytes([6, 72])) == 72
    assert p.heart_rate(bytes([1, 80, 0])) == 80
    assert p.heart_rate(bytes([0, 0])) is None
    assert p.heart_rate(bytes([1, 255, 1])) is None
    for b in [b"", b"\1\x48"]:
        with pytest.raises(ProtocolError):
            p.heart_rate(b)
    assert p.battery(bytes([128])) == {"percent": 28, "charging": True, "raw": 128}
    assert p.battery(bytes([76]))["percent"] == 76
    assert p.battery(bytes([255]))["percent"] is None
    with pytest.raises(ProtocolError):
        p.activity(bytes(8))
    with pytest.raises(ProtocolError):
        p.battery(b"")


def test_manual_records_empty_multi_and_bad():
    assert p.manual_records("oxygen", b"\x02\0") == []
    assert p.manual_records("stress", b"\x11\x02\0") == []
    stamp = 1704153600
    records = p.manual_records(
        "oxygen",
        b"\x02\x02"
        + bytes([98])
        + stamp.to_bytes(4, "little")
        + bytes([97])
        + (stamp + 60).to_bytes(4, "little"),
    )
    assert [r["value"] for r in records] == [98, 97]
    assert records[0]["time"] == "2024-01-02T08:00:00+08:00"
    assert (
        p.manual_records(
            "stress", b"\x11\x02\x01" + bytes([32]) + stamp.to_bytes(4, "little")
        )[0]["value"]
        == 32
    )
    assert p.manual_records("oxygen", b"\x02\x01" + bytes(5)) == []
    assert (
        p.manual_records("oxygen", b"\x02\x01" + b"\xff" + stamp.to_bytes(4, "little"))
        == []
    )
    for bad in [b"\x02", b"\3\0", b"\x02\2" + bytes(5)]:
        with pytest.raises(ProtocolError):
            p.manual_records("oxygen", bad)
    with pytest.raises(ValueError):
        p.manual_records("unknown", b"")


def test_alarms_and_workouts():
    alarm = p.Alarm(1, True, 2, 7, 35, b"\0\0", 62)
    assert p.Alarm.decode(alarm.encode()) == alarm
    assert len(p.alarms(bytes(24))) == 3
    assert p.Alarm.decode(bytes(8)).public(2)["slot"] == 2
    assert p.Alarm.decode(bytes(8)).public(2)["empty"]
    with pytest.raises(ValueError):
        p.Alarm(3, True, 2, 24, 0, b"\0\0", 128).encode()
    with pytest.raises(ProtocolError):
        p.alarms(b"")
    listing = bytearray(31)
    listing[0] = 1
    listing[1 + 5 * 2 : 1 + 5 * 2 + 4] = (1704153600).to_bytes(4, "little")
    assert p.workout_list(bytes(listing)) == [2]
    with pytest.raises(ProtocolError):
        p.workout_list(bytes(31))
    detail = bytearray(30)
    detail[:2] = bytes([3, 2])
    struct.pack_into("<IIH", detail, 2, 1704153600, 1704153720, 115)
    struct.pack_into("<IIH", detail, 14, 123, 80, 4)
    parsed = p.workout(bytes(detail))
    assert parsed and parsed["steps"] == 123 and parsed["elapsed_seconds"] == 120
    assert p.workout(bytes([3]) + bytes(29)) is None
    with pytest.raises(ProtocolError):
        p.workout(bytes(30))
    struct.pack_into("<I", detail, 6, 1)
    with pytest.raises(ProtocolError):
        p.workout(bytes(detail))
    assert p.workout_hr(bytes([5, 2, 255, 255, 0, 72, 255, 74]), 2)["samples"] == [
        None,
        72,
        None,
        74,
    ]
    assert p.workout_hr(bytes([5, 2]), 2)["terminal"]
    assert not p.workout_hr(bytes([5, 2, 0, 1, 72]), 2)["terminal"]
    with pytest.raises(ProtocolError):
        p.workout_hr(b"\x05\x01", 2)

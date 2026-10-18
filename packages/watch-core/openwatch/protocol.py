"""Pure Moyoung V2 framing and strict codecs. No OS or vendor SDK dependency."""

import struct
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from .errors import ProtocolError

MAX_FRAME = 4095
WATCH_ZONE = timezone(timedelta(hours=8))


def uuid(short: str) -> str:
    """Expand a Bluetooth SIG-style 16-bit UUID."""
    return f"0000{short.lower()}-0000-1000-8000-00805f9b34fb"


@dataclass(frozen=True)
class Frame:
    """A reassembled vendor command and its payload."""

    command: int
    payload: bytes


def encode(command: int, payload: bytes = b"") -> bytes:
    """Encode a length-bounded Moyoung V2 command."""
    size = 5 + len(payload)
    if not 0 <= command <= 255 or size > MAX_FRAME:
        raise ValueError("Command or frame length is out of range")
    return bytes((0xFE, 0xEA, 0x20 | (size >> 8), size & 255, command)) + payload


class FrameDecoder:
    """Reassemble arbitrary notification fragments and recover after bad headers."""

    def __init__(self) -> None:
        self.buffer = bytearray()

    def clear(self) -> None:
        """Discard partial data at a connection boundary."""
        self.buffer.clear()

    def feed(self, data: bytes) -> list[Frame]:
        """Return complete frames; never interpret partial packets as observations."""
        self.buffer.extend(data)
        result: list[Frame] = []
        while self.buffer:
            start = self.buffer.find(b"\xfe\xea")
            if start < 0:
                self.buffer[:] = b"\xfe" if self.buffer[-1] == 0xFE else b""
                break
            del self.buffer[:start]
            if len(self.buffer) < 5:
                break
            marker = self.buffer[2]
            size = ((marker & 15) << 8) | self.buffer[3]
            if marker != 0x10 and marker & 0xF0 != 0x20:
                del self.buffer[0]
                continue
            if size < 5 or size > MAX_FRAME:
                del self.buffer[0]
                continue
            if len(self.buffer) < size:
                break
            result.append(Frame(self.buffer[4], bytes(self.buffer[5:size])))
            del self.buffer[:size]
        return result


def require_size(data: bytes, size: int, label: str) -> None:
    """Reject unknown/truncated layouts rather than inventing a value."""
    if len(data) != size:
        raise ProtocolError(f"{label}: expected {size} bytes, received {len(data)}")


def activity(data: bytes) -> dict[str, int]:
    """Decode daily activity totals; distance/calorie units are candidates."""
    require_size(data, 9, "Activity")
    return {
        "steps": int.from_bytes(data[:3], "little"),
        "distance_raw": int.from_bytes(data[3:6], "little"),
        "calories_raw": int.from_bytes(data[6:9], "little"),
    }


def heart_rate(data: bytes) -> int | None:
    """Decode the standard Heart Rate Measurement flags and uint8/uint16 value."""
    if len(data) < 2:
        raise ProtocolError("Truncated heart-rate measurement")
    wide = bool(data[0] & 1)
    if wide and len(data) < 3:
        raise ProtocolError("Truncated 16-bit heart-rate measurement")
    value = int.from_bytes(data[1 : 3 if wide else 2], "little")
    return value if 0 < value < 255 else None


def battery(data: bytes) -> dict[str, Any]:
    """Handle observed Moyoung charging offset, retaining the raw value."""
    require_size(data, 1, "Battery")
    raw = data[0]
    charging = 100 < raw <= 200
    value = raw - 100 if charging else raw
    return {
        "percent": value if value <= 100 else None,
        "charging": charging,
        "raw": raw,
    }


def watch_time(timestamp: int) -> str:
    """Retain the profile's GMT+8 candidate time, independent of host timezone."""
    return datetime.fromtimestamp(timestamp, WATCH_ZONE).isoformat()


def manual_records(kind: str, data: bytes) -> list[dict[str, Any]]:
    """Decode manual history separately from automatic day-history packets."""
    prefixes = {"oxygen": b"\x02", "stress": b"\x11\x02"}
    if kind not in prefixes:
        raise ValueError("Unknown manual record kind")
    prefix = prefixes[kind]
    if not data.startswith(prefix) or len(data) <= len(prefix):
        raise ProtocolError("Unexpected manual-record response subtype")
    count = data[len(prefix)]
    body = data[len(prefix) + 1 :]
    require_size(body, count * 5, "Manual history")
    result: list[dict[str, Any]] = []
    for i in range(0, len(body), 5):
        value = body[i]
        timestamp = int.from_bytes(body[i + 1 : i + 5], "little")
        if not 0 < value <= 100 or timestamp == 0:
            continue
        result.append(
            {
                "kind": kind,
                "value": value,
                "source_time": timestamp,
                "time": watch_time(timestamp),
                "origin": "manual-history",
            }
        )
    return result


@dataclass(frozen=True)
class Alarm:
    """One eight-byte legacy alarm slot, preserving otherwise unknown date bytes."""

    slot: int
    enabled: bool
    repeat_mode: int
    hour: int
    minute: int
    date_bytes: bytes
    weekdays: int

    @classmethod
    def decode(cls, data: bytes) -> "Alarm":
        """Read one slot without rewriting its unknown fields."""
        require_size(data, 8, "Alarm")
        return cls(
            data[0], bool(data[1]), data[2], data[3], data[4], data[5:7], data[7]
        )

    def encode(self) -> bytes:
        """Encode a validated slot; zero unused slots are also representable."""
        if not (
            0 <= self.slot <= 2
            and 0 <= self.hour < 24
            and 0 <= self.minute < 60
            and 0 <= self.weekdays <= 127
            and self.repeat_mode in (0, 1, 2)
            and len(self.date_bytes) == 2
        ):
            raise ValueError("Invalid alarm slot/time/repetition")
        return (
            bytes(
                (self.slot, int(self.enabled), self.repeat_mode, self.hour, self.minute)
            )
            + self.date_bytes
            + bytes((self.weekdays,))
        )

    def public(self, index: int) -> dict[str, Any]:
        """Expose logical list index even when an empty slot has ID zero."""
        return {
            "slot": index,
            "enabled": self.enabled,
            "hour": self.hour,
            "minute": self.minute,
            "weekdays": self.weekdays,
            "empty": not self.enabled
            and self.hour == self.minute == self.weekdays == 0,
        }


def alarms(data: bytes) -> list[Alarm]:
    """Decode the tested three-slot legacy response."""
    require_size(data, 24, "Alarm list")
    return [Alarm.decode(data[i : i + 8]) for i in range(0, 24, 8)]


def workout_list(data: bytes) -> list[int]:
    """Extract occupied slots from the tested fixed-size timestamp list."""
    if len(data) != 31 or data[0] != 1:
        raise ProtocolError(
            "Unknown workout-list layout; raw data retained in inspector"
        )
    return [i for i in range(6) if any(data[1 + i * 5 : 6 + i * 5])]


def workout(data: bytes) -> dict[str, Any] | None:
    """Decode the observed 30-byte O20 detail layout, retaining uncertain fields."""
    require_size(data, 30, "Workout")
    if data[0] != 3:
        raise ProtocolError("Unknown workout detail subtype")
    if not any(data[2:26]):
        return None
    start, end, active = struct.unpack_from("<IIH", data, 2)
    if end < start:
        raise ProtocolError("Workout ends before its start")
    return {
        "kind": "workout",
        "slot": data[1],
        "source_time": start,
        "time": watch_time(start),
        "end_time": watch_time(end),
        "elapsed_seconds": end - start,
        "active_seconds_candidate": active,
        "sport_code": data[13],
        "steps": int.from_bytes(data[14:18], "little"),
        "distance_raw": int.from_bytes(data[18:22], "little"),
        "calories_raw": int.from_bytes(data[22:24], "little"),
        "byte12_raw": data[12],
        "byte24_raw": data[24],
        "origin": "workout-history",
    }


def workout_hr(data: bytes, slot: int) -> dict[str, Any]:
    """Decode a workout HR page; zero/FF samples remain missing, never health values."""
    if len(data) < 2 or data[0] != 5 or data[1] != slot:
        raise ProtocolError("Unknown workout HR response")
    if len(data) < 4:
        return {"samples": [], "terminal": True, "index_raw": None}
    return {
        "samples": [v if 0 < v < 255 else None for v in data[4:]],
        "terminal": data[2:4] == b"\xff\xff",
        "index_raw": data[2:4].hex(),
        "spacing_seconds_candidate": 10,
    }

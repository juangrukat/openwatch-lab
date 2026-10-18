"""Versioned, honest feature declarations separate from discovery."""

from typing import Any

CAPABILITIES: list[dict[str, Any]] = [
    {
        "id": "battery",
        "name": "Battery & device information",
        "status": "verified",
        "write": False,
    },
    {
        "id": "activity",
        "name": "Daily step count",
        "status": "verified",
        "write": False,
    },
    {
        "id": "heart_rate",
        "name": "Live heart rate",
        "status": "verified",
        "write": True,
    },
    {
        "id": "manual_history",
        "name": "Stored oxygen & stress",
        "status": "verified",
        "write": False,
    },
    {
        "id": "workouts",
        "name": "Workout detail & heart-rate pages",
        "status": "partial",
        "write": False,
    },
    {"id": "alarms", "name": "Three alarm slots", "status": "verified", "write": True},
    {
        "id": "settings",
        "name": "Goal, language, time format, units & reminders",
        "status": "verified",
        "write": True,
    },
    {
        "id": "watch_face",
        "name": "Built-in watch-face selection",
        "status": "verified",
        "write": True,
    },
    {
        "id": "notify",
        "name": "Local test notification",
        "status": "verified",
        "write": True,
    },
    {
        "id": "find",
        "name": "Audible find-watch signal",
        "status": "verified",
        "write": True,
    },
    {
        "id": "oxygen_live",
        "name": "Oxygen measurement start/stop",
        "status": "partial",
        "write": True,
        "note": "Fresh live values are unverified. Stored history is separate.",
    },
    {
        "id": "sleep",
        "name": "Sleep and periodic health histories",
        "status": "unverified",
        "write": False,
        "note": "Empty replies observed. Populated record decoding is not validated.",
    },
    {
        "id": "firmware",
        "name": "Firmware modification / reset",
        "status": "unavailable",
        "write": False,
    },
]


def match_adapter(
    name: str, services: list[str], manufacturer: dict[int, bytes]
) -> str | None:
    """Select the evidenced O20 advertisement, not unknown Moyoung models."""
    is_o20 = "o20" in name.lower() and "itel" in name.lower()
    signature = manufacturer.get(0x0942, b"").startswith(bytes.fromhex("00021023"))
    has_service = any("fd35" in value.lower() for value in services)
    return "moyoung-o20" if is_o20 and (signature or has_service) else None

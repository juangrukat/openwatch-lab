"""Errors safe to display across the desktop bridge."""


class WatchError(Exception):
    """A device operation could not be completed."""


class ProtocolError(WatchError):
    """Received bytes do not match the supported protocol."""


class UnsupportedError(WatchError):
    """The selected adapter does not implement this operation."""

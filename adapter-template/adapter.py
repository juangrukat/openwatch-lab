"""Copy into openwatch/adapters and replace identity/decoders with evidence.

This skeleton intentionally supports only standard information reads. It does
not register itself or enable writes for any model.
"""

from openwatch.protocol import uuid
from openwatch.transport import Transport


class ExampleAdapter:
    """Minimal transport-independent starting point for a new watch."""

    id = "example-read-only"

    def __init__(self, transport: Transport) -> None:
        self.transport = transport

    async def initialize(self) -> dict[str, str]:
        """Read optional standard information; unsupported fields stay absent."""
        info: dict[str, str] = {}
        for key, characteristic in (
            ("manufacturer", "2a29"),
            ("firmware", "2a26"),
            ("software", "2a28"),
        ):
            try:
                info[key] = (
                    (await self.transport.read(uuid(characteristic)))
                    .decode(errors="replace")
                    .strip("\0")
                )
            except Exception:
                continue
        return info

    async def close(self) -> None:
        """Release the connection owned by this adapter."""
        await self.transport.close()

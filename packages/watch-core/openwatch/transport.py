"""BLE transport abstraction and Bleak implementation for CoreBluetooth / WinRT."""

from collections.abc import Callable
from typing import Protocol

from bleak import BleakClient
from bleak.backends.device import BLEDevice

from .errors import WatchError

Receiver = Callable[[bytes], None]


class Transport(Protocol):
    """Minimum I/O contract an adapter needs; usable by replay/fake transports."""

    @property
    def connected(self) -> bool: ...

    async def read(self, characteristic: str) -> bytes: ...
    async def subscribe(self, characteristic: str, receiver: Receiver) -> None: ...
    async def write(self, characteristic: str, value: bytes) -> None: ...
    async def close(self) -> None: ...


class BleTransport:
    """One explicitly selected BLE device; never scans/connects in the background."""

    def __init__(
        self, device: BLEDevice | str, disconnected: Callable[[], None]
    ) -> None:
        self.client = BleakClient(
            device, disconnected_callback=lambda _: disconnected()
        )

    @property
    def connected(self) -> bool:
        """Whether the OS currently has an active client connection."""
        return self.client.is_connected

    async def connect(self) -> None:
        """Connect through the OS; no vendor login or owner ID is supplied."""
        await self.client.connect(timeout=20)

    async def read(self, characteristic: str) -> bytes:
        """Read a characteristic, retaining exceptions for the service boundary."""
        return bytes(await self.client.read_gatt_char(characteristic))

    async def subscribe(self, characteristic: str, receiver: Receiver) -> None:
        """Subscribe before issuing any query that expects notifications."""
        await self.client.start_notify(
            characteristic, lambda _sender, data: receiver(bytes(data))
        )

    async def write(self, characteristic: str, value: bytes) -> None:
        """Write fragments bounded by the characteristic's negotiated capacity."""
        char = self.client.services.get_characteristic(characteristic)
        if char is None:
            raise WatchError("The device does not expose the required write channel")
        capacity = max(1, min(char.max_write_without_response_size, 512))
        for offset in range(0, len(value), capacity):
            await self.client.write_gatt_char(
                char, value[offset : offset + capacity], response=False
            )

    async def close(self) -> None:
        """Disconnect the owned client (other apps' clients are not modified)."""
        if self.client.is_connected:
            await self.client.disconnect()

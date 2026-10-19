"""Validated O20 raw RGB565 background transfer, independent of the desktop UI."""

import asyncio
import binascii
from typing import TYPE_CHECKING

from . import protocol as p
from .errors import WatchError

if TYPE_CHECKING:
    from .adapters.moyoung import MoyoungAdapter

IMAGE_BYTES = (240 * 284 + 140 * 163) * 2
DIMENSIONS = bytes.fromhex("00f0008c011c00a3")


async def upload(adapter: "MoyoungAdapter", image: bytes) -> None:
    """Transfer an exact raw image with negotiated chunks and checksum commit."""
    if len(image) != IMAGE_BYTES:
        raise ValueError("Background must contain a 240×284 image and 140×163 preview")
    if adapter.measurement:
        await adapter.measure(None)
    async with adapter.operation_lock:
        before = await adapter.query(0x29)
        layout = await adapter.query(0x39)
        if not before or len(layout) != 46 or layout[37:45] != DIMENSIONS:
            raise WatchError(
                "Watch background dimensions are not the validated O20 size"
            )
        limit = await adapter.query(0x5A, b"\x08", lambda v: v[:1] == b"\x08")
        if len(limit) < 5 or int.from_bytes(limit[1:5], "little") < len(image):
            raise WatchError("Watch object limit is too small for this background")
        queue: asyncio.Queue[tuple[int, bytes]] = asyncio.Queue(maxsize=128)

        def receive(command: int, payload: bytes) -> None:
            if command in (-1, 0x6E, 0xBA) and not queue.full():
                queue.put_nowait((command, payload))

        adapter.image_receiver = receive
        started = False
        committed = False
        sent: set[int] = set()
        chunk_size = 0
        last = -1
        repeated = 0
        crc = binascii.crc_hqx(image, 0xFEEA)

        def progress(status: str, transferred: int, message: str) -> None:
            adapter.event(
                "background",
                {
                    "status": status,
                    "transferred": transferred,
                    "total": len(image),
                    "message": message,
                },
            )

        try:
            progress("uploading", 0, "Waiting for the watch…")
            started = True
            await adapter.send(0x6E, len(image).to_bytes(4, "big"))
            async with asyncio.timeout(240):
                while True:
                    command, payload = await asyncio.wait_for(queue.get(), 25)
                    if command == -1:
                        raise WatchError("Watch disconnected during background upload")
                    if command == 0xBA:
                        if payload[:1] == b"\x01":
                            if len(payload) != 3:
                                raise WatchError("Invalid image chunk negotiation")
                            size = int.from_bytes(payload[1:3], "little")
                            if sent or not 20 <= size <= 16384:
                                raise WatchError("Unsupported image chunk size")
                            chunk_size = size
                        continue
                    if not chunk_size:
                        raise WatchError("Watch did not negotiate an image chunk size")
                    count = (len(image) + chunk_size - 1) // chunk_size
                    if len(payload) == 4:
                        if (
                            len(sent) != count
                            or int.from_bytes(payload[2:], "big") != crc
                        ):
                            raise WatchError(
                                "Background checksum did not match; upload cancelled"
                            )
                        progress("verifying", len(image), "Verifying background…")
                        await adapter.send(0x6E, bytes(4))
                        committed = True
                        progress(
                            "success",
                            len(image),
                            "Uploaded and checksum verified. Check the watch display.",
                        )
                        return
                    if len(payload) != 2:
                        raise WatchError("Malformed background chunk request")
                    index = int.from_bytes(payload, "big")
                    if not 0 <= index < count or (
                        index != len(sent) and index not in sent
                    ):
                        raise WatchError("Watch requested an invalid background chunk")
                    repeated = repeated + 1 if index == last else 0
                    last = index
                    if repeated >= 11:
                        raise WatchError("Watch repeatedly rejected a background chunk")
                    chunk = image[index * chunk_size : (index + 1) * chunk_size]
                    for offset in range(0, len(chunk), 256):
                        await adapter.transport.write(
                            p.uuid("fee6"), chunk[offset : offset + 256]
                        )
                        await asyncio.sleep(0.01)
                    sent.add(index)
                    progress(
                        "uploading",
                        min(len(sent) * chunk_size, len(image)),
                        "Sending background…",
                    )
        finally:
            try:
                if started and not committed and adapter.transport.connected:
                    await adapter.send(0x6E, b"\xff" * 4)
                    await asyncio.sleep(0.2)
                    await adapter.send(0x19, before[:1])
                    restored = await adapter.query(0x29)
                    if restored != before:
                        raise WatchError(
                            "Upload stopped; prior face selection could not be verified"
                        )
            finally:
                adapter.image_receiver = None

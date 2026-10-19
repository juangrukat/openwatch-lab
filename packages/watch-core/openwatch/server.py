"""JSON-lines desktop sidecar. stdout is exclusively protocol; stderr is diagnostics."""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from platformdirs import user_data_path

from .service import Service


def output(message: dict[str, Any]) -> None:
    """Emit a finite JSON message atomically on the owner thread."""
    print(json.dumps(message, allow_nan=False, separators=(",", ":")), flush=True)


async def run(path: Path) -> None:
    """Process bounded commands serially and clean up on pipe closure."""
    service = Service(path, lambda event, data: output({"event": event, "data": data}))
    output({"event": "ready", "data": {"version": "0.2.0"}})
    try:
        while True:
            line = await asyncio.to_thread(sys.stdin.readline, 65537)
            if not line:
                break
            request_id: str | int | None = None
            try:
                if len(line) > 65536 or not line.endswith("\n"):
                    raise ValueError(
                        "Request exceeds 64 KiB or lacks a line terminator"
                    )
                request = json.loads(line)
                if not isinstance(request, dict):
                    raise ValueError("Expected a command object")
                request_id = request.get("id")
                if type(request_id) not in (str, int):
                    raise ValueError("Request id must be a string or integer")
                command = request.get("command")
                args = request.get("args", {})
                if not isinstance(command, str) or not isinstance(args, dict):
                    raise ValueError("Invalid command/args")
                result = await service.command(command, args)
                output({"id": request_id, "result": result})
            except Exception as exc:
                output(
                    {
                        "id": request_id,
                        "error": {"message": str(exc), "type": type(exc).__name__},
                    }
                )
    finally:
        await service.close()


def main() -> None:
    """Start the account-free backend at a platform-local database path."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path)
    args = parser.parse_args()
    directory = args.data_dir or user_data_path("OpenWatch Lab", appauthor=False)
    asyncio.run(run(directory / "observations.sqlite3"))


if __name__ == "__main__":
    main()

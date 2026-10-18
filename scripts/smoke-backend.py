"""Read-only packaged-backend smoke check; scan only when explicitly requested."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
exe = root / "build/backend/openwatch-backend/openwatch-backend"
with tempfile.TemporaryDirectory() as directory:
    commands = [
        {"id": 1, "command": "state"},
        {"id": 2, "command": "demo"},
        {"id": 3, "command": "history"},
    ]
    if "--scan" in sys.argv:
        commands.append({"id": 4, "command": "scan"})
    run = subprocess.run(
        [str(exe), "--data-dir", directory],
        input="".join(json.dumps(c) + "\n" for c in commands),
        text=True,
        capture_output=True,
        timeout=30,
        check=True,
    )
    replies = [json.loads(line) for line in run.stdout.splitlines()]
    assert next(x for x in replies if x.get("id") == 1)["result"]["connected"] is False
    assert next(x for x in replies if x.get("id") == 2)["result"]["demo"] is True
    assert len(next(x for x in replies if x.get("id") == 3)["result"]) == 2
    print("Packaged backend state, preview and history: PASS")
    if "--scan" in sys.argv:
        result = next(x for x in replies if x.get("id") == 4)
        print(
            "Scan:",
            result.get(
                "error",
                [
                    {"name": x["name"], "supported": x["supported"]}
                    for x in result.get("result", [])
                ],
            ),
        )

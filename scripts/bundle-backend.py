"""Bundle the backend on the target OS; never cross-compile BLE runtimes."""

import os
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
python = root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
subprocess.run(
    [
        str(python),
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--name",
        "openwatch-backend",
        "--distpath",
        "build/backend",
        "--workpath",
        "build/pyinstaller",
        "--specpath",
        "build",
        "--collect-submodules",
        "bleak",
        "scripts/backend-entry.py",
    ],
    cwd=root,
    check=True,
)

# Preserve dependency notices in the standalone runtime.
from importlib.metadata import distributions
import sysconfig

notices = ["OpenWatch Lab backend dependency notices\n"]
python_license = Path(sysconfig.get_path("stdlib")) / "LICENSE.txt"
if python_license.is_file():
    notices.append(python_license.read_text())
for distribution in sorted(distributions(), key=lambda d: d.metadata["Name"].lower()):
    for file in distribution.files or []:
        if "license" in file.name.lower() or file.name.lower().startswith("copying"):
            path = distribution.locate_file(file)
            if path.is_file():
                notices.append(
                    f"\n--- {distribution.metadata['Name']} {distribution.version}: {file} ---\n"
                )
                notices.append(path.read_text(errors="replace"))
(root / "build/backend/openwatch-backend/THIRD-PARTY-NOTICES.txt").write_text(
    "\n".join(notices)
)

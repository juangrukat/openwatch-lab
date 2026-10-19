# OpenWatch Lab

An account-free, local-first desktop companion and open adapter toolkit. The first adapter targets the **itel ISW-O20**, MOYOUNG-V2, software **O20-7LH2-2.1.12**. This is an early working implementation, not universal watch support.

## Run from source

Requirements: Node.js 22.12+ and Python 3.11+. Enable Bluetooth and keep iPulse closed so it does not compete for the connection.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
npm ci
npm run dev
```

On Windows, use `python -m venv .venv` and `.venv\Scripts\python -m pip install -e ".[dev]"`. Then use the same npm commands. Windows requires an actual BLE adapter; its runtime and installer still require hardware validation.

Choose **Connect watch**, scan, and explicitly select your watch. No account, cloud service, vendor token, or automatic pairing workflow is used. Allow the OS Bluetooth permission when prompted. The watch may not appear in macOS Bluetooth Settings because this app connects through BLE GATT.

**Preview** is explicitly synthetic and read-only. It never inserts samples into your watch history. Real history is stored locally in SQLite; the app displays its database path. Export creates a JSON file only where you choose. Packet inspection is held in memory and limited to 200 entries.

## Implemented

- Explicit scan/connect/disconnect; service and characteristic inspection.
- Battery, activity counters, device versions, settings and three legacy alarms.
- Read-back verified settings and alarm changes, preserving other alarm slots.
- Heart-rate and oxygen measurement start/stop; live heart rate.
- Saved oxygen, saved stress, workout details and workout heart-rate data.
- Local test messages, audible find-watch command, local history and JSON export.

Fresh oxygen numbers are **not yet verified**: initiating a measurement works, but saved samples are never presented as its fresh result. Sleep, full workout HR pagination, all sport IDs, all notification categories, phone integration, calling audio, weather and firmware updates are not implemented. Distance/calorie units and several raw setting enum meanings remain candidates. The UI retains raw values where interpretation is uncertain. Writes are disabled on unvalidated software versions. A factory-reset watch was accessed without login on the same Mac; a host with no prior OS cache/bond remains untested.

## Develop and package

```sh
.venv/bin/python -m pytest --cov=openwatch
.venv/bin/python -m mypy
.venv/bin/python -m ruff check packages/watch-core/openwatch
npm run check
npm run backend:bundle
npm run package:mac
```

For Windows, run `npm run backend:bundle` and `npm run package:win` **on Windows**. Each OS needs its own backend build. macOS output is unsigned; distribution signing/notarization is not configured. No releases are uploaded automatically.

See [adapter guide](docs/ADAPTERS.md) and [protocol notes](docs/PROTOCOL.md). Personal research captures and vendor binaries are excluded from the distributable source. Do not submit health records, stable hardware identifiers or account tokens in issues or fixtures.

## License and openness

App and adapter code: **AGPL-3.0-or-later**, see LICENSE. Original protocol documentation and synthetic fixtures: **CC0-1.0**, see docs/CC0-1.0.txt. Dependencies retain their licenses. The common API is a versioned proposal, not a certified interoperability standard. Anyone can implement the documented protocol independently or contribute an adapter without vendor registration.

Further protocol research: [contacts, custom faces, reminders, music and storage](docs/FEATURE-INVESTIGATION.md). These investigation results are separate from the controls shipped in version0.1.0.

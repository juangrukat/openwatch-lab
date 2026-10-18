# Validation — 2026-10-19

- Local platform: macOS, Apple Silicon; actual itel ISW-O20 software O20-7LH2-2.1.12.
- Python: 16 tests pass; 97% statement coverage. Fake BLE covers framing, response subtypes, timeouts, disconnects, setting rollback, alarm slot preservation, device isolation, history deduplication, command validation and transport chunking.
- Strict mypy and Ruff checks pass for the core. TypeScript and Vite production build pass. Two Node bridge tests pass.
- Bundled PyInstaller backend: state, explicit synthetic preview and history smoke check pass.
- Packaged Electron app launched and visually inspected. Preview clearly separated; controls disabled there. Native BLE scan recognized the O20; direct connection and reads succeeded without login. Profile, settings, activity and battery loaded.
- Packaged UI write check: changed goal 4000 → 4001, verified by re-query, then restored 4000 and verified again. Stored-history sync completed with zero records after the reset.
- Previous device experiments confirmed measurement screens, numeric live HR, stored oxygen/stress, notification, audible find, and reversible setting/alarm writes. Current packaging verification does not repeat all physical writes.
- Windows build workflow is supplied but has not run here. Windows BLE, clean-host connection, x64 Mac, signed distribution and notarization remain untested.

No raw personal packet capture is a public fixture. No cloud or vendor registration is involved in the implemented BLE operations.

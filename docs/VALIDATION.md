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

Additional diagnostic validation: custom background181960bytes transferred in18 negotiated10KiB logical chunks, terminalCRC74FF matched, commit sent, and user confirmed correct rendering. First attempt ignoring BA01 negotiation was cancelled and the previous face restored. This is an independent diagnostic operation; the release UI has not gained an upload button. Memory-capacity queries remain unresolved beyond the512000-byte object-transfer limit.

## Version 0.2.0 background uploader

26 Python tests and4 Node tests pass; backend statement coverage96%. Strict mypy, Ruff, Black and TypeScript checks pass. Tests cover10KiB negotiation, complete image/CRC commit, CRC rejection, malformed and missing negotiation, invalid indices, cancellation, disconnect, bounded staging and shutdown. Renderer tests cover RGB order, alpha compositing and center cropping. Windows hardware validation remains outstanding.

Packaged Mac app0.2.0: synthetic sample selected and previewed; a transfer was cancelled successfully from the UI. A subsequent complete UI upload reported a matching checksum and commit. The native file picker opens; automated Go-to-Folder navigation did not complete in the test tool, so arbitrary personal-file selection is not claimed as an automated end-to-end check. Sample loading uses the same bitmap/crop/encoder path.

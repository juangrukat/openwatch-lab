# Contributing to OpenWatch Lab

Contributions that make user-owned watches accessible without mandatory accounts are welcome. Start with the [README](README.md), [protocol notes](docs/PROTOCOL.md) and [adapter guide](docs/ADAPTERS.md).

## Useful contributions

- Validate a build on Windows or a completely fresh Bluetooth host.
- Add an adapter for a specific model/firmware with explicit capability status.
- Decode populated sleep/workout records and unverified settings using reproducible evidence.
- Improve image cropping, accessibility, error recovery or local data portability.

## Development

Use the source setup instructions, then run the Python tests, strict mypy, Ruff and `npm run check`. Include tests for meaningful protocol/lifecycle changes. Use a fake transport first; the current background tests cover negotiation, checksum rejection, cancellation and disconnect.

Keep device-specific commands out of the renderer. Add commands to the narrow IPC allowlists and validate payload types, size, range, device identity and firmware before writes. Preserve unrelated settings, distinguish transport acknowledgments from visible behavior, and explain any limitations.

## Reporting hardware findings

Include watch model, firmware/software version, OS, app version, the operation attempted, expected behavior and observed behavior. State whether the result was physically observed on the watch or inferred from a reply. A generic SDK method name alone is not proof of model support.

Use fabricated fixtures in pull requests. Do not upload real health history, personal contacts/photos, account tokens, stable device identifiers, databases or extracted vendor binaries. If a raw capture is necessary for a decoder, describe a redacted minimum example first.

Application contributions use AGPL-3.0-or-later; original protocol documentation and fabricated fixtures use CC0-1.0. Preserve third-party notices and provenance. See [NOTICE.md](NOTICE.md).

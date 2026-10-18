# Implementation plan

1. Establish repository boundaries, AGPL code/CC0 specification, dependencies, and synthetic fixtures. Preserve private research.
2. Implement pure Moyoung codecs, capability registry and adapter template. Verify malformed and fragmented input tests.
3. Implement asynchronous BLE transport, single-flight query/event dispatch, validated controls, manual/workout retrieval and disconnect/shutdown handling. Test using a fake client.
4. Implement SQLite observation store and validated JSON-lines sidecar API, explicit demo mode and export.
5. Implement sandboxed Electron/preload bridge and local React UI. No remote resources or analytics.
6. Add dependency setup, backend bundling, macOS/Windows packaging and CI. Generate a macOS app locally.
7. Run tests, strict type checks, formatting, build and UI inspection. Test live reads with the O20 when available. Record actual validation and remaining Windows/mobile gaps.

The user approved the design and requested notification once complete; no additional design gate is needed. The installed writing-plans skill was searched for and is unavailable, so this plan is authored directly. No new subagents are requested by this plan.

# Adding a watch adapter

Documentation license: CC0-1.0.

The separation is deliberate: `transport.py` owns BLE I/O; `protocol.py` owns pure framing and decoding; `adapters/moyoung.py` owns this watch's commands; `service.py` exposes a bounded desktop API. The Electron renderer cannot send arbitrary BLE writes or choose backend filesystem paths.

1. Scan and explicitly select the device. Unknown devices may be inspected without activating an adapter.
2. Record service UUIDs, characteristic properties, manufacturer/model/software. Do not use a model name alone to enable writes.
3. Start with standard read characteristics, then subscriptions and read-only vendor queries. Preserve raw payloads privately.
4. Write a pure decoder and synthetic fixtures. Check truncated frames, fragmentation, endianness, unknown values and response correlation.
5. Implement the transport contract from `openwatch.transport.Transport`. Reuse it rather than importing UI code.
6. Add an adapter with `initialize`, `refresh`, `history`, `close` and only capabilities actually supported. Correlate replies by command and subtype, serialize requests, timeout and drain late responses.
7. For settings, snapshot, write, query again, compare and attempt rollback on mismatch. A matching read-back confirms storage, not the physical effect. Preserve unrelated settings and alarm slots.
8. Gate writes by validated identity/firmware. Track unsupported, candidate, read-back verified and physically confirmed separately. Never turn a missing sample into zero or relabel old history as live.
9. Add synthetic transport tests and document hardware validation. Strip health records, device IDs and account credentials before publishing fixtures.

The current internal API uses `state`, `scan`, `connect`, `disconnect`, `refresh`, `sync`, `history`, `packets`, `set_setting`, `set_alarm`, `measure`, `notify`, `find`, `export`. Requests are newline JSON objects `{ "id": 1, "command": "state", "args": {} }`; responses contain the same id and `result` or `error`. Events carry `event` and `data`. The sidecar speaks over inherited stdio only. Export schema is `openwatch.observations.v1`; timestamps retain provenance and source interpretation.

See `adapter-template/README.md` for a contribution checklist. Do not copy vendor SDK binaries into adapters.

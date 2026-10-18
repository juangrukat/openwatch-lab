# New adapter template

Copy the architecture, not the O20 command numbers. Supply:

- `identity`: model, manufacturer, services and validated software versions.
- `capabilities`: explicit supported/candidate/unknown status and evidence.
- `codec`: pure frame encoder, incremental decoder and sample parsers.
- `adapter`: initialize, refresh, history, reversible setting operations, shutdown.
- `fixtures`: fabricated packets with expected decoded outputs and license.
- `tests`: fragmented notifications, late/wrong-subtype replies, disconnects, timeouts, read-back mismatch and rollback.
- `validation.md`: platform, firmware, date, user-observed effects and remaining gaps.

Implement against `openwatch.transport.Transport`. Keep vendor-specific types inside the adapter and expose observations with source timestamps, kind, value and provenance. Do not claim full support merely because a write returned successfully.

# OpenWatch Lab — approved first milestone

Approved by the user on 2026-10-19. Build a registration-free, local-first Mac/Windows desktop companion and a reusable device-adapter toolkit. No cloud, vendor SDK, account or telemetry dependency. Raw personal research captures are private and excluded from distribution.

## Architecture

Electron desktop shell with a sandboxed React/TypeScript renderer. A narrow preload IPC bridge exposes named backend commands. A Python asyncio sidecar speaks newline-delimited JSON over standard input/output; Bleak implements CoreBluetooth on macOS and WinRT on Windows. No HTTP server or open listening port. SQLite holds local observations and device metadata in the user's application-data directory. Events flow BLE -> adapter -> common observations -> SQLite/UI. Protocol codecs do not import Bleak, Electron or storage.

Adapter registry reports explicit matches based on advertisement data; an unrecognized watch can be inspected but receives no vendor writes. The initial adapter is Moyoung V2, tested on itel O20 O20-7LH2-2.1.12. Validate manufacturer and required services after connecting. Capability status distinguishes device-verified features, partially validated features and unavailable features. Existing setup worked after watch reset on the same Mac; never-used-host and Windows hardware tests remain outstanding.

## First-release UI

Sidebar: Overview, Health history, Watch controls, Device lab, and About. Connection panel scans and selects a device explicitly. Overview shows real connection/battery/steps/heart-rate values with empty states, not fabricated health scores. History lists manual oxygen/stress and workout records with timestamps, source and validation status. Controls cover tested alarms, goal, language, simple settings, built-in face and local test notification/find signal. Measurements expose start/stop controls; live oxygen result is explicitly unverified and cannot use old history as a fresh result. Device lab shows capabilities, services and a bounded packet log; unknown raw writes are not exposed by the normal UI. Demo mode is explicit, synthetic, opt-in and cannot write BLE.

## Protocol and operations

FE EA header, length and command framing with bounded reassembly and MTU-aware writes. Single-flight vendor queries, per-command payload matchers, timeouts and late-response handling. Subscriptions are installed before requests. Disconnection fails pending requests, invalidates live data and stops measurement/stream state. Reads validate lengths and supported enum/range values; unknown extensions are retained, never silently decoded as known. Weekday masks use Sunday bit0. Alarm editing preserves other slots and uses legacy 0x11 on the tested firmware. Manual oxygen AB/02 and stress B9/11/02 are separate from zero-filled automatic history. Source timestamps and received times remain separate. History deduplicates by device/type/source timestamp/record identity, not value alone.

## Safety and privacy boundaries

User-chosen writes only. Serialize commands; snapshot settings before changes; read back results and report mismatches. Measurement controls stop on disconnect/shutdown where possible. No reset, firmware flashing, unbinding, contacts or call audio in the first milestone. No arbitrary URL navigation or shell commands from renderer IPC. Export uses a save dialog and explicit chosen records; developer diagnostics omit device identifiers by default. Device association and records stay local. Automatic reconnect is bounded and only targets the user's selected device, never every scan result.

## Extensibility and licensing

Document the common API and wire profile; include synthetic fixtures, adapter template, contributor guide and capability validation checklist. New adapters register through a static registry; no remote plugin execution. Application code is AGPL-3.0-or-later; protocol/interface documentation and synthetic fixtures are CC0-1.0 so independent implementations can use the specification. Preserve provenance for Gadgetbridge reference material and original headers if reused; do not ship vendor binaries, extracted strings or personal captures.

## Acceptance and validation

Codec tests cover fragmentation, invalid lengths/resynchronization, signed/unsigned data, alarms, language, manual records, workout fields and missing markers. Fake transport tests cover query correlation, timeout, disconnect, serial writes and rollback/readback failure. Store tests cover deduplication and isolation. IPC validates command names/types/ranges and sender. Renderer handles connection loss and capability gaps. Build/type/lint/test checks must pass. Exercise supported read operations against the real Mac/watch; no surprise writes during smoke validation. Produce a runnable macOS application with bundled backend; provide Windows build configuration and CI, but label Windows BLE and installer as untested until run there. Do not publish releases or repositories without user instruction.

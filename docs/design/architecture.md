# Architecture

A sandboxed React/TypeScript renderer runs inside Electron. A narrow, validated preload bridge exposes named operations. The Python asyncio sidecar communicates over newline JSON on inherited stdio; Bleak provides CoreBluetooth/WinRT. SQLite stores local observations. There is no HTTP server, vendor SDK or account service.

Pure codecs describe wire bytes; adapters handle model-specific operations; the service owns device selection, local storage, firmware gates and the common command API. Unknown watches remain inspection-only.

Custom images are decoded/cropped in the renderer and encoded as original+preview RGB565. Bounded staging pieces cross IPC. The backend validates exact size and launches a cancellable task, blocks competing watch operations, honors logical-chunk negotiation, verifies CRC and commits. Failures attempt protocol abort and restoration of the prior face selection while connected; this does not promise backup/restoration of a prior custom image.

Capability status distinguishes verified, partial, unverified and unavailable functionality. Synthetic preview is explicit and read-only. Account-free onboarding is established on a reset O20 with previously used host state; completely fresh host support remains to be validated.

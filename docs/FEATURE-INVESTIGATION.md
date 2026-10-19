# Additional O20 features — investigation, 2026-10-19

Original documentation: CC0-1.0. These findings extend the protocol notes; they are **not new buttons in version 0.1.0**. Tested device: itel ISW-O20 / MOYOUNG-V2 / software O20-7LH2-2.1.12. No login or vendor library was used by the BLE probes.

## Results

| Question | Finding | Confidence / remaining work |
|---|---|---|
| Contacts | Watch advertises 8 slots, name field limit60 bytes, avatar width/height0, protocol version1. A dummy contact was added, count changed0→1, then removed, count restored0. | Capacity query and count changes verified. User reported no contact appeared; visible usable contact creation is NOT established. A complete contact-list readback was not located. |
| Custom backgrounds | Existing built-in face selection works. Custom image transfer is present in the shipped SDK and declared for O20. Query39 reports original240×284 pixels and preview140×163. | Subsequent test succeeded: raw RGB565 image+preview uploaded with matched whole-file CRC; user confirmed correct rendering. See O20-CUSTOM-BACKGROUNDS.md. |
| Memory | Query5A08 reports a512000-byte (500KiB) UDT/object transfer maximum. | **Not total RAM, total flash or free storage.** Those remain unknown. |
| Movement reminders | Schedule query83 returns four fields: period, step threshold, start hour, end hour. Period changed60→61 and restored60; all fields read back correctly. | Stored schedule write verified; physical reminder timing was not tested. |
| Water reminders | Legacy query8701 returns settings; newer BB040601 does not answer in this window. | Disabled schedule changed, read back, then fully restored; physical alerts untested. |
| Music files | SDK contains local-music/filesystem model classes, but no corroborated usable request/parser was located in this build. | Do not claim file upload or on-watch playback storage. |
| Music remote | Related Moyoung implementation defines metadata/status and incoming transport-control events. | User reported nothing on Music; no music-control event captured. O20 remote-control behavior remains unresolved. No audio player integration executed. |
| Named/calendar reminders | A related model implements B9/08 calendar writes. | O20 support untested. No clear-all calendar command sent. Desktop-scheduled text alerts are a possible companion feature; they would require the app running and connected. |

Water validation: baseline `01000000000000` changed to `01000900043cc8`, then returned exactly to baseline. Enable remained0 throughout. This establishes stored schedule access without activating timed alerts.

Music validation: a55-second passive listening window completed. The watch emitted a weather-request event64, but no67 music-control event was captured. The user later reported “nothing on music.” Timing and the exact watch-screen/button behavior were not established, so this does not show that the watch lacks remote music controls.

## Contacts wire profile

Wrap command/payload in normal FE EA framing. Query F2 payload00 -> `00 max avatarWidth avatarHeight [nameLimit]`; SDK defaults nameLimit20 if omitted. Query payloadEE -> `EE count`; payload05 -> `05 version`.

Single add commandF2:

`02 id 01 avatarWidth avatarHeight 00 00 00 00 nameField phoneField`

Name is UTF-8 in a fixed `nameLimit`-byte field, terminated and zero-padded; truncate at a valid UTF-8 boundary to at most limit−1 bytes. Phone is ASCII in a20-byte field, at most19 bytes plus termination/padding. Single delete commandF2 payload `01 id`. Neither operation is a whole-address-book sync. Do not clear all contacts as a capability probe.

The guarded experiment checked the exact expected profile and count0 before writing ID0, name `OW TEST`, dummy number `000`. The final count was0. Count alone is insufficient to verify exact text encoding; the phone was never dialed. The user later reported “no contact appeared.” The dummy was visible to protocol queries for only20seconds before removal; overlap with the user observation is unknown. Treat usable/visible contact creation as unresolved, not verified.

## Reminder queries

- Query83 -> four raw bytes; setter73 with the same four fields. Baseline `3c320a16` changed to `3d320a16`, then original restored.
- Query87 payload01 -> `01 enabled startHour startMinute reminderCount interval waterIntake`. Setter77 uses the same subtype and fields. SDK model names establish the field mapping; time/volume units and physical behavior need corroboration.
- Query87 payload02 -> `02 00 b4`: raw heart-rate-reminder reply, consistent with the SDK state/maximum model; exact semantics and setter untested.
- Query87 payload03 returned empty; handwashing reminders not established.

## Face / storage queries

- Query39 extension: uint16BE originalWidth at37:39, previewWidth39:41, originalHeight41:43, previewHeight43:45. The O20 returns240,140,284,163.
- BA payload02 reply `02 35 03`: market API version53, function version3.
- 5A payload08 reply: subtype08, uint32LE max object/UDT size at1:5, then observed ASCII `API_V1.0.0`. Maximum512000 bytes is not an inventory of available storage.
- B4 payload10 returns `100000000000d0070062`; keep raw. Another512000-looking field is not sufficient to identify capacity semantics.
- B4 payload26/00,26/01,26/02,26/04,26/05 timed out. JL707 face-memory parsing cannot be applied to the older O20 simply because that path exists in the SDK.
- Query84 returned an empty payload; this is not proof that custom faces are unsupported.

The older SDK `CRPScreen` path initiates an image transfer through command6E with a four-byte length, handles indexed chunks (candidate256-byte data slices), retries and a CRC seededFEEA. Some packet headers differ by API version. The original image packing, preview ordering, transfer characteristic, terminal response and abort semantics still need reconstruction. No firmware operation was attempted. Subsequent custom-background transfer and user rendering confirmation are documented in [O20 custom backgrounds](O20-CUSTOM-BACKGROUNDS.md).

## Music remote candidate

Related Gadgetbridge Moyoung code sends command44 with `00 + track` or `01 + artist`, command7B with playing1/paused0. Incoming67 payload values map to play/pause0, previous1, next2, volume up4, volume down5, play6 and pause7. Value3 is call rejection, so handlers must not treat every67 event as music. No Mac playback action was taken during investigation.

## Evidence / reproducibility

The unencrypted shipped CRPSmartBand binary has SHA256 `a10e908ebf1ec2bcb59ad72e99e7e8f811918c5f10bd04cfe996f478125cf824`. Queries were derived from saved `otool` disassembly plus static Swift arrays in the same binary, then exercised independently through Bleak. Native REA analysis was unavailable because its prior Hopper resource cleanup could not be confirmed; no REA decompilation success is claimed.

Relevant SDK addresses: contact queries static arrays1a3ae8/1a3c08/1a3c38, contact parser67310, add5b9a0, delete5c204; UDT parser6e024; face dimensions6d6fc; market API parser6c46c; image transfer25bd4 and24dfc. Raw local artifacts are ignored under research/ and intentionally absent from the public source archive.

Related source: [Gadgetbridge](https://codeberg.org/Freeyourgadget/Gadgetbridge), MoyoungConstants.java and MoyoungDeviceSupport.java. Their behavior is evidence for that implementation, not automatic O20 hardware validation. The [official itel O20 page](https://www.itel-life.com/products/smart-life/wear/watch-o2o) was checked; its accessible text did not establish RAM/flash capacity. Shipped app-profile method IDs are a different abstraction and must not be sent directly as BLE command bytes.

## Follow-up priorities after user feedback

Repeat contact validation with an explicitly synchronized observation window; preserve the dummy until the user reports its presence/absence, then delete only that test ID and verify the baseline. Investigate whether dummy-number validation, ID/index semantics, a commit operation or watch UI refresh is required; these are hypotheses, not findings. For music, establish whether the watch opens a controller or shows a disconnected state, then capture button events in the same observation window. Do not infer support from SDK method names or from a changed contact count alone.

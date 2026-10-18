# O20 protocol, draft 0.1

Documentation license: CC0-1.0. Derived from local runtime experiments and shipped-app inspection; this is a compatibility description, not vendor certification. Only the first watch profile is implemented.

BLE service FEEA, write FEE2, notification FEE3; activity FEE1. Standard UUID expansion is `0000xxxx-0000-1000-8000-00805f9b34fb`. Standard battery 2A19, manufacturer 2A29, firmware 2A26, software 2A28, heart rate 2A37.

Frame: `FE EA (20 | high-length-nibble) low-length command payload`. Length includes the five header bytes. Accept the observed legacy header variant 10. Reassemble notification fragments and split writes to the negotiated characteristic capacity. Do not assume one BLE callback equals one frame.

| Operation | Query / set | Payload |
|---|---|---|
| Goal | 26 / 16 | reply uint32 LE, setter uint32 BE |
| Time format | 27 / 17 | raw scalar |
| Units | 2A / 1A | raw scalar |
| Language | 2B / 1B | English 0; reply may include extension |
| Raise wrist | 28 / 18 | raw scalar |
| Sedentary | 2D / 1D | raw scalar |
| Watch face | 29 / 19 | only 2 and 3 validated |
| Alarms | 21 / 11 | 3 slots × 8 bytes; setter one slot |
| HR | 6D | 00 start, FF stop; numbers on 2A37 |
| Oxygen | 6B | 00 start, FF stop; fresh numeric result unverified |
| Saved oxygen | AB | request 02; reply 02,count,(value,ts32LE)* |
| Saved stress | B9 | request 11 02; reply 11 02,count,(value,ts32LE)* |
| Workouts | B2 | 00 list, 02 slot details, 04 slot page16LE HR |
| Local message | 41 | 01 then UTF-8 text |
| Find watch | 61 | empty; physically confirmed audible |

Alarm bytes: slot, enabled, repeat mode, hour, minute, two date bytes, weekday mask. Sunday is bit 0. Keep the complete other slots unchanged. Current app exposes weekly alarms and clear. Read-back tests verified legacy writes; the newer alarm format was not established.

Activity contains three uint24LE fields: steps, distance raw, calories raw. Steps were visually confirmed. Distance/calorie scales remain provisional. Manual oxygen and stress records have one value byte and a uint32LE source timestamp; current timestamp interpretation uses UTC+08 and is labeled in code. Periodic stress storage is separate from manual readings.

B2 list has subtype byte and six 5-byte entries. Detail payload is 30 bytes: subtype/slot, start at offset 2, end at 6, candidate active seconds uint16 at 10, sport code at 13, steps uint32 at 14, distance uint32 at 18, calories uint16 at 22. Other bytes remain unknown. HR pages carry subtype/slot/page and sample bytes; FFFF is terminal and zero samples are missing, not zero BPM. Current app retrieves the first page only.

Repository tests use fabricated records. Personal observations, original binary artifacts and raw traffic are intentionally outside the public source tree under ignored `research/`.

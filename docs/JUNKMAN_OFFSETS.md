# Junkman reverse notes (PC v1.3)

These notes document what was verified in-game for NFS MW (2005) PC v1.3 saves.

## Constants (PC v1.3)
- `saved_data_start (abs)` = `0x34`
- `slot_base_rel (from saved_data)` = `0x5735`
- `slot_base_abs (from file start)` = `0x5769`
- `slot_stride` = `0x0C` (12 bytes)
- `slot_count` = `59`

## Slot structure (12 bytes)
- `+0x00`: `Type_ID` (u8)
- `+0x08`: `Count` (u8) → we write `1`
- remaining bytes: `0x00`

Filled slot layout:
`[type, 00 00 00 00 00 00 00, 01, 00 00 00]`

Empty slot:
all 12 bytes are `00`.

## Counting model
Tokens behave like an **inventory slot array**, not a single counter.
- 1 token = 1 occupied slot
- quantity for a `Type_ID` = number of slots with that `Type_ID`

`set_count(type_id, n)`:
- remove extra slots of that id if current > n
- fill empty slots if current < n

## Known Type_IDs (verified)
Performance:
1 Brakes
2 Engine
3 NOS
4 Turbo
5 Suspension
6 Tires
7 Transmission

Visual:
8 Body
9 Hood
10 Spoiler
11 Rims
12 Roof
13 Gauge
14 Vinyl
15 Decal
16 Paint

Police/Markers (partial):
17 Out of Jail (verified)
20 Imp. Strike (verified)

Unknown:
The rest of ID's up until 30

## Testing method
Verified IDs by:
1) setting Want=1 for a single ID
2) Apply → Save+backup
3) checking in-game behavior
(if there's a better and easier way reach out)

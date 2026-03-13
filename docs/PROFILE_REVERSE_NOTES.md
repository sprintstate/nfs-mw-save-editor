# Profile reverse notes (PC v1.3)

These notes document how the Profile / Rap Sheet car data was reverse-engineered for
NFS Most Wanted (2005) PC v1.3 saves (`63,596` bytes).

Main reference saves used during validation:
- `Save1`
- `Save2`
- `lowdiff`

Forum reference:
- old Cheat Engine threads with the car list and save-structure hints

## Goal

Find a reliable way to resolve:
- per-car `Bounty`
- per-car `Escaped`
- per-car `Busted`
- real vehicle name for each Profile garage card

without guessing from a fake enum or UI order.

## Step 1: confirm the pursuit / bounty block

The first confirmed block was the per-car pursuit block:

- base: `0xE2ED`
- stride: `0x38`

Record layout:
- `+0x10` -> `u32 bounty`
- `+0x14` -> `u16 escaped`
- `+0x16` -> `u16 busted`

Detection invariants used in code:
- bytes `1:4 == CD 03 00`
- bytes `8:12 == 00 00 CD CD`

Observed results:
- `Save1`: `13` valid records, total bounty `12,190,486`
- `Save2`: `17` valid records, total bounty `14,926,350`
- `lowdiff`: `7` valid records, total bounty `200,150`

This block is the source of truth for:
- bounty editing
- escaped total
- busted total
- computed total bounty / rating

## Step 2: reject the fake global bounty idea

An earlier hypothesis treated a single global field as the main bounty source.
That did not hold up on real saves.

The decisive clue was:
- summing `+0x10` across valid pursuit records matched the in-game total bounty

This made the correct model:
- total bounty is derived from per-car pursuit records
- writes should target the pursuit record, not a separate global total field

## Step 3: find the real car identity block

The second major breakthrough was a separate career vehicle block:

- base: `0x6219`
- stride: `0x14`

Record layout:
- `+0x00` -> `u32 car number`
- `+0x04` -> `8-byte car signature`
- `+0x0C` -> `u16 flags`
- `+0x0E` -> `u16 flags2 / unknown`
- `+0x10` -> `u8 parts slot`
- `+0x11` -> `u8 career slot`
- `+0x12` -> `CD CD`

Important behavior:
- the block is larger than the active car list
- active records are at the front
- the tail is filler:
  - `car number = 0xFFFFFFFF`
  - signature = `00 00 00 00 00 00 00 00`
  - `career_slot = 0xFF`

Active record filter:
- `car_number != 0xFFFFFFFF`
- signature is not all zeroes
- `career_slot != 0xFF`

Observed results:
- `DIMAA`: `13` active car records
- `Sprint`: `17` active car records

## Step 4: link both layers through `career_slot`

The key relation is:

`career vehicle record.career_slot == pursuit record index`

In practice:
- read active car records from `0x6219`
- read pursuit records from `0xE2ED`
- join them by `career_slot`

This matched cleanly on the validation saves.

Examples from `Save2`:
- slot `0` -> `Chevrolet Cobalt SS` -> bounty `9,427,250`
- slot `1` -> `VW Golf GTI` -> bounty `29,950`
- slot `2` -> `Lexus IS300` -> bounty `51,750`
- slot `10` -> `Lamborghini Gallardo` -> bounty `270,550`
- slot `15` -> `BMW M3 GTR` -> bounty `2,390,000`

Examples from `Save1`:
- slot `0` -> `Chevrolet Cobalt SS`
- slot `7` -> `Lamborghini Gallardo`
- slot `12` -> `Mercedes SLR McLaren`

This is the relation now used by the editor.

## Step 5: resolve car names by exact 8-byte signature

Vehicle names are resolved by exact signature match, not by the old temporary `car_id`
display and not by a hand-made small enum.

Resolver rule:
- exact `8-byte signature -> model name`

Examples:
- `95 40 78 5A 95 40 78 5A` -> `Chevrolet Cobalt SS`
- `34 34 F1 66 34 34 F1 66` -> `Toyota Supra`
- `0B C4 2C 7B 0B C4 2C 7B` -> `Lamborghini Gallardo`
- `92 99 86 C4 D4 3D 06 67` -> `Porsche Carrera GT`
- `BB D9 2A E3 BB D9 2A E3` -> `Mercedes SLR McLaren`
- `4E 4A CC 23 B3 5F 08 4E` -> `BMW M3 GTR`

The forum car list was used as the initial source, then checked against real save data.

## Resulting implementation model

The editor now treats Profile data as two joined layers:

1. `PursuitRecord`
   - bounty
   - escaped
   - busted
   - source block: `0xE2ED`

2. `CareerVehicleRecord`
   - car number
   - signature
   - flags
   - parts slot
   - career slot
   - source block: `0x6219`

3. `ResolvedGarageEntry`
   - built by joining both layers through `career_slot`
   - used by the Profile UI

Write policy:
- bounty edits write only into the pursuit block
- car identity data is read-only in the current implementation

## Known limitations

Still not fully resolved:
- exact meaning of flags at `+0x0C`
- exact meaning of field at `+0x0E`
- whether `parts_slot` has a useful UI meaning yet
- how current car / active career car is marked in these structures

Current fallback policy:
- if a future save has no unique car-record match for a pursuit slot, the UI should
  show an honest fallback instead of guessing a vehicle name

## Practical validation summary

Validated against real saves:
- `Save1`
- `Save2`
- `lowdiff`

Confirmed in code:
- Profile vehicle labels can be resolved from signatures
- pursuit totals remain correct
- bounty editing still targets the pursuit block only
- filler records in the car block are ignored

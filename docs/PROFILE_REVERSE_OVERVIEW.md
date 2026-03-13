# How the Profile data was reversed

This note is a higher-level summary of how the Profile / Rap Sheet data model was
understood for **Need for Speed: Most Wanted (2005)** PC v1.3 saves.

If you need the exact offsets and record layouts, see
[`PROFILE_REVERSE_NOTES.md`](/docs/PROFILE_REVERSE_NOTES.md).

## What we wanted to solve

The Profile page needed to show and edit real per-car pursuit data:
- `Bounty`
- `Escaped`
- `Busted`
- correct vehicle identity for each card

At first, only the bounty side was clear. The missing piece was how to tell which
rap-sheet entry belonged to which actual car.

## The first breakthrough: bounty is stored per car

Reverse checks on real saves showed that the Profile total bounty is not best modeled
as one global number.

Instead, the save contains a repeated pursuit block where each record stores:
- bounty
- escapes
- busts

The decisive clue was simple:
- summing the per-record bounty values matched the in-game total bounty exactly

That changed the model completely:
- total bounty is computed
- the editable source of truth is the per-car pursuit record

## The second breakthrough: there is a separate car identity block

The pursuit block alone was not enough to label cards honestly.

The next step was finding a different block in the save that stores actual vehicle
identity. That block contains:
- a car number
- an 8-byte vehicle signature
- some still-not-fully-understood flags
- a `career_slot`

This was the key structural clue: the game appears to keep pursuit stats and vehicle
identity as two different layers.

## The link that unlocked everything: `career_slot`

Once both blocks were known, the important pattern became clear:

- each active vehicle record has a `career_slot`
- that `career_slot` matches the index of the corresponding pursuit record

In other words:
- vehicle block tells us **what car it is**
- pursuit block tells us **what bounty / escapes / busts belong to it**
- `career_slot` tells us **which records belong together**

That was the missing join.

## Why the old fake mapping had to go

Earlier UI work temporarily showed a raw `Car ID` field, and a guessed static mapping
was considered at one point. That approach was not good enough.

The reason is that the real vehicle identity is not coming from a tiny simple enum.
It is coming from the separate vehicle block and its exact 8-byte signature.

So the correct resolver became:
- read the vehicle signature
- match that exact signature to a known car
- only then show the vehicle name

This is why the current implementation resolves names from exact signature matches
instead of guessing from a small integer.

## What is confirmed now

The editor now has a confirmed model for PC v1.3 saves:

1. A pursuit block stores per-car bounty, escapes, and busts.
2. A separate vehicle block stores car identity data.
3. `career_slot` links those two layers together.
4. Vehicle names can be resolved from exact 8-byte signatures.
5. Bounty editing should continue writing only to the pursuit block.

That is enough to power the current Profile garage cards honestly.

## What is still unknown

Some fields are still not fully explained:
- the exact meaning of the vehicle flags
- the exact meaning of the second bitfield / unknown field
- how the game marks the current active career car

These do not block the current Profile feature, but they are still open reverse
engineering targets.

## Practical takeaway

The important outcome is not just "we found more offsets".

The real result is that the Profile page now stands on a coherent save model:
- pursuit stats come from the pursuit records
- car identity comes from the vehicle records
- the UI joins them through `career_slot`

That means the editor is no longer guessing which car a pursuit card belongs to.

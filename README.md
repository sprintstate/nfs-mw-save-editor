# NFS MW Junkman Editor (PC v1.3)

A save editor for **Need for Speed: Most Wanted (2005)** focused on **Junkman Tokens**.
Set exact token quantities (per type), apply safely, and save with automatic backup + integrity recomputation.

Supported: **PC v1.3 save format**

---

## Features

### Junkman Inventory (main)
- Pick **specific tokens** and set desired counts (Want)
- Apply changes in memory (**Apply**) and write to disk only via **Save + backup**
- **Preserve Unknown** (default ON): keeps unknown token types intact to avoid breaking saves
- Presets: **Load / Save / Export** (current “Have” state)

### Safety & Integrity
- Creates a `.bak` backup before writing
- Recomputes required integrity fields (checksums/hashes) so the game accepts the save

---

## Quick Start (Users)

1. Download `release.zip` from **GitHub Releases** and extract it.
2. Run `NFS_MW_Junkman_Editor.exe`.
3. Click **Open** and select your save file.
4. In **Junkman**, set your desired quantities (Want).
5. Click **Apply (memory)**.
6. Click **Save + backup** (writes file + creates `.bak`).

---

## Token catalog location (names)

Token names are stored in **your AppData** (per-user), so the app can write safely even when installed in protected folders.

Open it from the app: **Settings → Open folder**.

---

## Limitations
- Offsets and inventory logic are for **PC v1.3**.
- Some IDs may remain **Unknown** until fully confirmed.
- PyInstaller builds may trigger false positives in some antivirus products.

---

## Build from source

See: [`docs/BUILD.md`](docs/BUILD.md)

---

## Reverse notes (Junkman)

See: [`docs/JUNKMAN_OFFSETS.md`](docs/JUNKMAN_OFFSETS.md)

---

## Disclaimer
Not affiliated with EA/Black Box. Use at your own risk. Keep backups of your saves.

# NFS Most Wanted 2005 — Save Editor

Desktop save editor for **Need for Speed: Most Wanted (2005)** on PC (v1.3).  
Built with **Python 3** and **PySide6**. Dark theme inspired by the game's aesthetic.

---

## Features

### Junkman Inventory Editor
- Edit all **22 token types** — Performance (Brakes, Engine, NOS, Turbo…), Visual (Body, Hood, Spoiler…), Police (Out of Jail, Impound Release…)
- **Quick actions** — unlock all Performance / Visual / All tokens in one click
- Search and filter tokens by category
- Real-time "Have" vs "Want" comparison with unsaved changes indicator
- Adjustable per-token counts via spinbox or +/− buttons

### Save Integrity
- Automatic **MD5 hash** verification (supports `md5_saved_data` and `md5_all_minus_tail` schemes)
- **EA CRC32** checksum validation for all 3 header blocks
- File size validation against stored size field
- One-click **Fix checksums** to repair integrity after edits

### Junkman Slot Detection
- **Auto-detection** of the Junkman slot array within saved data (stride `0x0C`)
- Heuristic scanning with configurable range (`0x5400`–`0x5B00` relative to saved data)
- Shows free/total slot capacity

### Presets & Catalog
- Load / save token presets as JSON files
- Export current "Have" counts as a preset
- Editable **token catalog** (`token_catalog.json`) — rename tokens, add categories
- Catalog stored in `%APPDATA%/NFS_MW_Junkman_Editor/` for persistence across updates

### Settings
- **Safe mode** (max 63 per token) / **Advanced mode** (max 255)
- Preserve Unknown tokens on apply
- Clear Unknown tokens (with confirmation)

### Other
- Automatic **backup** on every save (`*.bak`)
- Profile / integrity info page
- Portable — supports **PyInstaller** packaging

---

## Installation

### From source

```bash
# Clone the repo
git clone https://github.com/sprintstate/nfs-mw-save-editor.git
cd nfs-mw-save-editor/nfs_mw_save_editor

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Linux / macOS

# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

### From release

Download the latest `.exe` from [Releases](../../releases) — no Python installation required.

---

## Usage

1. Click **Open save** and select your NFS MW save file  
   (default location: `%APPDATA%\NFS Most Wanted\`)
2. Adjust token counts in the **Junkman** tab using spinboxes or quick-action buttons
3. Click **Apply (memory)** to stage changes
4. Click **Save + backup** to write changes to disk (original file backed up as `.bak`)
5. Use **Fix checksums** if the game does not accept the modified save

> **Tip:** Use `Settings → Safe max (≤ 63)` to avoid potential game instability from high token counts.

---

## Project Structure

```
nfs_mw_save_editor/
├── main.py                 # Application entry point
├── resources.py            # PyInstaller-compatible resource loader
├── requirements.txt        # PySide6>=6.5
├── token_catalog.json      # Default token definitions (22 types)
│
├── core/                   # Save file logic (no Qt dependency)
│   ├── savefile.py         # SaveFile class — load, validate, fix, read/write slots
│   ├── checksums.py        # EA CRC32 implementation (poly 0x04C11DB7)
│   ├── junkman.py          # JunkmanInventory — slot detection, read/write, apply counts
│   ├── diff.py             # Byte-level and u32-aligned diff utilities
│   └── patch.py            # Low-level read/write helpers (u32, u8, bitmask)
│
├── ui/                     # PySide6 interface
│   ├── main_window.py      # MainWindow — all pages (Junkman, Profile, Presets, Settings, About)
│   └── theme.py            # Dark green theme (QSS stylesheet)
│
└── assets/
    └── icon.ico            # Application icon
```

---

## Save File Format (PC v1.3)

| Offset | Size | Description |
|--------|------|-------------|
| `0x00` | 4 | Magic: `MC02` |
| `0x04` | 4 | File size (LE) |
| `0x10` | 4 | CRC block 1 |
| `0x14` | 4 | CRC data |
| `0x18` | 4 | CRC block 2 |
| `0x34` | … | Saved data start |
| tail 16 | 16 | MD5 hash |

**Junkman slot layout** (12 bytes per slot):

| Byte | Description |
|------|-------------|
| `+0x00` | Token type ID (1–22 known) |
| `+0x01..0x07` | Padding (zero) |
| `+0x08` | Count (always 1 for filled slot, 0 for empty) |
| `+0x09..0x0B` | Padding (zero) |

---

## Requirements

- **Python** ≥ 3.10
- **PySide6** ≥ 6.5

---

## License

This project is provided as-is for educational and personal use.  
NFS Most Wanted is a trademark of Electronic Arts.

# NFS Most Wanted 2005 - Save Editor

Desktop save editor for **Need for Speed: Most Wanted (2005)** on PC (v1.3).
Built with **Python 3** and **PySide6**. Dark blue UI theme.

---

## Features

### Junkman Inventory Editor
- Edit all **22 token types** - Performance (Brakes, Engine, NOS, Turbo...), Visual (Body, Hood, Spoiler...), Police (Out of Jail, Impound Release...)
- **Card grid** layout with icons extracted from the original game
- **Quick actions** - unlock all Performance / Visual / All tokens in one click
- Search and filter tokens by category (with category icons)
- Real-time "Have" vs "Want" comparison with unsaved changes indicator
- Per-token counts via spinbox, slider, or +/- buttons
- Performance progress bar in footer (`X/7 Performance`)

### Profile / Rap Sheet Editor
- **Money** - editable field (u32) with current-value display
- **Total Bounty**, **Escapes**, **Busts** - read-only summary stats shown in a horizontal stat strip with rounded badge styling
- **Garage card grid** - scrollable, adaptive 1-3 column layout:
  - Each card shows the **resolved vehicle name** (8-byte signature -> model name via `core/cars.py`)
  - Per-car **bounty editor** with current-value display
  - Per-slot **Escaped** and **Busted** read-only stats
  - Changed-state highlight on pending edits
- Toggle to show/hide empty valid garage slots (via Settings)
- Optional **Integrity panel** with MD5/CRC validation details (hidden by default, toggle in Settings)

### Save Integrity
- Automatic **MD5 hash** verification (supports `md5_saved_data` and `md5_all_minus_tail` schemes)
- **EA CRC32** checksum validation for all 3 header blocks
- File size validation against stored size field
- One-click **Fix checksums** to repair integrity after edits

### Junkman Slot Detection
- **Auto-detection** of the Junkman slot array within saved data (stride `0x0C`)
- Heuristic scanning with configurable range (`0x5400`-`0x5B00` relative to saved data)
- Shows free/total slot capacity with real-time projected preview

### Presets and Catalog
- Load / save token presets as JSON files
- Export current "Have" counts as a preset
- Editable **token catalog** (`token_catalog.json`) - rename tokens, add categories
- Catalog stored in `%APPDATA%/NFS_MW_Junkman_Editor/` for persistence across updates

### Settings
- **Default cap <= 10** per token (practical mode)
- Optional **Unlock limit (<= 63)** toggle for advanced users
- Preserve or clear Unknown tokens on apply (with confirmation)
- **Show empty valid garage slots** - display all pursuit-block entries on Profile, not just occupied ones
- **Show Integrity panel** - toggle the Integrity section on the Profile page

### UX
- **Keyboard shortcuts**: `Ctrl+O` open, `Ctrl+S` save, `Ctrl+Z` reset
- **Drag and drop** save files onto the window to open
- **Toast notifications** for non-blocking success feedback
- **Fade-in animations** on card grid, hover effects on cards
- About page with version info, author credit, and shortcuts reference

### Other
- Automatic **backup** on every save (`*.bak`)
- Portable - supports **PyInstaller** packaging

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

Download the latest build from [Releases](https://github.com/sprintstate/nfs-mw-save-editor/releases) - no Python installation required.

---

## Usage

1. Click **Open save** (or press `Ctrl+O`, or drag a save file onto the window)
   Default save location: `%APPDATA%\NFS Most Wanted\`
2. Adjust token counts in the **Junkman** tab using spinboxes, sliders, or quick-action buttons
3. Edit **Money** and per-car **Bounty** values in the **Profile** tab
4. Click **Apply (memory)** to stage changes
5. Click **Save + backup** (or press `Ctrl+S`) to write changes to disk (original file backed up as `.bak`)
6. Use **Fix checksums** if the game does not accept the modified save

> **Tip:** The default per-token cap is 10 - enable `Settings -> Unlock limit (<= 63)` for higher values.

---

## Project Structure

```text
nfs_mw_save_editor/
├── main.py                 # Application entry point
├── resources.py            # PyInstaller-compatible resource loader
├── requirements.txt        # PySide6>=6.5
├── token_catalog.json      # Default token definitions (22 types)
│
├── core/                   # Save file logic (no Qt dependency)
│   ├── savefile.py         # SaveFile - load, validate, fix, read/write slots
│   ├── checksums.py        # EA CRC32 implementation (poly 0x04C11DB7)
│   ├── junkman.py          # JunkmanInventory - slot detection, apply counts
│   ├── cars.py             # Vehicle name resolver (8-byte signature -> model name)
│   ├── diff.py             # Byte-level diff utilities
│   └── patch.py            # Low-level read/write helpers (u32, u8)
│
├── ui/                     # PySide6 interface
│   ├── main_window.py      # MainWindow - all pages and coordination
│   ├── widgets.py          # TokenCard, WantSpinBox, ToastNotification
│   ├── icon_map.py         # Centralized icon path mappings
│   └── theme.py            # Dark blue theme (QSS stylesheet)
│
└── assets/
    ├── icon.ico            # Application icon
    ├── icon.png            # Application icon (PNG)
    └── icons/              # Token, nav, and category icons (from original game)
        ├── perf/           # Performance token icons (7 files)
        ├── vis/            # Visual token icons (9 files)
        ├── pol/            # Police token icons (5 files)
        ├── nav/            # Sidebar navigation icons (5 files + unknown.png)
        └── cat/            # Category filter icons (4 files)
```

`docs/` (repo root) contains reverse-engineering notes: `JUNKMAN_OFFSETS.md`, `PROFILE_REVERSE_NOTES.md`, `PROFILE_REVERSE_OVERVIEW.md`. Not included in releases.

`dev_assets/` (repo root) contains developer-only files: original DDS textures, icon prep scripts, and archived legacy code. Not included in releases.

---

## Save File Format (PC v1.3)

### Header and integrity

| Offset | Size | Description |
|--------|------|-------------|
| `0x00` | 4 | Magic: `MC02` |
| `0x04` | 4 | File size (LE) |
| `0x10` | 4 | CRC block 1 |
| `0x14` | 4 | CRC data |
| `0x18` | 4 | CRC block 2 |
| `0x34` | ... | Saved data start |
| tail 16 | 16 | MD5 hash |

### Junkman slot layout (12 bytes per slot)

| Byte | Description |
|------|-------------|
| `+0x00` | Token type ID (1-22 known) |
| `+0x01..0x07` | Padding (zero) |
| `+0x08` | Count (always 1 for filled slot, 0 for empty) |
| `+0x09..0x0B` | Padding (zero) |

### Profile / Rap Sheet data

The Profile data model spans two key blocks within saved data:

- **Pursuit block** (parsed from the confirmed pursuit-record region): contains per-slot bounty (u32), escaped count, busted count, and a `career_slot` index linking to the career vehicle record.
- **Career vehicle block** (starts at offset `0x6219` from saved data): holds 8-byte vehicle signatures that resolve to real car model names.
- **Money** is stored as a global u32 field at a fixed offset.

Vehicle names are resolved by joining pursuit records to career records via `career_slot`, then matching the 8-byte signature against a known dictionary in `core/cars.py`.

> For full offset tables and record layouts, see [`docs/PROFILE_REVERSE_NOTES.md`](docs/PROFILE_REVERSE_NOTES.md).
> For a higher-level explanation, see [`docs/PROFILE_REVERSE_OVERVIEW.md`](docs/PROFILE_REVERSE_OVERVIEW.md).

---

## Requirements

- **Python** >= 3.10
- **PySide6** >= 6.5

---

## License

This project is provided as-is for educational and personal use.
NFS Most Wanted is a trademark of Electronic Arts.

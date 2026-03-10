"""
NFS MW 2005 - Junkman Inventory Editor (main window)

The main window only keeps:
  - header (Open / Save / Fix + file path)
  - sidebar navigation with icons
  - QStackedWidget (pages are built here for simplicity)
  - footer (free slots, Apply, Save)
  - state coordination (refresh_state, apply, save, etc.)

Token cards are rendered as a grid of TokenCard widgets (see widgets.py).
"""
from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRegularExpression, QSize, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QIcon, QImage, QKeySequence, QPixmap, QRegularExpressionValidator, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.junkman import JunkmanInventory
from core.savefile import GarageSlot, SaveFile
from resources import resource_path
from ui.icon_map import cat_icon_path, nav_icon_path
from ui.widgets import TokenCard, ToastNotification


    # -- Constants -------------------------------------------------------
CAT_LIST = ["All", "Performance", "Visual", "Police", "Unknown"]
APP_NAME = "NFS_MW_Junkman_Editor"
CATALOG_FILENAME = "token_catalog.json"
SAFE_TYPE_MIN = 1
SAFE_TYPE_MAX = 22
PERF_IDS = (1, 2, 3, 4, 5, 6, 7)
PERF_TOTAL = 7
DEFAULT_CARDS_PER_ROW = 3
MAX_CARDS_PER_ROW = 4
U32_MAX = 0xFFFFFFFF
PROFILE_SIDEBAR_WIDTH = 360
GARAGE_TILE_MIN_WIDTH = 230
GARAGE_TILE_MAX_COLUMNS = 3


    # -- Helpers ---------------------------------------------------------

def _appdata_dir() -> Path:
    base = os.getenv("APPDATA")
    if base:
        return Path(base)
    return Path.home() / "AppData" / "Roaming"


def _user_catalog_path() -> Path:
    return _appdata_dir() / APP_NAME / CATALOG_FILENAME


def _default_catalog_path() -> Path:
    return resource_path(CATALOG_FILENAME)


def _ensure_user_catalog_path() -> Path:
    user_path = _user_catalog_path()
    if user_path.exists():
        return user_path
    user_path.parent.mkdir(parents=True, exist_ok=True)
    default_path = _default_catalog_path()
    if default_path.exists():
        try:
            shutil.copyfile(default_path, user_path)
            return user_path
        except Exception:
            pass
    return user_path


@dataclass
class TokenEntry:
    id: int
    name: str
    category: str = "Unknown"


    # ===================================================================
#  MAIN WINDOW
    # ===================================================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        icon_path = resource_path("assets", "icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.setWindowTitle("NFS MW 2005 - Junkman Inventory (PC v1.3)")
        self.resize(1180, 720)

    #  state
        self.savefile: Optional[SaveFile] = None
        self.have_counts: Dict[int, int] = {}
        self.want_counts: Dict[int, int] = {}
        self.have_money = 0
        self.want_money: Optional[int] = None
        self.garage_slots: List[GarageSlot] = []
        self.have_slot_bounties: Dict[int, int] = {}
        self.want_slot_bounties: Optional[Dict[int, int]] = None
        self.garage_detection_error: Optional[str] = None
        self.show_all_garage_slots = False
        self.show_integrity_panel = False
        self.tokens: List[TokenEntry] = []
        self.safe_mode = True
        self.practical_cap10 = True
        self.preserve_unknown = True
        self.clear_unknown_next = False
        self.show_only_changed = False
        self._profile_refreshing = False
        self._garage_slot_columns = 0

        self.catalog_path = _ensure_user_catalog_path()
        self.load_catalog()
        self._build_ui()
        self.refresh_state()

    # ================================================================
    #  CATALOG
    # ================================================================

    def _normalize_catalog_defaults(self) -> bool:
        changed = False
        expected: Dict[int, tuple[str, str]] = {
            17: ("Out of Jail", "Police"),
            18: ("Money Marker", "Police"),
            19: ("PinkSlip Marker", "Police"),
            20: ("Impound Strike Slot Add", "Police"),
            21: ("Impound Release", "Police"),
            22: ("Unknown ID 22 (valid)", "Unknown"),
        }
        legacy_names: Dict[int, set[str]] = {
            18: {"Unknown ID 18", "Imp. Strike?"},
            19: {"Imp. Release?"},
            20: {"Imp. Strike"},
        }
        idx = {t.id: t for t in self.tokens}
        for tid, (name, category) in expected.items():
            tok = idx.get(tid)
            if tok is None:
                self.tokens.append(TokenEntry(id=tid, name=name, category=category))
                changed = True
                continue
            if tok.name in legacy_names.get(tid, set()):
                tok.name = name
                changed = True
            if tok.category == "Unknown" and category == "Police":
                tok.category = category
                changed = True
        if changed:
            self.tokens.sort(key=lambda t: t.id)
        return changed

    def load_catalog(self):
        def from_list(toks):
            return [
                TokenEntry(
                    id=int(t.get("id")),
                    name=t.get("name", f"Token #{t.get('id')}"),
                    category=t.get("category", "Unknown"),
                )
                for t in toks if "id" in t
            ]

        def from_dict(obj):
            out = []
            for k, v in obj.items():
                try:
                    tid = int(k)
                except Exception:
                    continue
                if not isinstance(v, dict):
                    v = {}
                out.append(TokenEntry(
                    id=tid,
                    name=v.get("name", f"Token #{tid}"),
                    category=v.get("category", "Unknown"),
                ))
            return out

        self.tokens = []
        if self.catalog_path.exists():
            try:
                raw = json.loads(self.catalog_path.read_text(encoding="utf-8"))
                if isinstance(raw, dict) and "tokens" in raw and isinstance(raw["tokens"], list):
                    self.tokens = from_list(raw["tokens"])
                elif isinstance(raw, dict):
                    self.tokens = from_dict(raw)
            except Exception:
                self.tokens = []

        if not self.tokens:
            defaults = [
                (1, "Brakes", "Performance"), (2, "Engine", "Performance"),
                (3, "NOS", "Performance"), (4, "Turbo", "Performance"),
                (5, "Suspension", "Performance"), (6, "Tires", "Performance"),
                (7, "Transmission", "Performance"), (8, "Body", "Visual"),
                (9, "Hood", "Visual"), (10, "Spoiler", "Visual"),
                (11, "Rims", "Visual"), (12, "Roof", "Visual"),
                (13, "Gauge", "Visual"), (14, "Vinyl", "Visual"),
                (15, "Decal", "Visual"), (16, "Paint", "Visual"),
                (17, "Out of Jail", "Police"), (18, "Money Marker", "Police"),
                (19, "PinkSlip Marker", "Police"), (20, "Impound Strike Slot Add", "Police"),
                (21, "Impound Release", "Police"), (22, "Unknown ID 22 (valid)", "Unknown"),
            ]
            self.tokens = [TokenEntry(id=i, name=n, category=c) for i, n, c in defaults]
            self.save_catalog()
        if self._normalize_catalog_defaults():
            self.save_catalog()

    def save_catalog(self):
        data = {"tokens": [{"id": t.id, "name": t.name, "category": t.category} for t in self.tokens]}
        self.catalog_path.parent.mkdir(parents=True, exist_ok=True)
        self.catalog_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def ensure_token_entry(self, tid: int):
        if any(t.id == tid for t in self.tokens):
            return
        self.tokens.append(TokenEntry(id=tid, name=f"Token #{tid}", category="Unknown"))
        self.tokens.sort(key=lambda t: t.id)

    # ================================================================
    #  BUILD UI
    # ================================================================

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        base = QVBoxLayout(root)
        base.setContentsMargins(12, 12, 12, 12)
        base.setSpacing(10)

        base.addLayout(self._build_header())

        body = QHBoxLayout()
        body.setSpacing(12)
        base.addLayout(body, 1)

        body.addLayout(self._build_nav(), 0)

        self.stack = QStackedWidget()
        body.addWidget(self.stack, 1)

        self.page_junk = self._build_junk_page()
        self.page_profile = self._build_profile_page()
        self.page_presets = self._build_presets_page()
        self.page_settings = self._build_settings_page()
        self.page_about = self._build_about_page()

        for p in [self.page_junk, self.page_profile, self.page_presets,
                   self.page_settings, self.page_about]:
            self.stack.addWidget(p)

        self._select_page("Junkman")
        base.addLayout(self._build_footer())

        # -- Keyboard shortcuts --
        QShortcut(QKeySequence("Ctrl+O"), self, activated=self.on_open)
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self.on_save)
        QShortcut(QKeySequence("Ctrl+Z"), self, activated=self.on_reset_want)

        # -- Drag & drop --
        self.setAcceptDrops(True)

    # -- Header ----------------------------------------------------------

    def _build_header(self):
        row = QHBoxLayout()
        row.setSpacing(8)
        self.btn_open = QPushButton("Open save")
        self.btn_save_header = QPushButton("Save + backup")
        self.btn_fix = QPushButton("Fix checksums")
        self.btn_open.clicked.connect(self.on_open)
        self.btn_save_header.clicked.connect(self.on_save)
        self.btn_fix.clicked.connect(self.on_fix_checksums)

        self.lbl_file = QLabel("File: (not opened)")
        self.lbl_file.setObjectName("filePath")
        self.lbl_file.setAlignment(Qt.AlignCenter)
        self.lbl_status = QLabel("Status: -")
        self.lbl_status.setObjectName("mutedLabel")
        self.lbl_unsaved = QLabel("")
        self.lbl_unsaved.setObjectName("unsavedLabel")

        for w in [self.btn_open, self.btn_save_header, self.btn_fix]:
            row.addWidget(w)
        row.addStretch(1)
        row.addWidget(self.lbl_file, 1)
        row.addWidget(self.lbl_unsaved)
        row.addWidget(self.lbl_status)
        return row

    @staticmethod
    def _tight_icon(path: Path, size: QSize) -> QIcon:
        """Load icon and trim transparent paddings so visual size is consistent."""
        pix = QPixmap(str(path))
        if pix.isNull():
            return QIcon(str(path))

        img = pix.toImage().convertToFormat(QImage.Format_RGBA8888)
        w, h = img.width(), img.height()
        min_x, min_y = w, h
        max_x, max_y = -1, -1
        for y in range(h):
            for x in range(w):
                alpha = (img.pixel(x, y) >> 24) & 0xFF
                if alpha:
                    if x < min_x:
                        min_x = x
                    if y < min_y:
                        min_y = y
                    if x > max_x:
                        max_x = x
                    if y > max_y:
                        max_y = y

        if max_x >= min_x and max_y >= min_y:
            pix = pix.copy(min_x, min_y, (max_x - min_x + 1), (max_y - min_y + 1))
        pix = pix.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        return QIcon(pix)

    @staticmethod
    def _brand_pixmap(size: int) -> QPixmap:
        png_path = resource_path("assets", "icon.png")
        pix = QPixmap(str(png_path))
        if pix.isNull():
            ico_path = resource_path("assets", "icon.ico")
            if ico_path.exists():
                pix = QIcon(str(ico_path)).pixmap(size, size)
        if pix.isNull():
            return QPixmap()
        return pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    # -- Navigation sidebar -----------------------------------------------

    def _build_nav(self):
        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignTop)
        self.nav_buttons: Dict[str, QPushButton] = {}
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        for name in ["Junkman", "Profile", "Presets", "Settings", "About"]:
            btn = QPushButton(name)
            btn.setObjectName("navButton")
            btn.setCheckable(True)
            btn.setMinimumHeight(48)
            btn.setMinimumWidth(130)

            # Load nav icon
            icon_p = nav_icon_path(name)
            if icon_p and icon_p.exists():
                btn.setIcon(self._tight_icon(icon_p, QSize(28, 28)))
                btn.setIconSize(QSize(28, 28))

            btn.clicked.connect(lambda _, n=name: self._select_page(n))
            self.nav_buttons[name] = btn
            self.nav_group.addButton(btn)
            layout.addWidget(btn)

        layout.addStretch(1)
        return layout

    # -- Footer ----------------------------------------------------------

    def _build_footer(self):
        row = QHBoxLayout()
        row.setSpacing(10)
        self.lbl_free = QLabel("Free slots: -/-")
        self.lbl_free.setObjectName("pillLabel")

        # Progress bar: unlocked tokens
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("tokenProgress")
        self.progress_bar.setRange(0, PERF_TOTAL)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(18)
        self.progress_bar.setFixedWidth(160)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("0/7 Performance")

        self.btn_reset_want = QPushButton("Reset Want=Have")
        self.btn_apply = QPushButton("Apply (memory)")
        self.btn_save_footer = QPushButton("Save + backup")
        self.btn_reset_want.clicked.connect(self.on_reset_want)
        self.btn_apply.clicked.connect(self.on_apply_changes)
        self.btn_save_footer.clicked.connect(self.on_save)
        row.addWidget(self.lbl_free)
        row.addWidget(self.progress_bar)
        row.addStretch(1)
        row.addWidget(self.btn_reset_want)
        row.addWidget(self.btn_apply)
        row.addWidget(self.btn_save_footer)
        return row

    # -- Page select -----------------------------------------------------

    def _select_page(self, name: str):
        for n, btn in self.nav_buttons.items():
            btn.setChecked(n == name)
        mapping = {
            "Junkman": self.page_junk,
            "Profile": self.page_profile,
            "Presets": self.page_presets,
            "Settings": self.page_settings,
            "About": self.page_about,
        }
        self.stack.setCurrentWidget(mapping[name])
        if name == "Junkman" and hasattr(self, "cards_container") and hasattr(self, "lbl_free"):
            self._sync_cards_per_row(force=True)
            self.refresh_cards()
        elif name == "Profile":
            self._maybe_reflow_garage_rows(force=True)

    # ================================================================
    #  JUNKMAN PAGE  (grid of TokenCards)
    # ================================================================

    def _build_junk_page(self):
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setSpacing(12)

    # -- left panel (filters, quick actions) ------------------------------
        left = QVBoxLayout()
        left.setSpacing(8)
        left.setAlignment(Qt.AlignTop)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search tokens...")
        self.search.textChanged.connect(self.refresh_cards)
        left.addWidget(self.search)

        self.chk_show_changed = QCheckBox("Show only changed")
        self.chk_show_changed.stateChanged.connect(self.on_toggle_show_changed)
        left.addWidget(self.chk_show_changed)

        # category filter
        cat_box = QVBoxLayout()
        cat_box.setSpacing(4)
        self.cat_buttons: Dict[str, QPushButton] = {}
        self.cat_group = QButtonGroup(self)
        self.cat_group.setExclusive(True)
        for cat in CAT_LIST:
            btn = QPushButton(cat)
            btn.setObjectName("catButton")
            btn.setCheckable(True)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setMinimumHeight(32)
            # Category icon
            c_icon = cat_icon_path(cat)
            if c_icon:
                btn.setIcon(self._tight_icon(c_icon, QSize(20, 20)))
                btn.setIconSize(QSize(20, 20))
            btn.clicked.connect(lambda _, c=cat: self._select_category(c))
            self.cat_buttons[cat] = btn
            self.cat_group.addButton(btn)
            cat_box.addWidget(btn)
        self.cat_buttons["All"].setChecked(True)
        left.addLayout(cat_box)

        # quick actions
        left.addWidget(self._section_label("Quick actions"))
        self.btn_q_perf = QPushButton("Unlock Performance (1-7)")
        self.btn_q_vis = QPushButton("Unlock Visual (8-16)")
        self.btn_q_all = QPushButton("Unlock All (1-22)")
        self.btn_q_clear = QPushButton("Clear All (Want->0)")
        self.btn_q_perf.clicked.connect(lambda: self._quick_set(range(1, 8), 1))
        self.btn_q_vis.clicked.connect(lambda: self._quick_set(range(8, 17), 1))
        self.btn_q_all.clicked.connect(lambda: self._quick_set(range(SAFE_TYPE_MIN, SAFE_TYPE_MAX + 1), 1))
        self.btn_q_clear.clicked.connect(self.on_clear_all_want)
        for b in [self.btn_q_perf, self.btn_q_vis, self.btn_q_all, self.btn_q_clear]:
            left.addWidget(b)
        left.addStretch(1)

        left_widget = QWidget()
        left_widget.setLayout(left)
        left_widget.setFixedWidth(220)
        layout.addWidget(left_widget, 0)

        # -- right panel: stacked widget (cards vs empty state) --
        self.right_stack = QStackedWidget()
        layout.addWidget(self.right_stack, 1)

        # Page 0: card grid inside scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setObjectName("cardScroll")

        self.cards_container = QWidget()
        self.cards_grid = QGridLayout(self.cards_container)
        self.cards_grid.setSpacing(12)
        self.cards_grid.setContentsMargins(8, 8, 8, 8)
        self.cards_grid.setAlignment(Qt.AlignTop)

        self._cards_per_row = DEFAULT_CARDS_PER_ROW
        self.cards_container.setFixedWidth(self._card_area_width(self._cards_per_row))
        self.cards_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        self.cards_host = QWidget()
        self.cards_host_layout = QVBoxLayout(self.cards_host)
        self.cards_host_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_host_layout.setSpacing(0)
        self.cards_host_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.cards_host_layout.addWidget(self.cards_container, 0, Qt.AlignTop | Qt.AlignHCenter)

        self.scroll.setWidget(self.cards_host)
        self.right_stack.addWidget(self.scroll)           # index 0

        # Page 1: empty state (no file loaded)
        empty_page = QWidget()
        empty_page.setObjectName("emptyOverlay")
        ov_layout = QVBoxLayout(empty_page)
        ov_layout.setAlignment(Qt.AlignCenter)
        ov_layout.setSpacing(16)

        ov_icon = QLabel()
        ov_icon.setAlignment(Qt.AlignCenter)
        pix = self._brand_pixmap(64)
        if not pix.isNull():
            ov_icon.setPixmap(pix)
        ov_layout.addWidget(ov_icon)

        ov_title = QLabel("No save file loaded")
        ov_title.setObjectName("emptyTitle")
        ov_title.setAlignment(Qt.AlignCenter)
        ov_layout.addWidget(ov_title)

        ov_hint = QLabel('Click  "Open save"  to get started')
        ov_hint.setObjectName("emptyHint")
        ov_hint.setAlignment(Qt.AlignCenter)
        ov_layout.addWidget(ov_hint)

        self.right_stack.addWidget(empty_page)            # index 1
        self.right_stack.setCurrentIndex(1)                # start with empty

        # section headers & empty label
        self.section_labels: Dict[str, QLabel] = {}
        self.empty_label = QLabel("No tokens match your filter.")
        self.empty_label.setObjectName("mutedLabel")

        return w

    # -- Other pages -----------------------------------------------------

    def _build_profile_page(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 6, 10, 8)
        layout.setSpacing(14)
        layout.addWidget(QLabel("Profile / Integrity"))

        self._profile_number_validator = QRegularExpressionValidator(QRegularExpression(r"[0-9, ]*"), self)

        top_row = QHBoxLayout()
        top_row.setSpacing(22)

        left_panel = QFrame()
        left_panel.setObjectName("profileSummaryPanel")
        left_panel.setFixedWidth(PROFILE_SIDEBAR_WIDTH)
        left_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(8, 6, 14, 10)
        left_layout.setSpacing(14)
        left_layout.setAlignment(Qt.AlignTop)

        left_layout.addWidget(self._section_label("Economy"))
        self.profile_hint = QLabel(
            "Money and garage slot bounty values are staged until you click Apply (memory). "
            "Total Bounty / Rating is computed from the detected garage block."
        )
        self.profile_hint.setObjectName("mutedLabel")
        self.profile_hint.setWordWrap(True)
        left_layout.addWidget(self.profile_hint)

        left_layout.addWidget(self._build_profile_edit_row("Money"))
        left_layout.addWidget(self._build_profile_display_row("Total Bounty / Rating", "total_bounty"))
        left_layout.addWidget(self._build_profile_display_row("Escaped Pursuits", "escaped"))
        left_layout.addWidget(self._build_profile_display_row("Busted Pursuits", "busted"))
        left_layout.addStretch(1)

        right_panel = QFrame()
        right_panel.setObjectName("profileGaragePanel")
        right_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 6, 12, 10)
        right_layout.setSpacing(12)
        right_layout.setAlignment(Qt.AlignTop)
        right_layout.addWidget(self._section_label("Garage Slot Bounty"))

        self.garage_rows = QWidget()
        self.garage_rows.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.garage_rows_layout = QGridLayout(self.garage_rows)
        self.garage_rows_layout.setContentsMargins(10, 10, 24, 12)
        self.garage_rows_layout.setHorizontalSpacing(22)
        self.garage_rows_layout.setVerticalSpacing(16)
        self.garage_rows_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.garage_rows_scroll = QScrollArea()
        self.garage_rows_scroll.setObjectName("garageRowsScroll")
        self.garage_rows_scroll.setWidgetResizable(True)
        self.garage_rows_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.garage_rows_scroll.setWidget(self.garage_rows)
        self.garage_rows_scroll.setMinimumHeight(260)
        right_layout.addWidget(self.garage_rows_scroll, 1)

        top_row.addWidget(left_panel, 0)
        top_row.addWidget(right_panel, 1)
        layout.addLayout(top_row, 1)

        self.integrity_section_label = self._section_label("Integrity")
        layout.addWidget(self.integrity_section_label)
        self.profile_info = QTextEdit()
        self.profile_info.setReadOnly(True)
        self.profile_info.setMinimumHeight(140)
        self.profile_info.setMaximumHeight(180)
        self.profile_info.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.profile_info)
        self.garage_slot_edits: Dict[int, QLineEdit] = {}
        self.garage_slot_current_labels: Dict[int, QLabel] = {}
        self._rebuild_garage_slot_rows()
        self._sync_integrity_visibility()
        return w

    def _build_presets_page(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(10)
        layout.addWidget(QLabel("Presets"))
        self.btn_load_preset = QPushButton("Load preset JSON")
        self.btn_save_preset = QPushButton("Save preset JSON")
        self.btn_export_have = QPushButton("Export Have as preset")
        self.btn_load_preset.clicked.connect(self.on_load_preset)
        self.btn_save_preset.clicked.connect(self.on_save_preset)
        self.btn_export_have.clicked.connect(self.on_export_have)
        layout.addWidget(self.btn_load_preset)
        layout.addWidget(self.btn_save_preset)
        layout.addWidget(self.btn_export_have)
        layout.addStretch(1)
        return w

    def _build_settings_page(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(10)
        layout.addWidget(QLabel("Settings"))

        self.chk_preserve_unknown = QCheckBox("Preserve Unknown (default ON)")
        self.chk_preserve_unknown.setChecked(True)
        self.chk_preserve_unknown.stateChanged.connect(self.on_preserve_toggle)

        self.chk_safe = QCheckBox("Safe max (<= 63)")
        self.chk_safe.setChecked(True)
        self.chk_safe.stateChanged.connect(self.on_range_toggle)
        self.chk_adv = QCheckBox("Advanced (<= 255)")
        self.chk_adv.setChecked(False)
        self.chk_adv.stateChanged.connect(self.on_range_toggle)

        self.chk_practical_cap10 = QCheckBox("Unlock limit (<= 63)")
        self.chk_practical_cap10.setChecked(False)
        self.chk_practical_cap10.stateChanged.connect(self.on_practical_cap_toggle)

        self.chk_show_all_garage_slots = QCheckBox("Show empty valid garage slots")
        self.chk_show_all_garage_slots.setChecked(False)
        self.chk_show_all_garage_slots.stateChanged.connect(self.on_toggle_show_all_garage_slots)

        self.chk_show_integrity = QCheckBox("Show Integrity panel on Profile")
        self.chk_show_integrity.setChecked(False)
        self.chk_show_integrity.stateChanged.connect(self.on_toggle_show_integrity)

        self.btn_clear_unknown = QPushButton("Clear Unknown (danger)")
        self.btn_clear_unknown.clicked.connect(self.on_clear_unknown_confirm)

        self.lbl_limits = QLabel("Limits: -")
        self.lbl_limits.setObjectName("mutedLabel")
        self.lbl_type_safety = QLabel(
            f"Safe Type_ID range: {SAFE_TYPE_MIN}-{SAFE_TYPE_MAX}. "
            "Using IDs outside this range may crash the game."
        )
        self.lbl_type_safety.setObjectName("mutedLabel")
        self.lbl_type_safety.setWordWrap(True)

        self.lbl_catalog_path = QLabel(f"Catalog: {self.catalog_path}")
        self.lbl_catalog_path.setObjectName("mutedLabel")
        self.lbl_catalog_path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.btn_open_catalog = QPushButton("Open folder")
        self.btn_open_catalog.clicked.connect(self.on_open_catalog_folder)
        catalog_row = QHBoxLayout()
        catalog_row.addWidget(self.lbl_catalog_path, 1)
        catalog_row.addWidget(self.btn_open_catalog)

        layout.addWidget(self.chk_preserve_unknown)
        layout.addWidget(self.chk_safe)
        layout.addWidget(self.chk_adv)
        layout.addWidget(self.chk_practical_cap10)
        layout.addWidget(self.chk_show_all_garage_slots)
        layout.addWidget(self.chk_show_integrity)
        layout.addWidget(self.btn_clear_unknown)
        layout.addWidget(self.lbl_limits)
        layout.addWidget(self.lbl_type_safety)
        layout.addLayout(catalog_row)
        layout.addStretch(1)
        return w

    def _build_about_page(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignTop)
        layout.setSpacing(16)
        layout.setContentsMargins(32, 32, 32, 32)

        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignCenter)
        pix = self._brand_pixmap(80)
        if not pix.isNull():
            logo_label.setPixmap(pix)
        layout.addWidget(logo_label)

        title = QLabel("NFS MW 2005 - Junkman Inventory Editor")
        title.setObjectName("aboutTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        ver = QLabel("v1.3  ·  PC")
        ver.setObjectName("mutedLabel")
        ver.setAlignment(Qt.AlignCenter)
        layout.addWidget(ver)

        author = QLabel("Created by sprintstate")
        author.setObjectName("mutedLabel")
        author.setAlignment(Qt.AlignCenter)
        layout.addWidget(author)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("separator")
        layout.addWidget(sep)

        desc = QLabel(
            "Slot array is auto-detected per save (stride 0x0C).\n"
            "Apply writes to memory; Save+backup writes to disk.\n\n"
            "Keyboard shortcuts:\n"
            "  Ctrl+O  Open save · Ctrl+S  Save+backup · Ctrl+Z  Reset Want\n\n"
            "Drag & drop .sav files directly onto the window."
        )
        desc.setObjectName("mutedLabel")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)

        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignCenter)
        btn_github = QPushButton("GitHub")
        btn_github.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://github.com/sprintstate/nfs-mw-save-editor"))
        )
        btn_row.addWidget(btn_github)
        layout.addLayout(btn_row)

        layout.addStretch(1)
        return w

    # -- UI helpers ------------------------------------------------------

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("sectionLabel")
        return lbl

    @staticmethod
    def _format_u32(value: int) -> str:
        return str(int(value))

    @staticmethod
    def _clear_layout(layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                MainWindow._clear_layout(child_layout)

    def _parse_u32_text(self, raw: str) -> int:
        text = raw.replace(",", "").replace(" ", "").strip()
        if not text:
            raise ValueError("Value cannot be empty.")
        if not text.isdigit():
            raise ValueError("Only decimal digits are allowed.")
        value = int(text)
        if value > U32_MAX:
            raise ValueError(f"Value must be between 0 and {U32_MAX}.")
        return value

    @staticmethod
    def _format_current_value(value: int) -> str:
        return f"Current: {value}"

    def _build_profile_edit_row(self, label_text: str) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        label = QLabel(label_text)
        label.setMinimumWidth(140)

        edit = QLineEdit()
        edit.setPlaceholderText("0")
        edit.setMaximumWidth(220)
        edit.setValidator(self._profile_number_validator)

        current = QLabel("Current: -")
        current.setObjectName("mutedLabel")

        edit.editingFinished.connect(self.on_money_edit_finished)
        self.money_edit = edit
        self.money_current_label = current

        layout.addWidget(label)
        layout.addWidget(edit)
        layout.addWidget(current)
        layout.addStretch(1)
        return row

    def _build_profile_display_row(self, label_text: str, field_key: str) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        label = QLabel(label_text)
        label.setMinimumWidth(140)

        value = QLabel("-")
        value.setObjectName("pillLabel")
        current = QLabel("Current: -")
        current.setObjectName("mutedLabel")

        if field_key == "total_bounty":
            self.total_bounty_label = value
            self.total_bounty_current_label = current
        elif field_key == "escaped":
            self.escaped_total_label = value
            self.escaped_total_current_label = current
        else:
            self.busted_total_label = value
            self.busted_total_current_label = current

        layout.addWidget(label)
        layout.addWidget(value)
        layout.addWidget(current)
        layout.addStretch(1)
        return row

    def _visible_garage_slots(self) -> List[GarageSlot]:
        if self.show_all_garage_slots:
            return list(self.garage_slots)
        return [slot for slot in self.garage_slots if slot.occupied]

    def _detect_garage_slot_columns(self) -> int:
        if not hasattr(self, "garage_rows_scroll"):
            return 1
        viewport = self.garage_rows_scroll.viewport()
        if viewport is None:
            return 1
        available = max(240, viewport.width() - 44)
        if available >= 1280:
            return 3
        if available >= 760:
            return 2
        return 1

    def _maybe_reflow_garage_rows(self, force: bool = False) -> None:
        if not hasattr(self, "garage_rows_scroll"):
            return
        cols = self._detect_garage_slot_columns()
        if force or cols != self._garage_slot_columns:
            self._garage_slot_columns = cols
            self._rebuild_garage_slot_rows()
            if self.savefile is not None:
                self._refresh_profile_inputs()

    def _sync_integrity_visibility(self) -> None:
        visible = bool(self.show_integrity_panel)
        if hasattr(self, "integrity_section_label"):
            self.integrity_section_label.setVisible(visible)
        if hasattr(self, "profile_info"):
            self.profile_info.setVisible(visible)

    def _rebuild_garage_slot_rows(self) -> None:
        self._clear_layout(self.garage_rows_layout)
        self.garage_slot_edits = {}
        self.garage_slot_current_labels = {}
        columns = max(1, self._detect_garage_slot_columns())
        self._garage_slot_columns = columns

        if not self.savefile:
            label = QLabel("Open a save to inspect car bounty data.")
            label.setObjectName("mutedLabel")
            self.garage_rows_layout.addWidget(label, 0, 0, 1, columns)
            return

        if self.garage_detection_error:
            label = QLabel(f"Garage bounty editor disabled: {self.garage_detection_error}")
            label.setObjectName("mutedLabel")
            label.setWordWrap(True)
            self.garage_rows_layout.addWidget(label, 0, 0, 1, columns)
            return

        visible_slots = self._visible_garage_slots()
        if not visible_slots:
            if self.garage_slots:
                msg = "No occupied garage slots. Enable 'Show empty valid garage slots' in Settings."
            else:
                msg = "No valid garage slots detected."
            label = QLabel(msg)
            label.setObjectName("mutedLabel")
            label.setWordWrap(True)
            self.garage_rows_layout.addWidget(label, 0, 0, 1, columns)
            return

        for idx, slot in enumerate(visible_slots):
            card = QFrame()
            card.setObjectName("garageSlotCard")
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(6, 4, 8, 6)
            card_layout.setSpacing(8)

            label = QLabel(f"Car Slot {slot.slot_index + 1}")
            label.setObjectName("garageSlotTitle")

            edit = QLineEdit()
            edit.setPlaceholderText("0")
            edit.setMinimumWidth(120)
            edit.setMaximumWidth(160)
            edit.setValidator(self._profile_number_validator)
            edit.editingFinished.connect(lambda idx=slot.slot_index: self.on_garage_slot_edit_finished(idx))

            current = QLabel("Current: -")
            current.setObjectName("mutedLabel")
            current.setWordWrap(True)
            current.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            self.garage_slot_edits[slot.slot_index] = edit
            self.garage_slot_current_labels[slot.slot_index] = current

            edit_row = QHBoxLayout()
            edit_row.setContentsMargins(0, 0, 0, 0)
            edit_row.setSpacing(10)
            edit_row.addWidget(edit, 0)
            edit_row.addWidget(current, 1)

            card_layout.addWidget(label)
            card_layout.addLayout(edit_row)

            rows_per_col = (len(visible_slots) + columns - 1) // columns
            col = idx // rows_per_col
            row = idx % rows_per_col
            self.garage_rows_layout.addWidget(card, row, col)

        for col in range(columns):
            self.garage_rows_layout.setColumnStretch(col, 1)

    def _current_slot_bounties(self) -> Dict[int, int]:
        want_map = self.want_slot_bounties or {}
        return {
            slot.slot_index: want_map.get(slot.slot_index, self.have_slot_bounties.get(slot.slot_index, 0))
            for slot in self.garage_slots
        }

    def _set_profile_line_edit(self, edit: QLineEdit, value: int, enabled: bool) -> None:
        edit.blockSignals(True)
        edit.setText(self._format_u32(value) if enabled else "")
        edit.setEnabled(enabled)
        edit.blockSignals(False)

    def _refresh_garage_totals(self, loaded: bool) -> None:
        if not loaded:
            self.total_bounty_label.setText("-")
            self.total_bounty_current_label.setText("Current: -")
            self.escaped_total_label.setText("-")
            self.escaped_total_current_label.setText("Current: -")
            self.busted_total_label.setText("-")
            self.busted_total_current_label.setText("Current: -")
            return

        if self.garage_detection_error:
            self.total_bounty_label.setText("Unavailable")
            self.total_bounty_current_label.setText(self.garage_detection_error)
            self.escaped_total_label.setText("Unavailable")
            self.escaped_total_current_label.setText("Current: -")
            self.busted_total_label.setText("Unavailable")
            self.busted_total_current_label.setText("Current: -")
            return

        have_total = sum(self.have_slot_bounties.values())
        current_total = sum(self._current_slot_bounties().values())
        escaped_total = sum(slot.escaped for slot in self.garage_slots)
        busted_total = sum(slot.busted for slot in self.garage_slots)

        self.total_bounty_label.setText(self._format_u32(current_total))
        self.total_bounty_current_label.setText(self._format_current_value(have_total))
        self.escaped_total_label.setText(self._format_u32(escaped_total))
        self.escaped_total_current_label.setText(self._format_current_value(escaped_total))
        self.busted_total_label.setText(self._format_u32(busted_total))
        self.busted_total_current_label.setText(self._format_current_value(busted_total))

    def _refresh_profile_inputs(self) -> None:
        loaded = self.savefile is not None
        self.chk_show_all_garage_slots.blockSignals(True)
        self.chk_show_all_garage_slots.setChecked(self.show_all_garage_slots)
        self.chk_show_all_garage_slots.setEnabled(loaded and not self.garage_detection_error and bool(self.garage_slots))
        self.chk_show_all_garage_slots.blockSignals(False)
        self.chk_show_integrity.blockSignals(True)
        self.chk_show_integrity.setChecked(self.show_integrity_panel)
        self.chk_show_integrity.blockSignals(False)
        self._sync_integrity_visibility()
        self._rebuild_garage_slot_rows()

        self._profile_refreshing = True
        try:
            money_value = self.want_money if self.want_money is not None else self.have_money
            self._set_profile_line_edit(self.money_edit, money_value, loaded)
            self.money_current_label.setText(
                self._format_current_value(self.have_money) if loaded else "Current: -"
            )
            self._refresh_garage_totals(loaded)

            want_slot_bounties = self._current_slot_bounties() if loaded else {}
            for slot in self._visible_garage_slots():
                edit = self.garage_slot_edits.get(slot.slot_index)
                current = self.garage_slot_current_labels.get(slot.slot_index)
                if edit is None or current is None:
                    continue
                current_value = self.have_slot_bounties.get(slot.slot_index, 0)
                self._set_profile_line_edit(edit, want_slot_bounties.get(slot.slot_index, current_value), loaded)
                suffix = "" if slot.occupied else " [empty slot]"
                current.setText(self._format_current_value(current_value) + suffix)
        finally:
            self._profile_refreshing = False

    def _commit_profile_edit(self, edit: QLineEdit, fallback: int) -> Optional[int]:
        try:
            value = self._parse_u32_text(edit.text())
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid value", str(exc))
            self._set_profile_line_edit(edit, fallback, True)
            edit.setFocus()
            edit.selectAll()
            return None

        self._set_profile_line_edit(edit, value, True)
        return value

    def _has_profile_pending_changes(self) -> bool:
        if self.savefile is None:
            return False
        if (self.want_money if self.want_money is not None else self.have_money) != self.have_money:
            return True
        if self.garage_detection_error:
            return False
        for slot in self.garage_slots:
            have = self.have_slot_bounties.get(slot.slot_index, 0)
            want = self._current_slot_bounties().get(slot.slot_index, have)
            if want != have:
                return True
        return False

    def on_money_edit_finished(self) -> None:
        if self._profile_refreshing or not self.savefile:
            return
        fallback = self.want_money if self.want_money is not None else self.have_money
        value = self._commit_profile_edit(self.money_edit, fallback)
        if value is None:
            return
        self.want_money = value
        self._update_action_states()

    def on_toggle_show_all_garage_slots(self) -> None:
        self.show_all_garage_slots = self.chk_show_all_garage_slots.isChecked()
        self._refresh_profile_inputs()

    def on_toggle_show_integrity(self) -> None:
        self.show_integrity_panel = self.chk_show_integrity.isChecked()
        self._sync_integrity_visibility()

    def on_garage_slot_edit_finished(self, slot_index: int) -> None:
        if self._profile_refreshing or not self.savefile:
            return
        if self.garage_detection_error:
            return
        edit = self.garage_slot_edits.get(slot_index)
        if edit is None:
            return
        current_want = self._current_slot_bounties()
        fallback = current_want.get(slot_index, self.have_slot_bounties.get(slot_index, 0))
        value = self._commit_profile_edit(edit, fallback)
        if value is None:
            return
        if self.want_slot_bounties is None:
            self.want_slot_bounties = dict(self.have_slot_bounties)
        self.want_slot_bounties[slot_index] = value
        self._refresh_garage_totals(True)
        self._update_action_states()

    def _select_category(self, cat: str):
        for c, b in self.cat_buttons.items():
            b.setChecked(c == cat)
        self.refresh_cards()

    def _quick_set(self, ids, val: int):
        max_val = self._current_max()
        for tid in ids:
            self.want_counts[tid] = max(0, min(val, max_val))
            self.ensure_token_entry(tid)
        self.refresh_cards()

    # ================================================================
    #  STATE & RENDERING
    # ================================================================

    def _slot_capacity(self) -> int:
        if self.savefile and self.savefile.junkman:
            return self.savefile.junkman.slot_count
        return 59

    def _current_max(self) -> int:
        cap = self._slot_capacity()
        if self.practical_cap10:
            return min(10, cap)
        return min(63, cap)

    def _unknown_ids(self) -> List[int]:
        return [t.id for t in self.tokens if t.category == "Unknown"]

    def _card_area_width(self, cols: int) -> int:
        margins = self.cards_grid.contentsMargins()
        return (
            margins.left()
            + margins.right()
            + cols * TokenCard.CARD_WIDTH
            + (cols - 1) * self.cards_grid.spacing()
        )

    def _detect_cards_per_row(self) -> int:
        if not hasattr(self, "scroll"):
            return DEFAULT_CARDS_PER_ROW
        viewport = self.scroll.viewport()
        if viewport is None:
            return getattr(self, "_cards_per_row", DEFAULT_CARDS_PER_ROW)
        available = max(320, viewport.width() - 8)
        for cols in range(MAX_CARDS_PER_ROW, 0, -1):
            if self._card_area_width(cols) <= available:
                return cols
        return 1

    def _sync_cards_per_row(self, force: bool = False) -> int:
        cols = self._detect_cards_per_row()
        current = getattr(self, "_cards_per_row", DEFAULT_CARDS_PER_ROW)
        if force or cols != current:
            self._cards_per_row = cols
            self.cards_container.setFixedWidth(self._card_area_width(cols))
        return getattr(self, "_cards_per_row", DEFAULT_CARDS_PER_ROW)

    def refresh_state(self):
        loaded = self.savefile is not None

        # Toggle empty state vs cards
        self.right_stack.setCurrentIndex(0 if loaded else 1)

        for btn in [
            self.btn_save_header, self.btn_save_footer, self.btn_fix,
            self.btn_apply, self.btn_reset_want,
            self.btn_q_perf, self.btn_q_vis, self.btn_q_all, self.btn_q_clear,
            self.btn_load_preset, self.btn_save_preset, self.btn_export_have,
            self.btn_clear_unknown,
        ]:
            btn.setEnabled(loaded)

        if loaded:
            self.lbl_file.setText(f"File: {self.savefile.path}")
            integrity = self.savefile.validate_integrity()
            parts = []
            if integrity.md5_ok is True:
                parts.append("MD5 OK")
            elif integrity.md5_ok is False:
                parts.append("MD5 BAD")
            for name, ok in [("CRC1", integrity.crc_block1_ok),
                             ("CRCdata", integrity.crc_data_ok),
                             ("CRC2", integrity.crc_block2_ok)]:
                if ok:
                    parts.append(f"{name} OK")
            self.lbl_status.setText("Status: " + ", ".join(parts) if parts else "Status: -")
            self.profile_info.setText(
                f"Hash scheme: {integrity.hash_scheme}\n"
                f"File size ok: {integrity.file_size_ok} ({integrity.actual_size})\n"
                f"MD5 stored: {integrity.stored_md5.hex()}\n"
                f"MD5 computed: {(integrity.computed_md5.hex() if integrity.computed_md5 else '-')}\n"
            )
            self.have_counts = self.savefile.get_junkman_counts()
            self.have_money = self.savefile.get_money()
            self.garage_detection_error = None
            try:
                self.garage_slots = self.savefile.get_garage_slots()
                self.have_slot_bounties = {
                    slot.slot_index: slot.bounty for slot in self.garage_slots
                }
            except Exception as exc:
                self.garage_detection_error = str(exc)
                self.garage_slots = []
                self.have_slot_bounties = {}
            for tid in self.have_counts:
                self.ensure_token_entry(tid)
            if not self.want_counts:
                self.want_counts = dict(self.have_counts)
            if self.want_money is None:
                self.want_money = self.have_money
            if self.garage_detection_error:
                self.want_slot_bounties = None
            elif self.want_slot_bounties is None:
                self.want_slot_bounties = dict(self.have_slot_bounties)
            else:
                self.want_slot_bounties = {
                    slot.slot_index: self.want_slot_bounties.get(slot.slot_index, slot.bounty)
                    for slot in self.garage_slots
                }
        else:
            self.lbl_file.setText("File: (not opened)")
            self.lbl_status.setText("Status: -")
            self.profile_info.setText("")
            self.have_counts = {}
            self.want_counts = {}
            self.have_money = 0
            self.want_money = None
            self.garage_slots = []
            self.have_slot_bounties = {}
            self.want_slot_bounties = None
            self.garage_detection_error = None
            self.show_all_garage_slots = False

        self.lbl_limits.setText(
            f"Limits: Safe {min(63, self._slot_capacity())}, Advanced {min(255, self._slot_capacity())}"
        )
        self._refresh_profile_inputs()
        self.refresh_cards()

    # -- Card grid rendering ---------------------------------------------

    def refresh_cards(self):
        """Rebuild the entire card grid."""
        # Clear everything from the grid
        while self.cards_grid.count():
            item = self.cards_grid.takeAt(0)
            w = item.widget()
            if w and w is not self.empty_label:
                w.deleteLater()

        term = self.search.text().lower() if self.search else ""
        active_cat = next((c for c, b in self.cat_buttons.items() if b.isChecked()), "All")
        max_val = self._current_max()
        cards_per_row = self._sync_cards_per_row(force=True)

        def matches(tok: TokenEntry) -> bool:
            if active_cat != "All" and tok.category != active_cat:
                return False
            if term and term not in tok.name.lower() and term not in str(tok.id):
                return False
            if self.show_only_changed:
                have = self.have_counts.get(tok.id, 0)
                want = self.want_counts.get(tok.id, have)
                if want == have:
                    return False
            return True

        grid_row = 0
        grid_col = 0
        any_added = False

        for cat in ["Performance", "Visual", "Police", "Unknown"]:
            toks = [t for t in self.tokens if t.category == cat and matches(t)]
            if not toks:
                continue

            # Section header (spans full row)
            if grid_col != 0:
                grid_row += 1
                grid_col = 0

            header = self._section_label(cat)
            header.setObjectName("gridSectionLabel")
            self.cards_grid.addWidget(header, grid_row, 0, 1, cards_per_row)
            grid_row += 1
            grid_col = 0
            any_added = True

            for t in toks:
                have = self.have_counts.get(t.id, 0)
                want = self.want_counts.get(t.id, have)
                card = TokenCard(
                    token_id=t.id,
                    name=t.name,
                    have=have,
                    want=want,
                    max_val=max_val,
                    on_change=self.on_want_changed,
                    on_rename=self.on_token_renamed,
                )
                self.cards_grid.addWidget(card, grid_row, grid_col)
                self._fade_in_card(card, delay_ms=grid_col * 30)
                grid_col += 1
                if grid_col >= cards_per_row:
                    grid_col = 0
                    grid_row += 1

            # Move to next row after category
            if grid_col != 0:
                grid_row += 1
                grid_col = 0

        if not any_added:
            self.empty_label.setParent(None)
            self.cards_grid.addWidget(self.empty_label, 0, 0, 1, cards_per_row)
            self.empty_label.setVisible(True)
        else:
            self.empty_label.setVisible(False)

        self._update_free_label()
        self._update_action_states()

    # -- Status helpers --------------------------------------------------

    def _projected_slot_usage(self) -> tuple[int, int, int]:
        """Return (used, free, cap) for current preview state (Want)."""
        cap = self._slot_capacity()
        want_full = self._build_want_full() if self.savefile else {}
        used = sum(want_full.values()) if self.savefile else sum(self.have_counts.values())
        free = cap - used
        return used, free, cap

    def _projected_perf_unlocked_count(self) -> int:
        """Return realtime unlocked coverage for performance IDs (1..7)."""
        mapping = self._build_want_full() if self.savefile else self.have_counts
        return sum(1 for tid in PERF_IDS if mapping.get(tid, 0) > 0)

    def _update_free_label(self):
        _used, free, cap = self._projected_slot_usage()
        if free < 0:
            self.lbl_free.setText(f"Free slots: 0/{cap} (over by {abs(free)})")
        else:
            self.lbl_free.setText(f"Free slots: {free}/{cap}")

        # Update progress bar — realtime performance coverage (IDs 1..7)
        perf_unlocked = self._projected_perf_unlocked_count()
        self.progress_bar.setRange(0, PERF_TOTAL)
        self.progress_bar.setValue(perf_unlocked)
        self.progress_bar.setFormat(f"{perf_unlocked}/{PERF_TOTAL} Performance")

        self._update_header_path()

    def _has_pending_changes(self) -> bool:
        for tid in set(self.want_counts.keys()) | set(self.have_counts.keys()):
            have = self.have_counts.get(tid, 0)
            want = self.want_counts.get(tid, have)
            if want != have:
                return True
        return self.clear_unknown_next or self._has_profile_pending_changes()

    def _update_action_states(self):
        pending = self._has_pending_changes()
        enabled = self.savefile is not None
        self.btn_apply.setEnabled(enabled and pending)
        self.btn_reset_want.setEnabled(enabled)
        self.lbl_unsaved.setText("\u25cf Unsaved changes" if pending else "")

    def _update_header_path(self):
        text = "File: (not opened)" if not self.savefile else f"{self.savefile.path}"
        fm = self.lbl_file.fontMetrics()
        available = max(120, self.lbl_file.width())
        self.lbl_file.setText(fm.elidedText(text, Qt.ElideMiddle, available))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_header_path()
        if hasattr(self, "scroll") and hasattr(self, "cards_container"):
            prev = getattr(self, "_cards_per_row", DEFAULT_CARDS_PER_ROW)
            now = self._detect_cards_per_row()
            if now != prev:
                self._cards_per_row = now
                self.cards_container.setFixedWidth(self._card_area_width(now))
                self.refresh_cards()
            else:
                self.cards_container.setFixedWidth(self._card_area_width(prev))
        self._maybe_reflow_garage_rows()

    # -- Drag & drop ------------------------------------------------

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path:
                self.on_open(filepath=path)
        event.acceptProposedAction()

    # -- Card fade-in animation -------------------------------------

    @staticmethod
    def _fade_in_card(card: TokenCard, delay_ms: int = 0):
        """Animate a card appearing with a quick opacity fade."""
        eff = QGraphicsOpacityEffect(card)
        eff.setOpacity(0.0)
        card.setGraphicsEffect(eff)
        anim = QPropertyAnimation(eff, b"opacity", card)
        anim.setDuration(250)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        # Remove the effect after animation so scrolling doesn't glitch
        anim.finished.connect(lambda: card.setGraphicsEffect(None))
        from PySide6.QtCore import QTimer
        QTimer.singleShot(delay_ms, anim.start)

    # ================================================================
    #  EVENTS
    # ================================================================

    def on_token_renamed(self, tid: int, new_name: str):
        for t in self.tokens:
            if t.id == tid:
                t.name = new_name
                break
        self.save_catalog()
        self.refresh_cards()

    def on_want_changed(self, tid: int, val: int):
        have = self.have_counts.get(tid, 0)
        prev = self.want_counts.get(tid, have)
        self.want_counts[tid] = val
        if self.show_only_changed:
            # Rebuild only when the row should appear/disappear.
            if (prev == have) != (val == have):
                self.refresh_cards()
            else:
                self._update_free_label()
                self._update_action_states()
            return
        self._update_free_label()
        self._update_action_states()

    def on_range_toggle(self):
        if self.sender() == self.chk_safe and self.chk_safe.isChecked():
            self.chk_adv.setChecked(False)
            self.safe_mode = True
        elif self.sender() == self.chk_adv and self.chk_adv.isChecked():
            self.chk_safe.setChecked(False)
            self.safe_mode = False
        if not self.chk_safe.isChecked() and not self.chk_adv.isChecked():
            self.chk_safe.setChecked(True)
            self.safe_mode = True
        self.refresh_cards()

    def on_practical_cap_toggle(self):
        # Default mode is practical cap <=10. Checked means unlock up to <=63.
        self.practical_cap10 = not self.chk_practical_cap10.isChecked()
        self.refresh_cards()

    def on_preserve_toggle(self):
        self.preserve_unknown = self.chk_preserve_unknown.isChecked()

    def on_toggle_show_changed(self):
        self.show_only_changed = self.chk_show_changed.isChecked()
        self.refresh_cards()

    def on_clear_unknown_confirm(self):
        if not self.savefile:
            return
        res = QMessageBox.warning(
            self, "Clear Unknown",
            "This will clear all Unknown-category tokens on next Apply.\nContinue?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if res == QMessageBox.Yes:
            self.clear_unknown_next = True
            for tid in self._unknown_ids():
                self.want_counts[tid] = 0
            self.refresh_cards()

    def on_reset_want(self):
        self.want_counts = dict(self.have_counts)
        self.want_money = self.have_money
        self.want_slot_bounties = None if self.garage_detection_error else dict(self.have_slot_bounties)
        self._refresh_profile_inputs()
        self.refresh_cards()

    def on_clear_all_want(self):
        self.want_counts = {t.id: 0 for t in self.tokens}
        self.refresh_cards()

    # -- Apply -----------------------------------------------------------

    def _build_want_full(self) -> Dict[int, int]:
        mapping: Dict[int, int] = {}
        max_val = self._current_max()
        for t in self.tokens:
            want = self.want_counts.get(t.id, self.have_counts.get(t.id, 0))
            mapping[t.id] = max(0, min(want, max_val))
        if not self.preserve_unknown or self.clear_unknown_next:
            for tid in self._unknown_ids():
                mapping[tid] = 0
        return mapping

    def _summary_text(self, want_full: Dict[int, int]) -> str:
        total = self._slot_capacity()
        used = sum(self.have_counts.values())
        needed = sum(want_full.values())
        free = max(0, total - used)
        add = max(0, needed - used)
        remove = max(0, used - needed)
        unknown_preserved = 0
        if self.preserve_unknown and not self.clear_unknown_next:
            unknown_preserved = sum(want_full.get(tid, 0) for tid in self._unknown_ids())
        slot_changes = []
        if not self.garage_detection_error:
            want_slot_bounties = self._current_slot_bounties()
            for slot in self.garage_slots:
                have = self.have_slot_bounties.get(slot.slot_index, 0)
                want = want_slot_bounties.get(slot.slot_index, have)
                if want != have:
                    slot_changes.append(f"Car Slot {slot.slot_index + 1}: {have} -> {want}")
        have_total_bounty = sum(self.have_slot_bounties.values())
        want_total_bounty = sum(self._current_slot_bounties().values()) if not self.garage_detection_error else None
        summary = (
            f"Total slots: {total}\n"
            f"Used (have): {used}\n"
            f"Free: {free}\n"
            f"Need (want): {needed}\n"
            f"Delta: +{add} / -{remove}\n"
            f"Unknown preserved: {unknown_preserved}"
        )
        summary += f"\n\nProfile changes:\nMoney: {self.have_money} -> {self.want_money if self.want_money is not None else self.have_money}"
        if self.garage_detection_error:
            summary += f"\nGarage Bounty: unavailable ({self.garage_detection_error})"
        else:
            summary += f"\nTotal Bounty / Rating: {have_total_bounty} -> {want_total_bounty}"
            if slot_changes:
                summary += "\n" + "\n".join(slot_changes)
        return summary

    def on_apply_changes(self):
        if not self.savefile:
            QMessageBox.warning(self, "No save", "Open a save first.")
            return
        want_full = self._build_want_full()
        unsafe_added = sorted(
            tid for tid, qty in want_full.items()
            if qty > self.have_counts.get(tid, 0) and not (SAFE_TYPE_MIN <= tid <= SAFE_TYPE_MAX)
        )
        if unsafe_added:
            ids = ", ".join(str(t) for t in unsafe_added)
            res = QMessageBox.warning(
                self, "Unsafe Type_ID",
                f"Type_ID(s) outside safe range {SAFE_TYPE_MIN}-{SAFE_TYPE_MAX}: {ids}\n"
                "These values may crash the game. Continue anyway?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if res != QMessageBox.Yes:
                return
        needed = sum(want_full.values())
        cap = self._slot_capacity()
        if needed > cap:
            QMessageBox.warning(
                self, "Not enough slots",
                f"Need {needed} slots, have {cap}.\nReduce Want values or clear a category.",
            )
            return
        summary = self._summary_text(want_full)
        res = QMessageBox.question(
            self, "Apply changes?",
            summary + "\n\nApply changes to loaded save (memory only)?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if res != QMessageBox.Yes:
            return
        try:
            self.savefile.set_junkman_counts(want_full, clamp_max=self._current_max())
            self.savefile.set_money(self.want_money if self.want_money is not None else self.have_money)
            if not self.garage_detection_error:
                for slot_index, value in self._current_slot_bounties().items():
                    self.savefile.set_slot_bounty(slot_index, value)
            self.want_counts = {}
            self.want_money = None
            self.want_slot_bounties = None
            self.clear_unknown_next = False
            self.refresh_state()
            ToastNotification.show_toast(self, "Changes applied in memory")
        except Exception as e:
            QMessageBox.critical(self, "Apply failed", str(e))

    # -- Presets ---------------------------------------------------------

    def on_load_preset(self):
        if not self.savefile:
            QMessageBox.warning(self, "No save", "Open a save first.")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Load preset", str(Path.home()), "JSON (*.json)")
        if not path:
            return
        try:
            obj = json.loads(Path(path).read_text(encoding="utf-8"))
            counts_obj = obj.get("counts", obj)
            counts: Dict[int, int] = {}
            rejected: List[int] = []
            for k, v in counts_obj.items():
                tid = int(k)
                qty = int(v)
                if qty < 0:
                    continue
                if tid < SAFE_TYPE_MIN or tid > SAFE_TYPE_MAX:
                    rejected.append(tid)
                    continue
                counts[tid] = qty
            for tid in counts:
                self.ensure_token_entry(tid)
            self.want_counts.update(counts)
            self.refresh_cards()
            if rejected:
                uniq = ", ".join(str(t) for t in sorted(set(rejected)))
                QMessageBox.warning(
                    self, "Preset IDs skipped",
                    f"Skipped unsafe Type_ID(s): {uniq}\nAllowed range: {SAFE_TYPE_MIN}-{SAFE_TYPE_MAX}.",
                )
        except Exception as e:
            QMessageBox.critical(self, "Load failed", str(e))

    def on_save_preset(self):
        if not self.savefile:
            QMessageBox.warning(self, "No save", "Open a save first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save preset", str(Path.home() / "junkman_preset.json"), "JSON (*.json)"
        )
        if not path:
            return
        payload = {"counts": self.want_counts}
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        ToastNotification.show_toast(self, "Preset saved")

    def on_export_have(self):
        if not self.savefile:
            QMessageBox.warning(self, "No save", "Open a save first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Have", str(Path.home() / "junkman_have.json"), "JSON (*.json)"
        )
        if not path:
            return
        payload = {"counts": self.have_counts}
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        ToastNotification.show_toast(self, "Have exported")

    # -- File operations --------------------------------------------------

    def on_open_catalog_folder(self):
        folder = self.catalog_path.parent
        opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
        if not opened and hasattr(os, "startfile"):
            try:
                os.startfile(folder)
            except Exception:
                pass

    def on_open(self, filepath: str | None = None):
        path = filepath
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "Open save", str(Path.home()), "All files (*.*)")
        if not path:
            return
        try:
            self.savefile = SaveFile.load(path)
            self.want_counts = {}
            self.want_money = None
            self.want_slot_bounties = None
            self.garage_detection_error = None
            self.refresh_state()
            ToastNotification.show_toast(self, "Save loaded")
        except Exception as e:
            QMessageBox.critical(self, "Open failed", str(e))

    def on_save(self):
        if not self.savefile:
            QMessageBox.warning(self, "No file", "Open a save first.")
            return
        try:
            self.savefile.save(make_backup=True)
            ToastNotification.show_toast(self, "Saved with backup")
        except Exception as e:
            QMessageBox.critical(self, "Save failed", str(e))

    def on_fix_checksums(self):
        if not self.savefile:
            QMessageBox.warning(self, "No file", "Open a save first.")
            return
        status = self.savefile.fix_integrity()
        ToastNotification.show_toast(self, f"Checksums fixed ({status.hash_scheme})")
        self.refresh_state()


    # ===================================================================

def build_window() -> MainWindow:
    return MainWindow()

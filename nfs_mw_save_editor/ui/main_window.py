from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)

from core.junkman import JunkmanInventory
from core.savefile import SaveFile
from resources import resource_path


CAT_LIST = ["All", "Performance", "Visual", "Police", "Unknown"]
APP_NAME = "NFS_MW_Junkman_Editor"
CATALOG_FILENAME = "token_catalog.json"


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


class WantSpinBox(QSpinBox):
    def wheelEvent(self, event):
        # Prevent accidental edits while scrolling
        event.ignore()


class TokenRow(QWidget):
    def __init__(self, token: TokenEntry, have: int, want: int, max_val: int, on_change, on_rename):
        super().__init__()
        self.setObjectName("tokenRow")
        self.token = token
        self.on_change = on_change
        self.on_rename = on_rename

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(36)

        self.name_edit = QLineEdit(token.name)
        self.name_edit.setMinimumHeight(28)
        self.name_edit.setMaximumWidth(440)
        self.name_edit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.name_edit.editingFinished.connect(self._handle_rename)
        layout.addWidget(self.name_edit)

        have_lbl = QLabel(f"Have: {have}")
        have_lbl.setObjectName("haveLabel")
        layout.addWidget(have_lbl)

        self.btn_minus = QPushButton("-")
        self.btn_minus.setObjectName("iconBtn")
        self.btn_minus.setFixedSize(24, 24)
        self.btn_minus.clicked.connect(lambda: self._bump(-1))

        self.want_spin = WantSpinBox()
        self.want_spin.setRange(0, max_val)
        self.want_spin.setValue(want)
        self.want_spin.setMinimumHeight(28)
        self.want_spin.setFixedWidth(64)
        self.want_spin.valueChanged.connect(self._handle_change)

        self.btn_plus = QPushButton("+")
        self.btn_plus.setObjectName("iconBtn")
        self.btn_plus.setFixedSize(24, 24)
        self.btn_plus.clicked.connect(lambda: self._bump(1))

        layout.addWidget(self.btn_minus)
        layout.addWidget(self.want_spin)
        layout.addWidget(self.btn_plus)
        layout.addStretch(1)

    def _bump(self, delta: int):
        self.want_spin.setValue(max(self.want_spin.minimum(), min(self.want_spin.maximum(), self.want_spin.value() + delta)))

    def _handle_change(self, val: int):
        self.on_change(self.token.id, val)

    def _handle_rename(self):
        new_name = self.name_edit.text().strip() or f"Token #{self.token.id}"
        self.name_edit.setText(new_name)
        self.on_rename(self.token.id, new_name)

    def set_max(self, max_val: int):
        cur = self.want_spin.value()
        self.want_spin.setRange(0, max_val)
        self.want_spin.setValue(min(cur, max_val))

    def set_have_want(self, have: int, want: int):
        have_lbl = self.layout().itemAt(1).widget()
        have_lbl.setText(f"Have: {have}")
        self.want_spin.setValue(want)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        icon_path = resource_path("assets", "icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.setWindowTitle("NFS MW 2005 - Junkman Inventory (PC v1.3)")

        self.savefile: Optional[SaveFile] = None
        self.have_counts: Dict[int, int] = {}
        self.want_counts: Dict[int, int] = {}
        self.tokens: List[TokenEntry] = []
        self.safe_mode = True
        self.preserve_unknown = True
        self.clear_unknown_next = False
        self.show_only_changed = False

        self.catalog_path = _ensure_user_catalog_path()
        self.load_catalog()
        self._build_ui()
        self.refresh_state()

    # ---------- Catalog ----------
    def load_catalog(self):
        def from_list(toks):
            return [
                TokenEntry(
                    id=int(t.get("id")),
                    name=t.get("name", f"Token #{t.get('id')}"),
                    category=t.get("category", "Unknown"),
                )
                for t in toks
                if "id" in t
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
                out.append(
                    TokenEntry(
                        id=tid,
                        name=v.get("name", f"Token #{tid}"),
                        category=v.get("category", "Unknown"),
                    )
                )
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
                (1, "Brakes", "Performance"),
                (2, "Engine", "Performance"),
                (3, "NOS", "Performance"),
                (4, "Turbo", "Performance"),
                (5, "Suspension", "Performance"),
                (6, "Tires", "Performance"),
                (7, "Transmission", "Performance"),
                (8, "Body", "Visual"),
                (9, "Hood", "Visual"),
                (10, "Spoiler", "Visual"),
                (11, "Rims", "Visual"),
                (12, "Roof", "Visual"),
                (13, "Gauge", "Visual"),
                (14, "Vinyl", "Visual"),
                (15, "Decal", "Visual"),
                (16, "Paint", "Visual"),
                (17, "Out of Jail", "Police"),
                (20, "Imp. Strike", "Police"),
                (19, "Imp. Release?", "Police"),
                (18, "Unknown ID 18", "Unknown"),
            ]
            self.tokens = [TokenEntry(id=i, name=n, category=c) for i, n, c in defaults]
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

    # ---------- UI build ----------
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

        self.nav = self._build_nav()
        body.addLayout(self.nav, 0)

        self.stack = QStackedWidget()
        body.addWidget(self.stack, 1)

        self.page_junk = self._build_junk_page()
        self.page_profile = self._build_profile_page()
        self.page_presets = self._build_presets_page()
        self.page_settings = self._build_settings_page()
        self.page_about = self._build_about_page()

        self.stack.addWidget(self.page_junk)
        self.stack.addWidget(self.page_profile)
        self.stack.addWidget(self.page_presets)
        self.stack.addWidget(self.page_settings)
        self.stack.addWidget(self.page_about)

        self._select_page("Junkman")

        base.addLayout(self._build_footer())

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
        row.addWidget(self.btn_open)
        row.addWidget(self.btn_save_header)
        row.addWidget(self.btn_fix)
        row.addStretch(1)
        row.addWidget(self.lbl_file, 1)
        row.addWidget(self.lbl_unsaved)
        row.addWidget(self.lbl_status)
        return row

    def _build_nav(self):
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignTop)
        self.nav_buttons: Dict[str, QPushButton] = {}
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        for name in ["Junkman", "Profile", "Presets", "Settings", "About"]:
            btn = QPushButton(name)
            btn.setObjectName("navButton")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, n=name: self._select_page(n))
            self.nav_buttons[name] = btn
            self.nav_group.addButton(btn)
            layout.addWidget(btn)
        layout.addStretch(1)
        return layout

    def _build_junk_page(self):
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setSpacing(12)

        # left panel (filters/actions)
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

        cat_row = QVBoxLayout()
        cat_row.setSpacing(6)
        self.cat_buttons: Dict[str, QPushButton] = {}
        self.cat_group = QButtonGroup(self)
        self.cat_group.setExclusive(True)
        for cat in CAT_LIST:
            btn = QPushButton(cat)
            btn.setObjectName("catButton")
            btn.setCheckable(True)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setMinimumHeight(30)
            btn.clicked.connect(lambda _, c=cat: self._select_category(c))
            self.cat_buttons[cat] = btn
            self.cat_group.addButton(btn)
            cat_row.addWidget(btn)
        self.cat_buttons["All"].setChecked(True)
        left.addLayout(cat_row)

        left.addWidget(self._section_label("Quick actions"))
        self.btn_q_perf = QPushButton("Unlock Performance (1-7)")
        self.btn_q_vis = QPushButton("Unlock Visual (8-16)")
        self.btn_q_all = QPushButton("Unlock All (1-19)")
        self.btn_q_clear = QPushButton("Clear All (Want=0)")
        self.btn_q_perf.clicked.connect(lambda: self._quick_set(range(1, 8), 1))
        self.btn_q_vis.clicked.connect(lambda: self._quick_set(range(8, 17), 1))
        self.btn_q_all.clicked.connect(lambda: self._quick_set(range(1, 20), 1))
        self.btn_q_clear.clicked.connect(self.on_clear_all_want)
        for b in [self.btn_q_perf, self.btn_q_vis, self.btn_q_all, self.btn_q_clear]:
            left.addWidget(b)
        left.addStretch(1)

        left_widget = QWidget()
        left_widget.setLayout(left)
        left_widget.setFixedWidth(260)
        layout.addWidget(left_widget, 0)

        # right panel (cards)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        container_layout.setAlignment(Qt.AlignTop)
        self.cards_holder = QWidget()
        self.cards_holder.setMaximumWidth(1100)
        self.cards_holder.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.cards_layout = QVBoxLayout(self.cards_holder)
        self.cards_layout.setSpacing(8)
        self.cards_layout.setContentsMargins(8, 8, 8, 8)
        self.cards_layout.setAlignment(Qt.AlignTop)
        container_layout.addStretch(1)
        container_layout.addWidget(self.cards_holder)
        container_layout.addStretch(1)
        self.scroll.setWidget(container)
        layout.addWidget(self.scroll, 1)
        self._init_sections()
        return w

    def _build_profile_page(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        self.profile_info = QTextEdit()
        self.profile_info.setReadOnly(True)
        layout.addWidget(QLabel("Profile / Integrity"))
        layout.addWidget(self.profile_info)
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

        self.btn_clear_unknown = QPushButton("Clear Unknown (danger)")
        self.btn_clear_unknown.clicked.connect(self.on_clear_unknown_confirm)

        self.lbl_limits = QLabel("Limits: -")
        self.lbl_limits.setObjectName("mutedLabel")

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
        layout.addWidget(self.btn_clear_unknown)
        layout.addWidget(self.lbl_limits)
        layout.addLayout(catalog_row)
        layout.addStretch(1)
        return w

    def _build_about_page(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setText(
            "Junkman Inventory Editor for NFS MW 2005 PC v1.3\n"
            "Slot array is auto-detected per save (stride 0x0C).\n"
            "Apply writes to memory; Save+backup writes to disk."
        )
        layout.addWidget(text)
        return w

    def _build_footer(self):
        row = QHBoxLayout()
        row.setSpacing(10)
        self.lbl_free = QLabel("Free slots: -/-")
        self.lbl_free.setObjectName("pillLabel")
        self.btn_reset_want = QPushButton("Reset Want=Have")
        self.btn_apply = QPushButton("Apply (memory)")
        self.btn_save_footer = QPushButton("Save + backup")
        self.btn_reset_want.clicked.connect(self.on_reset_want)
        self.btn_apply.clicked.connect(self.on_apply_changes)
        self.btn_save_footer.clicked.connect(self.on_save)
        row.addWidget(self.lbl_free)
        row.addStretch(1)
        row.addWidget(self.btn_reset_want)
        row.addWidget(self.btn_apply)
        row.addWidget(self.btn_save_footer)
        return row

    # ---------- UI helpers ----------
    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("sectionLabel")
        return lbl

    def _section_header(self, text: str) -> QWidget:
        wrapper = QWidget()
        row = QHBoxLayout(wrapper)
        row.setContentsMargins(0, 6, 0, 2)
        row.setSpacing(10)
        lbl = self._section_label(text)
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Plain)
        line.setObjectName("sectionLine")
        row.addWidget(lbl)
        row.addWidget(line, 1)
        return wrapper

    def _init_sections(self):
        self.section_widgets: Dict[str, QWidget] = {}
        self.section_rows: Dict[str, QVBoxLayout] = {}
        for cat in ["Performance", "Visual", "Police", "Unknown"]:
            section = QWidget()
            section.setObjectName("sectionWidget")
            section.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            v = QVBoxLayout(section)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(6)
            v.addWidget(self._section_header(cat))

            rows_container = QWidget()
            rows_layout = QVBoxLayout(rows_container)
            rows_layout.setContentsMargins(0, 0, 0, 0)
            rows_layout.setSpacing(6)
            v.addWidget(rows_container)

            self.section_widgets[cat] = section
            self.section_rows[cat] = rows_layout
            self.cards_layout.addWidget(section)

        self.empty_label = QLabel("No tokens match your filter.")
        self.empty_label.setObjectName("mutedLabel")
        self.cards_layout.addWidget(self.empty_label)

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

    def _slot_capacity(self) -> int:
        if self.savefile and self.savefile.junkman:
            return self.savefile.junkman.slot_count
        return 59

    def _current_max(self) -> int:
        cap = self._slot_capacity()
        if self.safe_mode:
            return min(63, cap)
        return min(255, cap)

    def _unknown_ids(self) -> List[int]:
        return [t.id for t in self.tokens if t.category == "Unknown"]

    # ---------- State & rendering ----------
    def refresh_state(self):
        loaded = self.savefile is not None
        for btn in [
            self.btn_save_header,
            self.btn_save_footer,
            self.btn_fix,
            self.btn_apply,
            self.btn_reset_want,
            self.btn_q_perf,
            self.btn_q_vis,
            self.btn_q_all,
            self.btn_q_clear,
            self.btn_load_preset,
            self.btn_save_preset,
            self.btn_export_have,
            self.btn_clear_unknown,
        ]:
            btn.setEnabled(loaded)

        if loaded:
            self.lbl_file.setText(f"File: {self.savefile.path}")
            integrity = self.savefile.validate_integrity()
            status = []
            if integrity.md5_ok is True:
                status.append("MD5 OK")
            elif integrity.md5_ok is False:
                status.append("MD5 BAD")
            if integrity.crc_block1_ok:
                status.append("CRC1 OK")
            if integrity.crc_data_ok:
                status.append("CRCdata OK")
            if integrity.crc_block2_ok:
                status.append("CRC2 OK")
            self.lbl_status.setText("Status: " + ", ".join(status) if status else "Status: -")
            self.profile_info.setText(
                f"Hash scheme: {integrity.hash_scheme}\n"
                f"File size ok: {integrity.file_size_ok} ({integrity.actual_size})\n"
                f"MD5 stored: {integrity.stored_md5.hex()}\n"
                f"MD5 computed: {(integrity.computed_md5.hex() if integrity.computed_md5 else '-')}\n"
            )
            self.have_counts = self.savefile.get_junkman_counts()
            for tid in self.have_counts:
                self.ensure_token_entry(tid)
            if not self.want_counts:
                self.want_counts = dict(self.have_counts)
        else:
            self.lbl_file.setText("File: (not opened)")
            self.lbl_status.setText("Status: -")
            self.profile_info.setText("")
            self.have_counts = {}
            self.want_counts = {}

        self.lbl_limits.setText(
            f"Limits: Safe {min(63, self._slot_capacity())}, Advanced {min(255, self._slot_capacity())}"
        )
        self.refresh_cards()

    def refresh_cards(self):
        for cat, layout in self.section_rows.items():
            while layout.count():
                item = layout.takeAt(0)
                w = item.widget()
                if w:
                    w.deleteLater()

        term = self.search.text().lower() if self.search else ""
        active_cat = next((c for c, b in self.cat_buttons.items() if b.isChecked()), "All")
        max_val = self._current_max()

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

        any_added = False
        for cat in ["Performance", "Visual", "Police", "Unknown"]:
            toks = [t for t in self.tokens if t.category == cat and matches(t)]
            show_section = (active_cat == "All" or active_cat == cat) and bool(toks)
            self.section_widgets[cat].setVisible(show_section)
            if not show_section:
                continue
            any_added = True
            for t in toks:
                have = self.have_counts.get(t.id, 0)
                want = self.want_counts.get(t.id, have)
                row = TokenRow(
                    token=t,
                    have=have,
                    want=want,
                    max_val=max_val,
                    on_change=self.on_want_changed,
                    on_rename=self.on_token_renamed,
                )
                row.setProperty("changed", want != have)
                row.style().unpolish(row)
                row.style().polish(row)
                self.section_rows[cat].addWidget(row)

        self.empty_label.setVisible(not any_added)
        self._update_free_label()
        self._update_action_states()

    def _update_free_label(self):
        cap = self._slot_capacity()
        used = sum(self.have_counts.values())
        free = max(0, cap - used)
        self.lbl_free.setText(f"Free slots: {free}/{cap}")
        self._update_header_path()

    def _has_pending_changes(self) -> bool:
        for tid in set(self.want_counts.keys()) | set(self.have_counts.keys()):
            have = self.have_counts.get(tid, 0)
            want = self.want_counts.get(tid, have)
            if want != have:
                return True
        if self.clear_unknown_next:
            return True
        return False

    def _update_action_states(self):
        pending = self._has_pending_changes()
        enabled = self.savefile is not None
        self.btn_apply.setEnabled(enabled and pending)
        self.btn_reset_want.setEnabled(enabled)
        if pending:
            self.lbl_unsaved.setText("● Unsaved changes")
        else:
            self.lbl_unsaved.setText("")

    def _update_header_path(self):
        text = "File: (not opened)" if not self.savefile else f"{self.savefile.path}"
        fm = self.lbl_file.fontMetrics()
        available = max(120, self.lbl_file.width())
        self.lbl_file.setText(fm.elidedText(text, Qt.ElideMiddle, available))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_header_path()

    # ---------- Events ----------
    def on_token_renamed(self, tid: int, new_name: str):
        for t in self.tokens:
            if t.id == tid:
                t.name = new_name
                break
        self.save_catalog()
        self.refresh_cards()

    def on_want_changed(self, tid: int, val: int):
        self.want_counts[tid] = val
        if self.show_only_changed:
            self.refresh_cards()
            return
        # update row highlight without full refresh
        sender = self.sender()
        if sender is not None and hasattr(sender, "parent"):
            row = sender.parent()
            have = self.have_counts.get(tid, 0)
            row.setProperty("changed", val != have)
            row.style().unpolish(row)
            row.style().polish(row)
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

    def on_preserve_toggle(self):
        self.preserve_unknown = self.chk_preserve_unknown.isChecked()

    def on_toggle_show_changed(self):
        self.show_only_changed = self.chk_show_changed.isChecked()
        self.refresh_cards()

    def on_clear_unknown_confirm(self):
        if not self.savefile:
            return
        res = QMessageBox.warning(
            self,
            "Clear Unknown",
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
        self.refresh_cards()

    def on_clear_all_want(self):
        self.want_counts = {t.id: 0 for t in self.tokens}
        self.refresh_cards()

    # ---------- Apply ----------
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
        return (
            f"Total slots: {total}\n"
            f"Used (have): {used}\n"
            f"Free: {free}\n"
            f"Need (want): {needed}\n"
            f"Delta: +{add} / -{remove}\n"
            f"Unknown preserved: {unknown_preserved}"
        )

    def on_apply_changes(self):
        if not self.savefile:
            QMessageBox.warning(self, "No save", "Open a save first.")
            return
        want_full = self._build_want_full()
        needed = sum(want_full.values())
        cap = self._slot_capacity()
        if needed > cap:
            QMessageBox.warning(
                self,
                "Not enough slots",
                f"Need {needed} slots, have {cap}.\n"
                "Reduce Want values or clear a category.",
            )
            return
        summary = self._summary_text(want_full)
        res = QMessageBox.question(
            self,
            "Apply changes?",
            summary + "\n\nApply changes to loaded save (memory only)?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if res != QMessageBox.Yes:
            return
        try:
            self.savefile.set_junkman_counts(want_full, clamp_max=self._current_max())
            self.have_counts = self.savefile.get_junkman_counts()
            self.want_counts = dict(self.have_counts)
            self.clear_unknown_next = False
            self.refresh_cards()
            QMessageBox.information(self, "Applied", "Changes applied in memory. Use Save+backup to persist.")
        except Exception as e:
            QMessageBox.critical(self, "Apply failed", str(e))

    # ---------- Presets ----------
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
            counts = {int(k): int(v) for k, v in counts_obj.items() if int(v) >= 0}
            for tid in counts:
                self.ensure_token_entry(tid)
            self.want_counts.update(counts)
            self.refresh_cards()
        except Exception as e:
            QMessageBox.critical(self, "Load failed", str(e))

    def on_save_preset(self):
        if not self.savefile:
            QMessageBox.warning(self, "No save", "Open a save first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save preset", str(Path.home() / "junkman_preset.json"), "JSON (*.json)")
        if not path:
            return
        payload = {"counts": self.want_counts}
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        QMessageBox.information(self, "Saved", f"Preset saved to {path}")

    def on_export_have(self):
        if not self.savefile:
            QMessageBox.warning(self, "No save", "Open a save first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Have", str(Path.home() / "junkman_have.json"), "JSON (*.json)")
        if not path:
            return
        payload = {"counts": self.have_counts}
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        QMessageBox.information(self, "Exported", f"Have exported to {path}")

    # ---------- File ops ----------
    def on_open_catalog_folder(self):
        folder = self.catalog_path.parent
        opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
        if not opened and hasattr(os, "startfile"):
            try:
                os.startfile(folder)
            except Exception:
                pass

    def on_open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open save", str(Path.home()), "All files (*.*)")
        if not path:
            return
        try:
            self.savefile = SaveFile.load(path)
            self.want_counts = {}
            self.refresh_state()
        except Exception as e:
            QMessageBox.critical(self, "Open failed", str(e))

    def on_save(self):
        if not self.savefile:
            QMessageBox.warning(self, "No file", "Open a save first.")
            return
        try:
            self.savefile.save(make_backup=True)
            QMessageBox.information(self, "Saved", "Backup created and file saved.")
        except Exception as e:
            QMessageBox.critical(self, "Save failed", str(e))

    def on_fix_checksums(self):
        if not self.savefile:
            QMessageBox.warning(self, "No file", "Open a save first.")
            return
        status = self.savefile.fix_integrity()
        QMessageBox.information(self, "Checksums", f"Fixed. Scheme={status.hash_scheme}")
        self.refresh_state()


def build_window() -> MainWindow:
    return MainWindow()

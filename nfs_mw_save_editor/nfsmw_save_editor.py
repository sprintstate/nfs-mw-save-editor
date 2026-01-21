import hashlib
import os
import struct
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QCheckBox,
)


# ------------------------- EA CRC32 (as described in MW save editor techinfo) -------------------------

def _ea_crc32_table() -> List[int]:
    # Big-endian CRC32 table with poly 0x04C11DB7
    poly = 0x04C11DB7
    table: List[int] = []
    for i in range(256):
        c = (i << 24) & 0xFFFFFFFF
        for _ in range(8):
            if c & 0x80000000:
                c = ((c << 1) ^ poly) & 0xFFFFFFFF
            else:
                c = (c << 1) & 0xFFFFFFFF
        table.append(c)
    return table


_EA_CRC32_TAB = _ea_crc32_table()


def ea_crc32(data: bytes) -> int:
    # Matches the algorithm structure shown in the tech info:
    # init from first 4 bytes (big-endian), bitwise not, then byte-wise with table.
    if len(data) < 4:
        return 0
    b0, b1, b2, b3 = data[0], data[1], data[2], data[3]
    crc = ((b0 << 24) | (b1 << 16) | (b2 << 8) | b3) & 0xFFFFFFFF
    crc = (~crc) & 0xFFFFFFFF
    for byte in data[4:]:
        idx = (crc >> 24) & 0xFF
        crc = ((((crc << 8) & 0xFFFFFFFF) | byte) ^ _EA_CRC32_TAB[idx]) & 0xFFFFFFFF
    return (~crc) & 0xFFFFFFFF


# ------------------------- Save core -------------------------

@dataclass
class SaveLayout:
    saved_data_offset: int = 0x34
    md5_len: int = 16


class NfsMwSave:
    def __init__(self, raw: bytearray, path: str, layout: SaveLayout = SaveLayout()):
        self.raw = raw
        self.path = path
        self.layout = layout

    @staticmethod
    def load(path: str) -> "NfsMwSave":
        with open(path, "rb") as f:
            data = bytearray(f.read())
        s = NfsMwSave(data, path)
        s._basic_validate_or_raise()
        return s

    def _basic_validate_or_raise(self) -> None:
        if len(self.raw) < 0x34 + 16:
            raise ValueError("Файл слишком маленький, не похож на сейв MW.")
        if self.raw[0:4] != b"MC02":
            raise ValueError("Magic не MC02 — это не профиль NFS MW 2005 (PC).")
        file_len = struct.unpack_from("<I", self.raw, 0x4)[0]
        if file_len != len(self.raw):
            # Не всегда критично, но подозрительно.
            # Лучше просто предупреждать в UI, но для ядра оставим мягко.
            pass

    def saved_data_slice(self) -> Tuple[int, int]:
        start = self.layout.saved_data_offset
        end = len(self.raw) - self.layout.md5_len
        if end <= start:
            raise ValueError("Некорректная разметка saved_data / MD5.")
        return start, end

    def get_saved_data(self) -> bytes:
        start, end = self.saved_data_slice()
        return bytes(self.raw[start:end])

    def get_md5_in_file(self) -> bytes:
        return bytes(self.raw[len(self.raw) - self.layout.md5_len:])

    def compute_md5(self) -> bytes:
        return hashlib.md5(self.get_saved_data()).digest()

    def md5_matches(self) -> bool:
        return self.compute_md5() == self.get_md5_in_file()

    def update_md5(self) -> None:
        digest = self.compute_md5()
        self.raw[len(self.raw) - self.layout.md5_len:] = digest

    def update_crcs(self) -> None:
        # Per tech info:
        # crc32_blk1 @0x10: crc32 of 8-byte block at 0x1C
        # crc32_data @0x14: crc32 of data at 0x24 till end-of-file
        # crc32_blk2 @0x18: crc32 of 0x18 byte block from file beginning (0..0x17)
        blk1 = ea_crc32(bytes(self.raw[0x1C:0x24]))
        data_crc = ea_crc32(bytes(self.raw[0x24:]))
        struct.pack_into("<I", self.raw, 0x10, blk1)
        struct.pack_into("<I", self.raw, 0x14, data_crc)
        blk2 = ea_crc32(bytes(self.raw[0x00:0x18]))
        struct.pack_into("<I", self.raw, 0x18, blk2)

    def fix_checksums(self) -> None:
        # Order: saved_data changed -> update MD5 -> update CRCs (which include MD5 in data_crc)
        self.update_md5()
        self.update_crcs()

    def backup_path(self) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{self.path}.bak_{ts}"

    def save_in_place(self, make_backup: bool = True) -> None:
        if make_backup:
            bp = self.backup_path()
            with open(bp, "wb") as f:
                f.write(self.raw)
        with open(self.path, "wb") as f:
            f.write(self.raw)

    # ----- generic read/write helpers -----

    def read_u32(self, file_offset: int) -> int:
        return struct.unpack_from("<I", self.raw, file_offset)[0]

    def write_u32(self, file_offset: int, value: int) -> None:
        struct.pack_into("<I", self.raw, file_offset, int(value) & 0xFFFFFFFF)

    def read_u8(self, file_offset: int) -> int:
        return self.raw[file_offset]

    def write_u8(self, file_offset: int, value: int) -> None:
        self.raw[file_offset] = int(value) & 0xFF

    # ----- scanning -----

    def find_u32_in_saved_data(self, value: int) -> List[int]:
        needle = struct.pack("<I", int(value) & 0xFFFFFFFF)
        saved = self.get_saved_data()
        base = self.layout.saved_data_offset
        hits: List[int] = []
        i = 0
        while True:
            j = saved.find(needle, i)
            if j == -1:
                break
            hits.append(base + j)
            i = j + 1
        return hits


def diff_saved_data(a: NfsMwSave, b: NfsMwSave) -> List[Tuple[int, int, int]]:
    a_start, a_end = a.saved_data_slice()
    b_start, b_end = b.saved_data_slice()
    if (a_end - a_start) != (b_end - b_start):
        raise ValueError("saved_data разной длины — сравнение некорректно.")
    diffs: List[Tuple[int, int, int]] = []
    for i in range(a_end - a_start):
        av = a.raw[a_start + i]
        bv = b.raw[b_start + i]
        if av != bv:
            diffs.append((a_start + i, av, bv))
    return diffs


# ------------------------- GUI -------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NFS MW 2005 (PC) Save Editor — MVP")

        self.save: Optional[NfsMwSave] = None

        # remembered offsets (user-selected)
        self.money_offset: Optional[int] = None
        self.bounty_offset: Optional[int] = None
        self.junkman_offset: Optional[int] = None

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.overview_tab = self._build_overview_tab()
        self.money_tab = self._build_money_tab()
        self.junkman_tab = self._build_junkman_tab()
        self.tools_tab = self._build_tools_tab()

        self.tabs.addTab(self.overview_tab, "Overview")
        self.tabs.addTab(self.money_tab, "Money/Bounty")
        self.tabs.addTab(self.junkman_tab, "Junkman")
        self.tabs.addTab(self.tools_tab, "Tools")

        self._refresh_ui()

    # ---------- Tabs ----------

    def _build_overview_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        top = QHBoxLayout()
        self.path_label = QLabel("No file loaded")
        self.open_btn = QPushButton("Open save...")
        self.open_btn.clicked.connect(self.on_open)

        self.save_btn = QPushButton("Save (fix checksums)")
        self.save_btn.clicked.connect(self.on_save)

        top.addWidget(self.path_label, 1)
        top.addWidget(self.open_btn)
        top.addWidget(self.save_btn)
        layout.addLayout(top)

        self.status_box = QTextEdit()
        self.status_box.setReadOnly(True)
        layout.addWidget(self.status_box, 1)

        return w

    def _build_money_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        # Money group
        money_g = QGroupBox("Money")
        money_l = QVBoxLayout(money_g)

        f1 = QHBoxLayout()
        self.money_current = QSpinBox()
        self.money_current.setRange(0, 2_000_000_000)
        self.money_scan_btn = QPushButton("Scan")
        self.money_scan_btn.clicked.connect(self.on_scan_money)
        f1.addWidget(QLabel("Current value (in-game):"))
        f1.addWidget(self.money_current, 1)
        f1.addWidget(self.money_scan_btn)
        money_l.addLayout(f1)

        self.money_hits = QListWidget()
        self.money_hits.itemSelectionChanged.connect(self.on_pick_money_offset)
        money_l.addWidget(self.money_hits, 1)

        f2 = QHBoxLayout()
        self.money_new = QSpinBox()
        self.money_new.setRange(0, 2_000_000_000)
        self.money_apply_btn = QPushButton("Apply")
        self.money_apply_btn.clicked.connect(self.on_apply_money)
        self.money_offset_label = QLabel("Offset: —")
        f2.addWidget(QLabel("New value:"))
        f2.addWidget(self.money_new, 1)
        f2.addWidget(self.money_apply_btn)
        f2.addWidget(self.money_offset_label)
        money_l.addLayout(f2)

        # Bounty group
        bounty_g = QGroupBox("Bounty (обычно меняют для 1-й машины)")
        bounty_l = QVBoxLayout(bounty_g)

        b1 = QHBoxLayout()
        self.bounty_current = QSpinBox()
        self.bounty_current.setRange(0, 2_000_000_000)
        self.bounty_scan_btn = QPushButton("Scan")
        self.bounty_scan_btn.clicked.connect(self.on_scan_bounty)
        b1.addWidget(QLabel("Current value (in-game):"))
        b1.addWidget(self.bounty_current, 1)
        b1.addWidget(self.bounty_scan_btn)
        bounty_l.addLayout(b1)

        self.bounty_hits = QListWidget()
        self.bounty_hits.itemSelectionChanged.connect(self.on_pick_bounty_offset)
        bounty_l.addWidget(self.bounty_hits, 1)

        b2 = QHBoxLayout()
        self.bounty_new = QSpinBox()
        self.bounty_new.setRange(0, 2_000_000_000)
        self.bounty_apply_btn = QPushButton("Apply")
        self.bounty_apply_btn.clicked.connect(self.on_apply_bounty)
        self.bounty_offset_label = QLabel("Offset: —")
        b2.addWidget(QLabel("New value:"))
        b2.addWidget(self.bounty_new, 1)
        b2.addWidget(self.bounty_apply_btn)
        b2.addWidget(self.bounty_offset_label)
        bounty_l.addLayout(b2)

        layout.addWidget(money_g, 1)
        layout.addWidget(bounty_g, 1)

        return w

    def _build_junkman_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        top = QHBoxLayout()
        self.junkman_offset_edit = QLineEdit()
        self.junkman_offset_edit.setPlaceholderText("file offset (hex), e.g. 0x1234")
        self.junkman_set_offset_btn = QPushButton("Set offset")
        self.junkman_set_offset_btn.clicked.connect(self.on_set_junkman_offset)

        self.junkman_autofind_btn = QPushButton("Auto-find from two saves...")
        self.junkman_autofind_btn.clicked.connect(self.on_autofind_junkman)

        self.junkman_byte_label = QLabel("Current byte: —")

        top.addWidget(QLabel("Junkman byte offset:"))
        top.addWidget(self.junkman_offset_edit, 1)
        top.addWidget(self.junkman_set_offset_btn)
        top.addWidget(self.junkman_autofind_btn)
        top.addWidget(self.junkman_byte_label)
        layout.addLayout(top)

        # checkboxes (bitmask)
        self.jm_checks: List[QCheckBox] = []
        grid = QHBoxLayout()

        labels = [
            "Engine", "Transmission", "Suspension", "Brakes",
            "Tires", "Nitrous", "Turbo", "Supercharger/Other",
        ]
        left = QVBoxLayout()
        right = QVBoxLayout()
        for i, name in enumerate(labels):
            cb = QCheckBox(f"Bit {i}: {name}")
            cb.stateChanged.connect(self.on_junkman_checkbox_changed)
            self.jm_checks.append(cb)
            (left if i < 4 else right).addWidget(cb)
        grid.addLayout(left)
        grid.addLayout(right)
        layout.addLayout(grid)

        buttons = QHBoxLayout()
        self.jm_set_5f = QPushButton("Set byte = 0x5F")
        self.jm_set_7f = QPushButton("Set byte = 0x7F")
        self.jm_apply = QPushButton("Apply")
        self.jm_set_5f.clicked.connect(lambda: self._set_junkman_byte_direct(0x5F))
        self.jm_set_7f.clicked.connect(lambda: self._set_junkman_byte_direct(0x7F))
        self.jm_apply.clicked.connect(self.on_apply_junkman)

        buttons.addWidget(self.jm_set_5f)
        buttons.addWidget(self.jm_set_7f)
        buttons.addWidget(self.jm_apply)
        layout.addLayout(buttons)

        self.junkman_log = QTextEdit()
        self.junkman_log.setReadOnly(True)
        layout.addWidget(self.junkman_log, 1)

        return w

    def _build_tools_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        line = QHBoxLayout()
        self.diff_a_btn = QPushButton("Pick Save A...")
        self.diff_b_btn = QPushButton("Pick Save B...")
        self.diff_run_btn = QPushButton("Diff saved_data")
        self.diff_run_btn.clicked.connect(self.on_diff)

        self.diff_a_path = QLabel("A: —")
        self.diff_b_path = QLabel("B: —")
        self._diff_a: Optional[str] = None
        self._diff_b: Optional[str] = None

        self.diff_a_btn.clicked.connect(lambda: self._pick_diff_file("A"))
        self.diff_b_btn.clicked.connect(lambda: self._pick_diff_file("B"))

        line.addWidget(self.diff_a_btn)
        line.addWidget(self.diff_b_btn)
        line.addWidget(self.diff_run_btn)
        layout.addLayout(line)
        layout.addWidget(self.diff_a_path)
        layout.addWidget(self.diff_b_path)

        self.diff_out = QTextEdit()
        self.diff_out.setReadOnly(True)
        layout.addWidget(self.diff_out, 1)

        return w

    # ---------- UI helpers ----------

    def _refresh_ui(self) -> None:
        has = self.save is not None
        self.save_btn.setEnabled(has)

        self.money_scan_btn.setEnabled(has)
        self.money_apply_btn.setEnabled(has and self.money_offset is not None)

        self.bounty_scan_btn.setEnabled(has)
        self.bounty_apply_btn.setEnabled(has and self.bounty_offset is not None)

        self.junkman_set_offset_btn.setEnabled(has)
        self.junkman_autofind_btn.setEnabled(has)
        self.jm_apply.setEnabled(has and self.junkman_offset is not None)
        self.jm_set_5f.setEnabled(has and self.junkman_offset is not None)
        self.jm_set_7f.setEnabled(has and self.junkman_offset is not None)

        for cb in self.jm_checks:
            cb.setEnabled(has and self.junkman_offset is not None)

        # Update labels
        if not has:
            self.path_label.setText("No file loaded")
            self.status_box.setText("")
            self.money_offset_label.setText("Offset: —")
            self.bounty_offset_label.setText("Offset: —")
            self.junkman_byte_label.setText("Current byte: —")
            return

        s = self.save
        assert s is not None

        self.path_label.setText(s.path)

        # status
        md5_ok = s.md5_matches()
        file_len = len(s.raw)
        magic = s.raw[0:4].decode(errors="replace")
        unk2 = struct.unpack_from("<I", s.raw, 0x1C)[0]
        status = []
        status.append(f"Magic: {magic}")
        status.append(f"File size: {file_len} bytes")
        status.append(f"Header unknown2 @0x1C: 0x{unk2:08X}")
        status.append(f"MD5 matches: {'YES' if md5_ok else 'NO (will be fixed on Save)'}")
        if file_len != 63596:
            status.append("⚠️ Размер не 63 596 — старые оффсетные схемы могут не подойти.")
        status.append("")
        status.append("Tip: лучше закрыть игру или хотя бы перезагрузить профиль после правок.")
        self.status_box.setText("\n".join(status))

        # offsets
        self.money_offset_label.setText(f"Offset: {self._fmt_off(self.money_offset)}")
        self.bounty_offset_label.setText(f"Offset: {self._fmt_off(self.bounty_offset)}")

        # junkman
        self._refresh_junkman_view()

    @staticmethod
    def _fmt_off(off: Optional[int]) -> str:
        return "—" if off is None else f"0x{off:08X}"

    def _warn(self, title: str, text: str) -> None:
        QMessageBox.warning(self, title, text)

    def _info(self, title: str, text: str) -> None:
        QMessageBox.information(self, title, text)

    # ---------- Actions ----------

    def on_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open NFS MW save (MC02)", "", "All Files (*)"
        )
        if not path:
            return
        try:
            self.save = NfsMwSave.load(path)
            self.money_offset = None
            self.bounty_offset = None
            self.junkman_offset = None
            self.money_hits.clear()
            self.bounty_hits.clear()
            self.junkman_log.setText("")
        except Exception as e:
            self.save = None
            self._warn("Open failed", str(e))
        self._refresh_ui()

    def on_save(self) -> None:
        if not self.save:
            return
        try:
            self.save.fix_checksums()
            # backup original before overwriting
            backup = self.save.backup_path()
            with open(backup, "wb") as f:
                f.write(self.save.raw)
            with open(self.save.path, "wb") as f:
                f.write(self.save.raw)
            self._info("Saved", f"Saved with fixed checksums.\nBackup created:\n{backup}")
        except Exception as e:
            self._warn("Save failed", str(e))
        self._refresh_ui()

    # ----- Money/Bounty scan/apply -----

    def on_scan_money(self) -> None:
        if not self.save:
            return
        val = int(self.money_current.value())
        hits = self.save.find_u32_in_saved_data(val)
        self.money_hits.clear()
        for off in hits[:500]:
            item = QListWidgetItem(f"{self._fmt_off(off)}  (u32 LE match)")
            item.setData(Qt.UserRole, off)
            self.money_hits.addItem(item)
        if not hits:
            self._warn("No hits", "Совпадений не найдено. Проверь значение или сделай его уникальным в игре (например 1234567).")

    def on_pick_money_offset(self) -> None:
        items = self.money_hits.selectedItems()
        if not items:
            self.money_offset = None
        else:
            self.money_offset = int(items[0].data(Qt.UserRole))
        self._refresh_ui()

    def on_apply_money(self) -> None:
        if not self.save or self.money_offset is None:
            return
        try:
            newv = int(self.money_new.value())
            self.save.write_u32(self.money_offset, newv)
            self._info("Applied", f"Money written at {self._fmt_off(self.money_offset)}.\nNow press Save (fix checksums).")
        except Exception as e:
            self._warn("Apply failed", str(e))
        self._refresh_ui()

    def on_scan_bounty(self) -> None:
        if not self.save:
            return
        val = int(self.bounty_current.value())
        hits = self.save.find_u32_in_saved_data(val)
        self.bounty_hits.clear()
        for off in hits[:500]:
            item = QListWidgetItem(f"{self._fmt_off(off)}  (u32 LE match)")
            item.setData(Qt.UserRole, off)
            self.bounty_hits.addItem(item)
        if not hits:
            self._warn("No hits", "Совпадений не найдено. Лучше выставь в игре уникальное число и пересохранись.")

    def on_pick_bounty_offset(self) -> None:
        items = self.bounty_hits.selectedItems()
        if not items:
            self.bounty_offset = None
        else:
            self.bounty_offset = int(items[0].data(Qt.UserRole))
        self._refresh_ui()

    def on_apply_bounty(self) -> None:
        if not self.save or self.bounty_offset is None:
            return
        try:
            newv = int(self.bounty_new.value())
            self.save.write_u32(self.bounty_offset, newv)
            self._info("Applied", f"Bounty written at {self._fmt_off(self.bounty_offset)}.\nNow press Save (fix checksums).")
        except Exception as e:
            self._warn("Apply failed", str(e))
        self._refresh_ui()

    # ----- Junkman -----

    def on_set_junkman_offset(self) -> None:
        if not self.save:
            return
        t = self.junkman_offset_edit.text().strip().lower()
        if not t:
            self._warn("Offset", "Введи оффсет, например 0x1234")
            return
        try:
            off = int(t, 16) if t.startswith("0x") else int(t, 16)
            if off < 0 or off >= len(self.save.raw):
                raise ValueError("Offset out of range")
            self.junkman_offset = off
            self.junkman_log.append(f"Set junkman offset = {self._fmt_off(off)}")
        except Exception as e:
            self._warn("Offset parse failed", str(e))
        self._refresh_ui()

    def _refresh_junkman_view(self) -> None:
        if not self.save or self.junkman_offset is None:
            self.junkman_byte_label.setText("Current byte: —")
            return
        try:
            b = self.save.read_u8(self.junkman_offset)
            self.junkman_byte_label.setText(f"Current byte: 0x{b:02X} @ {self._fmt_off(self.junkman_offset)}")
            for i, cb in enumerate(self.jm_checks):
                cb.blockSignals(True)
                cb.setChecked(bool(b & (1 << i)))
                cb.blockSignals(False)
        except Exception as e:
            self._warn("Junkman read failed", str(e))

    def on_junkman_checkbox_changed(self) -> None:
        # live preview label only (no write yet)
        if not self.save or self.junkman_offset is None:
            return
        b = 0
        for i, cb in enumerate(self.jm_checks):
            if cb.isChecked():
                b |= (1 << i)
        self.junkman_byte_label.setText(f"Current byte: 0x{b:02X} (preview) @ {self._fmt_off(self.junkman_offset)}")

    def _set_junkman_byte_direct(self, value: int) -> None:
        if not self.save or self.junkman_offset is None:
            return
        try:
            self.save.write_u8(self.junkman_offset, value)
            self.junkman_log.append(f"Wrote byte 0x{value:02X} at {self._fmt_off(self.junkman_offset)}")
        except Exception as e:
            self._warn("Write failed", str(e))
        self._refresh_ui()

    def on_apply_junkman(self) -> None:
        if not self.save or self.junkman_offset is None:
            return
        try:
            b = 0
            for i, cb in enumerate(self.jm_checks):
                if cb.isChecked():
                    b |= (1 << i)
            self.save.write_u8(self.junkman_offset, b)
            self.junkman_log.append(f"Applied bitmask 0x{b:02X} at {self._fmt_off(self.junkman_offset)}")
            self._info("Applied", "Junkman byte written. Now press Save (fix checksums).")
        except Exception as e:
            self._warn("Apply failed", str(e))
        self._refresh_ui()

    def on_autofind_junkman(self) -> None:
        # Pick two saves, diff, suggest byte-sized candidates
        if not self.save:
            return

        a_path, _ = QFileDialog.getOpenFileName(self, "Pick Save A (before junkman)", "", "All Files (*)")
        if not a_path:
            return
        b_path, _ = QFileDialog.getOpenFileName(self, "Pick Save B (after junkman)", "", "All Files (*)")
        if not b_path:
            return

        try:
            a = NfsMwSave.load(a_path)
            b = NfsMwSave.load(b_path)
            diffs = diff_saved_data(a, b)
            # heuristics: prefer single-byte diffs that look like bitmasks
            cands: List[Tuple[int, int, int, int]] = []  # (score, off, old, new)
            for off, old, new in diffs:
                score = 0
                # common patterns for bitmask-ish changes
                if old == 0x00 and new in (0x5F, 0x7F):
                    score += 10
                if (old ^ new) != 0 and ((old ^ new) & 0xFF) == (old ^ new):
                    score += 2
                if new in (0x1F, 0x3F, 0x5F, 0x7F, 0xFF):
                    score += 3
                if (new & 0x80) == 0:
                    score += 1
                if score > 0:
                    cands.append((score, off, old, new))

            cands.sort(reverse=True, key=lambda x: x[0])
            if not cands:
                self._warn("Auto-find", f"Не нашёл понятных кандидатов. Diff bytes: {len(diffs)}.\nПопробуй сделать изменения более “узкие”: установить/снять ровно 1 junkman деталь и пересохраниться.")
                return

            # show top candidates in a picker list
            picker = QMessageBox(self)
            picker.setWindowTitle("Junkman candidates")
            picker.setText("Нашёл кандидаты (топ-10). Выбери номер и нажми OK.\n"
                           "Если не уверен — выбирай тот, где new=0x5F/0x7F, и потом проверим в игре.")
            details = "\n".join(
                [f"{i+1}) score={sc} off={self._fmt_off(off)}  {old:02X}->{new:02X}"
                 for i, (sc, off, old, new) in enumerate(cands[:10])]
            )
            picker.setDetailedText(details)
            picker.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            if picker.exec() != QMessageBox.Ok:
                return

            # by default pick best candidate
            best = cands[0]
            self.junkman_offset = best[1]
            self.junkman_offset_edit.setText(self._fmt_off(self.junkman_offset))
            self.junkman_log.append(f"Auto-picked offset = {self._fmt_off(self.junkman_offset)} (score={best[0]}, {best[2]:02X}->{best[3]:02X})")
        except Exception as e:
            self._warn("Auto-find failed", str(e))

        self._refresh_ui()

    # ----- Tools / diff -----

    def _pick_diff_file(self, which: str) -> None:
        path, _ = QFileDialog.getOpenFileName(self, f"Pick Save {which}", "", "All Files (*)")
        if not path:
            return
        if which == "A":
            self._diff_a = path
            self.diff_a_path.setText(f"A: {path}")
        else:
            self._diff_b = path
            self.diff_b_path.setText(f"B: {path}")

    def on_diff(self) -> None:
        if not self._diff_a or not self._diff_b:
            self._warn("Diff", "Pick both A and B first.")
            return
        try:
            a = NfsMwSave.load(self._diff_a)
            b = NfsMwSave.load(self._diff_b)
            diffs = diff_saved_data(a, b)
            out = []
            out.append(f"Diff count (saved_data): {len(diffs)}")
            out.append("Showing first 200 diffs as: offset  old->new")
            for off, old, new in diffs[:200]:
                out.append(f"{self._fmt_off(off)}  {old:02X}->{new:02X}")
            self.diff_out.setText("\n".join(out))
        except Exception as e:
            self._warn("Diff failed", str(e))


def main() -> int:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.resize(980, 720)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

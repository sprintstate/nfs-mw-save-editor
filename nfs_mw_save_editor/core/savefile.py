from __future__ import annotations

import datetime
import hashlib
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple

from core.checksums import ea_crc32
from core.junkman import JunkmanInventory

HashScheme = Optional[Literal["md5_saved_data", "md5_all_minus_tail"]]


@dataclass(frozen=True)
class SaveLayout:
    saved_data_offset: int = 0x34
    md5_len: int = 16
    file_size_offset: int = 0x04
    crc_block1_offset: int = 0x10
    crc_data_offset: int = 0x14
    crc_block2_offset: int = 0x18
    crc_block1_range: Tuple[int, int] = (0x1C, 0x24)
    crc_data_start: int = 0x24
    crc_block2_range: Tuple[int, int] = (0x00, 0x18)
    magic: bytes = b"MC02"
    header_len: int = 0x34


@dataclass
class IntegrityStatus:
    hash_scheme: HashScheme
    md5_ok: Optional[bool]
    crc_block1_ok: Optional[bool]
    crc_data_ok: Optional[bool]
    crc_block2_ok: Optional[bool]
    file_size_ok: bool
    stored_size: int
    actual_size: int
    stored_md5: bytes
    computed_md5: Optional[bytes]
    crc_details: Dict[str, Tuple[int, int]]


@dataclass(frozen=True)
class GarageSlot:
    slot_index: int
    car_id: int
    occupied: bool
    bounty: int
    escaped: int
    busted: int
    abs_off: int


class SaveFile:
    # Junkman inventory slot layout (dynamically detected)
    SAVED_DATA_START = JunkmanInventory.SAVED_DATA_START
    SLOT_STRIDE = JunkmanInventory.SLOT_STRIDE
    SLOT_TYPE_OFF = 0x00
    SLOT_COUNT_OFF = 0x08
    SLOT_SIZE = JunkmanInventory.SLOT_SIZE
    SLOT_MAX = 200  # upper bound for diff helpers
    MONEY_OFFSET = 0x4039
    GARAGE_BASE_OFFSET = 0xE2ED
    GARAGE_SLOT_SIZE = 0x38
    GARAGE_BOUNTY_OFFSET = 0x10
    GARAGE_ESCAPED_OFFSET = 0x14
    GARAGE_BUSTED_OFFSET = 0x16
    GARAGE_SIGNATURE_A = b"\xCD\x03\x00"
    GARAGE_SIGNATURE_B = b"\x00\x00\xCD\xCD"
    INVALID_CAR_ID = 0xFF

    def __init__(self, path: Path, data: bytearray, layout: SaveLayout | None = None, hash_scheme: HashScheme = None):
        self.path = path
        self.data = data
        self.layout = layout or SaveLayout()
        self.hash_scheme = hash_scheme or self.detect_hash_scheme()
        self._junk_base_cache: Optional[int] = None
        self.junkman = JunkmanInventory(self)
        self._junk_base_cache = self.junkman.base_rel

    @staticmethod
    def load(path: str | Path) -> "SaveFile":
        p = Path(path)
        data = bytearray(p.read_bytes())
        sf = SaveFile(path=p, data=data)
        sf.hash_scheme = sf.detect_hash_scheme()
        return sf

    # --- basic helpers ---

    def _read_u32(self, offset: int) -> int:
        return struct.unpack_from("<I", self.data, offset)[0]

    def _read_u16(self, offset: int) -> int:
        return struct.unpack_from("<H", self.data, offset)[0]

    def _read_u8(self, offset: int) -> int:
        return self.data[offset]

    def _write_u32(self, offset: int, value: int) -> None:
        struct.pack_into("<I", self.data, offset, int(value) & 0xFFFFFFFF)

    @staticmethod
    def _require_u32(value: int) -> int:
        ivalue = int(value)
        if not (0 <= ivalue <= 0xFFFFFFFF):
            raise ValueError("value must be in range 0..4294967295")
        return ivalue

    def saved_data_slice(self) -> Tuple[int, int]:
        start = self.layout.saved_data_offset
        if start != self.SAVED_DATA_START:
            # Enforce ground truth for PC v1.3
            start = self.SAVED_DATA_START
        end = len(self.data) - self.layout.md5_len
        if end <= start:
            raise ValueError("saved_data slice is invalid for this file")
        return start, end

    def saved_data_start(self) -> int:
        return self.saved_data_slice()[0]

    def saved_data(self) -> bytes:
        s, e = self.saved_data_slice()
        return bytes(self.data[s:e])

    def abs_to_rel(self, abs_off: int) -> int:
        return abs_off - self.saved_data_start()

    def tail_md5(self) -> bytes:
        return bytes(self.data[-self.layout.md5_len:])

    # --- hashing ---

    def md5_saved_data(self) -> bytes:
        return hashlib.md5(self.saved_data()).digest()

    def md5_all_minus_tail(self) -> bytes:
        if len(self.data) <= self.layout.md5_len:
            return b""
        return hashlib.md5(bytes(self.data[:-self.layout.md5_len])).digest()

    def detect_hash_scheme(self) -> HashScheme:
        if len(self.data) < self.layout.md5_len:
            return None
        tail = self.tail_md5()
        if self.md5_saved_data() == tail:
            return "md5_saved_data"
        if self.md5_all_minus_tail() == tail:
            return "md5_all_minus_tail"
        return None

    # --- CRCs ---

    def _bounded_slice(self, start: int, end: int) -> bytes:
        if start < 0:
            start = 0
        if end < 0:
            end = 0
        end = min(end, len(self.data))
        start = min(start, end)
        return bytes(self.data[start:end])

    def compute_crc_block1(self) -> int:
        a, b = self.layout.crc_block1_range
        return ea_crc32(self._bounded_slice(a, b))

    def compute_crc_data(self) -> int:
        return ea_crc32(self._bounded_slice(self.layout.crc_data_start, len(self.data)))

    def compute_crc_block2(self) -> int:
        a, b = self.layout.crc_block2_range
        return ea_crc32(self._bounded_slice(a, b))

    # --- scanning helpers ---

    def find_u32_in_saved_data(self, value: int, limit: Optional[int] = 5000) -> list[int]:
        needle = struct.pack("<I", int(value) & 0xFFFFFFFF)
        start, end = self.saved_data_slice()
        hay = self.data[start:end]
        res: list[int] = []
        i = 0
        while True:
            j = hay.find(needle, i)
            if j == -1:
                break
            res.append(start + j)
            i = j + 1
            if limit is not None and len(res) >= limit:
                break
        return res

    # --- economy / garage bounty ---

    def get_money(self) -> int:
        return self._read_u32(self.MONEY_OFFSET)

    def set_money(self, value: int) -> None:
        self._write_u32(self.MONEY_OFFSET, self._require_u32(value))

    @classmethod
    def _is_garage_slot(cls, raw: bytes) -> bool:
        return (
            len(raw) == cls.GARAGE_SLOT_SIZE
            and raw[1:4] == cls.GARAGE_SIGNATURE_A
            and raw[8:12] == cls.GARAGE_SIGNATURE_B
        )

    def get_garage_slots(self) -> List[GarageSlot]:
        slots: List[GarageSlot] = []
        slot_index = 0
        base_off = self.GARAGE_BASE_OFFSET

        while base_off + self.GARAGE_SLOT_SIZE <= len(self.data):
            raw = bytes(self.data[base_off:base_off + self.GARAGE_SLOT_SIZE])
            if not self._is_garage_slot(raw):
                break
            car_id = raw[0]
            slots.append(
                GarageSlot(
                    slot_index=slot_index,
                    car_id=car_id,
                    occupied=(car_id != self.INVALID_CAR_ID),
                    bounty=self._read_u32(base_off + self.GARAGE_BOUNTY_OFFSET),
                    escaped=self._read_u16(base_off + self.GARAGE_ESCAPED_OFFSET),
                    busted=self._read_u16(base_off + self.GARAGE_BUSTED_OFFSET),
                    abs_off=base_off,
                )
            )
            base_off += self.GARAGE_SLOT_SIZE
            slot_index += 1

        if not slots:
            raise ValueError("Failed to detect garage block")
        return slots

    def set_slot_bounty(self, slot_index: int, value: int) -> None:
        wanted = int(slot_index)
        bounty = self._require_u32(value)
        for slot in self.get_garage_slots():
            if slot.slot_index == wanted:
                self._write_u32(slot.abs_off + self.GARAGE_BOUNTY_OFFSET, bounty)
                return
        raise ValueError(f"Garage slot {wanted} was not detected")

    def get_total_bounty(self) -> int:
        return sum(slot.bounty for slot in self.get_garage_slots())

    def get_escape_bust_totals(self) -> Tuple[int, int]:
        slots = self.get_garage_slots()
        return (
            sum(slot.escaped for slot in slots),
            sum(slot.busted for slot in slots),
        )

    # --- integrity ---

    def validate_integrity(self) -> IntegrityStatus:
        scheme = self.hash_scheme or self.detect_hash_scheme()
        stored_md5 = self.tail_md5()
        computed_md5: Optional[bytes] = None
        md5_ok: Optional[bool] = None
        if scheme == "md5_saved_data":
            computed_md5 = self.md5_saved_data()
            md5_ok = stored_md5 == computed_md5
        elif scheme == "md5_all_minus_tail":
            computed_md5 = self.md5_all_minus_tail()
            md5_ok = stored_md5 == computed_md5

        stored_size = self._read_u32(self.layout.file_size_offset) if len(self.data) >= self.layout.file_size_offset + 4 else 0
        file_size_ok = stored_size == len(self.data)

        c1_stored = self._read_u32(self.layout.crc_block1_offset) if len(self.data) >= self.layout.crc_block1_offset + 4 else 0
        c_data_stored = self._read_u32(self.layout.crc_data_offset) if len(self.data) >= self.layout.crc_data_offset + 4 else 0
        c2_stored = self._read_u32(self.layout.crc_block2_offset) if len(self.data) >= self.layout.crc_block2_offset + 4 else 0

        c1_cmp = self.compute_crc_block1()
        cdata_cmp = self.compute_crc_data()
        c2_cmp = self.compute_crc_block2()

        return IntegrityStatus(
            hash_scheme=scheme,
            md5_ok=md5_ok,
            crc_block1_ok=(c1_stored == c1_cmp),
            crc_data_ok=(c_data_stored == cdata_cmp),
            crc_block2_ok=(c2_stored == c2_cmp),
            file_size_ok=file_size_ok,
            stored_size=stored_size,
            actual_size=len(self.data),
            stored_md5=stored_md5,
            computed_md5=computed_md5,
            crc_details={
                "block1": (c1_stored, c1_cmp),
                "data": (c_data_stored, cdata_cmp),
                "block2": (c2_stored, c2_cmp),
            },
        )

    def fix_integrity(self, force_scheme: HashScheme = None) -> IntegrityStatus:
        # keep header length field in sync
        self._write_u32(self.layout.file_size_offset, len(self.data))

        scheme = force_scheme or self.hash_scheme or self.detect_hash_scheme() or "md5_saved_data"
        if scheme == "md5_all_minus_tail":
            digest = self.md5_all_minus_tail()
        else:
            digest = self.md5_saved_data()
            scheme = "md5_saved_data"
        self.data[-self.layout.md5_len:] = digest
        self.hash_scheme = scheme

        # CRC order is important: block1/data first, then block2 which covers header CRCs
        c1 = self.compute_crc_block1()
        c_data = self.compute_crc_data()
        self._write_u32(self.layout.crc_block1_offset, c1)
        self._write_u32(self.layout.crc_data_offset, c_data)
        c2 = self.compute_crc_block2()
        self._write_u32(self.layout.crc_block2_offset, c2)

        return self.validate_integrity()

    # --- junkman inventory slots (saved_data-relative array) ---

    def read_slot(self, abs_off: int) -> Tuple[int, int, bytes]:
        raw = bytes(self.data[abs_off:abs_off + self.SLOT_SIZE])
        if len(raw) != self.SLOT_SIZE:
            raise IndexError("Slot read out of bounds")
        type_id = raw[self.SLOT_TYPE_OFF]
        count = raw[self.SLOT_COUNT_OFF]
        return type_id, count, raw

    @staticmethod
    def is_empty_slot(raw12: bytes) -> bool:
        return len(raw12) >= 9 and raw12[0] == 0 and raw12[8] == 0

    @staticmethod
    def is_clean_empty(raw12: bytes) -> bool:
        return len(raw12) == 12 and all(b == 0 for b in raw12)

    @staticmethod
    def is_clean_filled(raw12: bytes) -> bool:
        if len(raw12) != 12:
            return False
        type_id = raw12[0]
        if not (1 <= type_id <= 64):
            return False
        if raw12[8] != 1:
            return False
        return all(b == 0 for b in raw12[1:8]) and all(b == 0 for b in raw12[9:12])

    def write_token_into_slot(self, abs_off: int, type_id: int, count: int = 1) -> None:
        if not (0 <= type_id <= 0xFF) or not (0 <= count <= 0xFF):
            raise ValueError("type_id/count must be u8")
        payload = bytearray(self.SLOT_SIZE)
        payload[self.SLOT_TYPE_OFF] = type_id
        payload[self.SLOT_COUNT_OFF] = count
        self.data[abs_off:abs_off + self.SLOT_SIZE] = payload

    def clear_slot(self, abs_off: int) -> None:
        self.data[abs_off:abs_off + self.SLOT_SIZE] = b"\x00" * self.SLOT_SIZE

    def locate_junkman_base(self, max_slots: int = 80) -> Optional[int]:
        """Return detected junkman base (saved_data-relative)."""
        return self.junkman.base_rel

    def locate_junkman_base_from_diff(
        self, save_a: str | Path, save_b: str | Path, max_slots: int = 80
    ) -> Tuple[Optional[int], List[Tuple[int, bytes, bytes]], Tuple[int, int, int]]:
        """
        Deterministic locator from two saves:
        Finds offsets where block A matches [type,0..0,1,0,0,0] (type 1..64) and B has 12x00.
        Returns (base_rel, hit_details[(off, block_a, block_b)], (score_total, covered_hits, clean_filled)).
        """
        a = SaveFile.load(save_a)
        b = SaveFile.load(save_b)
        a_start, a_end = a.saved_data_slice()
        b_start, b_end = b.saved_data_slice()
        if (a_end - a_start) != (b_end - b_start):
            raise ValueError("Saved data size mismatch between A and B")
        sa = a.saved_data()
        sb = b.saved_data()
        hits: List[Tuple[int, bytes, bytes]] = []
        for off in range(0, len(sa) - self.SLOT_SIZE + 1):
            block_a = sa[off: off + self.SLOT_SIZE]
            block_b = sb[off: off + self.SLOT_SIZE]
            if not self.is_clean_filled(block_a):
                continue
            if not self.is_clean_empty(block_b):
                continue
            hits.append((off, block_a, block_b))
        if not hits:
            return None, [], (0, 0)

        def score_base(base_rel: int) -> Optional[Tuple[int, int, int, int]]:
            if base_rel < 0:
                return None
            clean_empty = 0
            clean_filled = 0
            filled = 0
            covered_hits = 0
            start = a_start
            end = a_end
            for idx in range(min(max_slots, self.SLOT_MAX)):
                abs_off = start + base_rel + idx * self.SLOT_STRIDE
                if abs_off + self.SLOT_SIZE > end:
                    break
                raw = sa[abs_off - start: abs_off - start + self.SLOT_SIZE]
                if self.is_clean_empty(raw):
                    clean_empty += 1
                elif self.is_clean_filled(raw):
                    clean_filled += 1
                    filled += 1
                else:
                    break
            for h, _, _ in hits:
                if h < base_rel:
                    continue
                if (h - base_rel) % self.SLOT_STRIDE == 0:
                    covered_hits += 1
            if filled == 0:
                return None
            if covered_hits == 0:
                return None
            score_total = clean_empty + clean_filled
            return (score_total, covered_hits, clean_filled, -base_rel)

        best: Optional[Tuple[int, int, int, int]] = None
        best_base: Optional[int] = None
        best_counts: Tuple[int, int, int] = (0, 0, 0)
        for h, _, _ in hits:
            for k in range(0, 201):
                cand = h - k * self.SLOT_STRIDE
                sc = score_base(cand)
                if sc is None:
                    continue
                if best is None or sc > best:
                    best = sc
                    best_base = cand
                    best_counts = (sc[0], sc[1], sc[2])  # total, covered_hits, clean_filled
        if best_base is None:
            return None, hits, (0, 0, 0)
        self._junk_base_cache = best_base
        return best_base, hits, best_counts

    def read_slots(self, max_slots: int = 20) -> List[Tuple[int, int, int, int, int, bytes]]:
        """
        Return (index, rel_offset, abs_offset, type_id, count, raw12) for slots within saved_data.
        """
        slots: List[Tuple[int, int, int, int, int, bytes]] = []
        start, _ = self.saved_data_slice()
        max_slots = min(max_slots, self.junkman.slot_count)
        for slot in self.junkman.read_slots()[:max_slots]:
            rel = slot.abs_off - start
            slots.append((slot.index, rel, slot.abs_off, slot.type_id, slot.count, slot.raw))
        return slots

    # Junkman convenience wrappers for UI
    def get_junkman_counts(self) -> Dict[int, int]:
        return self.junkman.get_counts()

    def set_junkman_count(self, type_id: int, count: int, clamp_max: int = 63) -> None:
        self.junkman.apply_counts({type_id: count}, clamp_max=clamp_max)

    def set_junkman_counts(self, mapping: Dict[int, int], clamp_max: int = 63) -> None:
        self.junkman.apply_counts(mapping, clamp_max=clamp_max)

    # --- persistence ---

    def backup_path(self) -> Path:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.path.with_suffix(self.path.suffix + f".bak_{ts}")

    def write_backup(self) -> Path:
        bp = self.backup_path()
        bp.write_bytes(bytes(self.data))
        return bp

    def save(self, out_path: str | Path | None = None, make_backup: bool = True) -> Path:
        if make_backup:
            try:
                original_bytes = self.path.read_bytes()
                self.backup_path().write_bytes(original_bytes)
            except Exception:
                # fallback to backing up current buffer if reading original failed
                self.write_backup()

        self.fix_integrity()
        dest = Path(out_path) if out_path is not None else self.path
        dest.write_bytes(bytes(self.data))
        return dest

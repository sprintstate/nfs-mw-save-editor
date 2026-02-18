from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class Slot:
    index: int
    abs_off: int
    type_id: int
    count: int
    raw: bytes


class JunkmanInventory:
    """
    Slot-based Junkman inventory (1 token = 1 slot, Count always 1).
    Base and slot_count are auto-detected per save.
    """

    SAVED_DATA_START = 0x34  # fixed for PC v1.3 header
    SLOT_STRIDE = 0x0C
    SLOT_SIZE = 0x0C
    SCAN_START_REL = 0x5400
    SCAN_END_REL = 0x5B00

    def __init__(self, savefile: "SaveFile"):
        self.sf = savefile
        self.data = savefile.data
        self.base_rel: Optional[int] = None
        self.base_abs: Optional[int] = None
        self.slot_count: int = 0
        self._auto_detect()

    # ---- detection ----
    def _auto_detect(self) -> None:
        saved_start, saved_end = self.sf.saved_data_slice()
        saved = self.sf.saved_data()
        scan_start = min(self.SCAN_START_REL, max(0, len(saved) - self.SLOT_SIZE))
        scan_end = min(self.SCAN_END_REL, len(saved) - self.SLOT_SIZE)
        best: Tuple[int, Optional[int]] = (0, None)  # (prefix_len, base_rel)

        for rel in range(scan_start, max(scan_start, scan_end) + 1):
            prefix = 0
            while True:
                off = rel + prefix * self.SLOT_STRIDE
                if off + self.SLOT_SIZE > len(saved):
                    break
                block = saved[off : off + self.SLOT_SIZE]
                if not self._slot_like(block):
                    break
                prefix += 1
            if prefix > best[0]:
                best = (prefix, rel)

        if best[1] is None or best[0] == 0:
            raise ValueError("Failed to detect Junkman slot array")

        self.base_rel = best[1]
        self.slot_count = best[0]
        self.base_abs = saved_start + self.base_rel

    @staticmethod
    def _slot_like(raw: bytes) -> bool:
        if len(raw) != 12:
            return False
        if raw[8] not in (0, 1):
            return False
        if raw[1:8] != b"\x00" * 7:
            return False
        if raw[9:12] != b"\x00" * 3:
            return False
        return True

    # ---- core helpers ----
    def slot_abs(self, index: int) -> int:
        if self.base_abs is None or self.slot_count == 0:
            raise ValueError("Junkman base not detected")
        if index < 0 or index >= self.slot_count:
            raise IndexError(f"Slot index {index} out of bounds (0..{self.slot_count - 1})")
        return self.base_abs + index * self.SLOT_STRIDE

    @staticmethod
    def is_empty_slot(raw12: bytes) -> bool:
        return len(raw12) == 12 and raw12 == b"\x00" * 12

    # ---- IO ----
    def read_slot(self, index: int) -> Slot:
        abs_off = self.slot_abs(index)
        raw = bytes(self.data[abs_off : abs_off + self.SLOT_SIZE])
        if len(raw) != self.SLOT_SIZE:
            raise IndexError("Slot read out of bounds")
        type_id = raw[0]
        count = raw[8]
        return Slot(index=index, abs_off=abs_off, type_id=type_id, count=count, raw=raw)

    def read_slots(self) -> List[Slot]:
        return [self.read_slot(i) for i in range(self.slot_count)]

    def _write_full_slot(self, abs_off: int, type_id: int) -> None:
        payload = bytearray(self.SLOT_SIZE)
        payload[0] = type_id & 0xFF
        payload[8] = 1  # Count always 1 for filled slot
        self.data[abs_off : abs_off + self.SLOT_SIZE] = payload

    def _clear_slot(self, abs_off: int) -> None:
        self.data[abs_off : abs_off + self.SLOT_SIZE] = b"\x00" * self.SLOT_SIZE

    # ---- model operations ----
    def get_counts(self) -> Dict[int, int]:
        counts: Dict[int, int] = {}
        for slot in self.read_slots():
            # +0x08 is an "unused" state flag (1 = available marker).
            if slot.type_id == 0 or slot.count != 1:
                continue
            counts[slot.type_id] = counts.get(slot.type_id, 0) + 1
        return counts

    def free_slots(self) -> int:
        return sum(1 for s in self.read_slots() if self.is_empty_slot(s.raw))

    def apply_counts(self, desired: Dict[int, int], clamp_max: int = 63) -> None:
        """
        Apply counts transactionally using one-slot-per-token.
        - Preserve unknown IDs (from current save) not present in desired.
        - Ensure total tokens fit in slot_count.
        - Clear all slots, then rewrite sequentially.
        """
        have = self.get_counts()
        # preserve unspecified
        want_full = dict(have)
        for k, v in desired.items():
            want_full[int(k)] = int(v)
        # clamp to allowed range
        for k in list(want_full.keys()):
            want_full[k] = max(0, min(want_full[k], clamp_max))

        needed = sum(v for v in want_full.values() if v > 0)
        if needed > self.slot_count:
            raise ValueError(f"Need {needed} slots, have {self.slot_count}")

        # clear all slots
        for s in self.read_slots():
            self._clear_slot(s.abs_off)

        # write tokens sequentially
        idx = 0
        for tid in sorted(want_full.keys()):
            cnt = want_full[tid]
            for _ in range(cnt):
                if idx >= self.slot_count:
                    raise ValueError("Internal error: slot overflow")
                self._write_full_slot(self.slot_abs(idx), tid)
                idx += 1

    def clear_all(self) -> None:
        for s in self.read_slots():
            self._clear_slot(s.abs_off)

from __future__ import annotations
import struct
from typing import List

def find_u32_le(data: bytes | bytearray, value: int) -> List[int]:
    pat = struct.pack("<I", value & 0xFFFFFFFF)
    res: List[int] = []
    start = 0
    while True:
        i = data.find(pat, start)
        if i == -1:
            break
        res.append(i)
        start = i + 1
    return res

def read_u32_le(data: bytes | bytearray, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]

def write_u32_le(data: bytearray, offset: int, value: int) -> None:
    struct.pack_into("<I", data, offset, value & 0xFFFFFFFF)

def read_u8(data: bytes | bytearray, offset: int) -> int:
    return data[offset]

def write_u8(data: bytearray, offset: int, value: int) -> None:
    data[offset] = value & 0xFF

def mask_set_bit(mask: int, bit_index: int, enabled: bool) -> int:
    if enabled:
        return mask | (1 << bit_index)
    return mask & ~(1 << bit_index)

from __future__ import annotations

from typing import List


def _ea_crc32_table() -> List[int]:
    """Build the EA big-endian CRC32 lookup table (poly 0x04C11DB7)."""
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


_EA_CRC32_TABLE = _ea_crc32_table()


def ea_crc32(data: bytes) -> int:
    """
    EA-style CRC32 used by NFS MW save headers.
    Seeds from the first 4 bytes (big-endian), bitwise-not,
    then processes remaining bytes with the lookup table.
    """
    if len(data) < 4:
        return 0
    b0, b1, b2, b3 = data[0], data[1], data[2], data[3]
    crc = ((b0 << 24) | (b1 << 16) | (b2 << 8) | b3) & 0xFFFFFFFF
    crc = (~crc) & 0xFFFFFFFF
    for byte in data[4:]:
        idx = (crc >> 24) & 0xFF
        crc = ((((crc << 8) & 0xFFFFFFFF) | byte) ^ _EA_CRC32_TABLE[idx]) & 0xFFFFFFFF
    return (~crc) & 0xFFFFFFFF

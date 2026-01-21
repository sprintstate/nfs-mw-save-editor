from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import struct

@dataclass(frozen=True)
class ByteDiff:
    offset: int
    a: int
    b: int

def diff_bytes(a: bytes, b: bytes, limit: Optional[int] = 50000) -> List[ByteDiff]:
    n = min(len(a), len(b))
    out: List[ByteDiff] = []
    for i in range(n):
        if a[i] != b[i]:
            out.append(ByteDiff(i, a[i], b[i]))
            if limit is not None and len(out) >= limit:
                break
    # include tail length mismatch as synthetic diffs
    if limit is None or len(out) < limit:
        if len(a) != len(b):
            longer = a if len(a) > len(b) else b
            base = n
            for j in range(base, len(longer)):
                out.append(ByteDiff(j, a[j] if j < len(a) else -1, b[j] if j < len(b) else -1))
                if limit is not None and len(out) >= limit:
                    break
    return out

@dataclass(frozen=True)
class U32Diff:
    offset: int
    a: int
    b: int

def diff_u32_aligned(a: bytes, b: bytes, start: int = 0, end: Optional[int] = None, limit: Optional[int] = 20000) -> List[U32Diff]:
    n = min(len(a), len(b))
    if end is None or end > n:
        end = n
    out: List[U32Diff] = []
    i = start - (start % 4)
    while i + 4 <= end:
        va = struct.unpack_from("<I", a, i)[0]
        vb = struct.unpack_from("<I", b, i)[0]
        if va != vb:
            out.append(U32Diff(i, va, vb))
            if limit is not None and len(out) >= limit:
                break
        i += 4
    return out

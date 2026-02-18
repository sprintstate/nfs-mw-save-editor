from __future__ import annotations

import sys
from pathlib import Path


def resource_path(*parts: str) -> Path:
    candidates: list[Path] = []

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass))

    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        candidates.append(exe_dir)
        candidates.append(exe_dir / "_internal")

    module_dir = Path(__file__).resolve().parent
    candidates.append(module_dir)

    seen: set[Path] = set()
    unique_candidates: list[Path] = []
    for base in candidates:
        if base not in seen:
            seen.add(base)
            unique_candidates.append(base)

    for base in unique_candidates:
        candidate = base.joinpath(*parts)
        if candidate.exists():
            return candidate

    return unique_candidates[0].joinpath(*parts)


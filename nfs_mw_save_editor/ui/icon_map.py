"""Centralized mapping from token/nav IDs to icon file paths."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from resources import resource_path

_ICONS_ROOT = resource_path("assets", "icons")


# -- Token ID -> icon file (relative to _ICONS_ROOT) --
TOKEN_ICONS: Dict[int, str] = {
    1:  "perf/perf_brakes.png",
    2:  "perf/perf_engine.png",
    3:  "perf/perf_nos.png",
    4:  "perf/perf_turbo.png",
    5:  "perf/perf_suspension.png",
    6:  "perf/perf_tires.png",
    7:  "perf/perf_transmission.png",
    8:  "vis/vis_body.png",
    9:  "vis/vis_hood.png",
    10: "vis/vis_spoiler.png",
    11: "vis/vis_rims.png",
    12: "vis/vis_roof.png",
    13: "vis/vis_gauge.png",
    14: "vis/vis_vinyl.png",
    15: "vis/vis_decal.png",
    16: "vis/vis_spray.png",
    17: "pol/pol_jail.png",
    18: "pol/pol_money.png",
    19: "pol/pol_badge.png",
    20: "pol/pol_impound_strike.png",
    21: "pol/pol_impound_release.png",
    22: "nav/unknown.png",
}


# -- Navigation page -> icon file (relative to _ICONS_ROOT) --
NAV_ICONS: Dict[str, str] = {
    "Junkman":  "nav/nav_car.png",
    "Profile":  "nav/nav_profile.png",
    "Presets":  "nav/nav_save.png",
    "Settings": "nav/nav_settings.png",
    "About":    "nav/nav_info.png",
}


def token_icon_path(token_id: int) -> Optional[Path]:
    """Return token icon path; unknown IDs fallback to token 22 icon."""
    rel = TOKEN_ICONS.get(token_id, TOKEN_ICONS.get(22))
    if rel is None:
        return None
    p = _ICONS_ROOT / rel
    if p.exists():
        return p
    # Final fallback in case mapped file is missing.
    fallback = _ICONS_ROOT / TOKEN_ICONS.get(22, "")
    return fallback if fallback.exists() else None


def nav_icon_path(page_name: str) -> Optional[Path]:
    """Return absolute Path for a nav icon, or None if not mapped."""
    rel = NAV_ICONS.get(page_name)
    if rel is None:
        return None
    p = _ICONS_ROOT / rel
    return p if p.exists() else None


# -- Category -> representative icon --
CAT_ICONS: Dict[str, str] = {
    "Performance": "cat/cat_performance.png",
    "Visual":      "cat/cat_visual.png",
    "Police":      "cat/cat_police.png",
    "Unknown":     "cat/cat_unknown.png",
}


def cat_icon_path(category: str) -> Optional[Path]:
    """Return absolute Path for a category filter icon, or None."""
    rel = CAT_ICONS.get(category)
    if rel is None:
        return None
    p = _ICONS_ROOT / rel
    return p if p.exists() else None




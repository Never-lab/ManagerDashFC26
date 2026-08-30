"""Estimate in-game transfer value.

The career save has no reliable market-value field, so we estimate from:
1) SoFIFA/EA catalog value when the player ID matches and ratings are still close
2) otherwise an empirical curve fitted to catalog medians by OVR + age

The old (ovr/48)**7 curve was only sane near 80–85 OVR and overvalued
low/mid ratings by ~10x (e.g. 67 OVR teen → ~15M instead of ~2M).
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import date, timedelta

# Median catalog value (EUR) by overall, for age band 22–25 (anchor).
# Built once from scout/data catalog; fallback constants if catalog missing.
_MARKET_BY_OVR: dict[int, int] | None = None

# Age multipliers vs the 22–25 anchor (from catalog median ratios).
def _age_mult(age: int) -> float:
    if age <= 21:
        return 1.45
    if age <= 25:
        return 1.0
    if age <= 29:
        return 0.68
    if age <= 33:
        return 0.51
    return 0.22


def age_from_birth(birthdate: int | None, season: int) -> int | None:
    if not birthdate:
        return None
    born = date(1582, 10, 15) + timedelta(days=int(birthdate) - 1)
    # FC 26 career season 1 ≈ calendar 2025
    year = 2024 + int(season or 1)
    return max(15, min(45, year - born.year))


def build_market(catalog: dict[str, dict] | None) -> dict[int, int]:
    """Median value_eur by OVR for players aged 22–25 (stable anchor band)."""
    buckets: dict[int, list[int]] = defaultdict(list)
    for c in (catalog or {}).values():
        v = c.get("value")
        o = c.get("ovr")
        if not v or not o or int(v) < 25_000:
            continue
        age = int(c.get("age") or 24)
        if 22 <= age <= 25 and 45 <= int(o) <= 99:
            buckets[int(o)].append(int(v))
    out = {o: int(statistics.median(vs)) for o, vs in buckets.items() if len(vs) >= 3}
    return out


def set_market_from_catalog(catalog: dict[str, dict] | None) -> None:
    global _MARKET_BY_OVR
    _MARKET_BY_OVR = build_market(catalog)


def _fallback_anchor(ovr: int) -> int:
    """Closed-form stand-in when catalog medians are missing for this OVR."""
    # log(v) ≈ 7.68 + 0.009*o + 0.00134*o^2  (fit on catalog 22–25)
    import math

    o = max(45, min(99, ovr))
    return int(math.exp(7.677 + 0.00905 * o + 0.001341 * o * o))


def _anchor_value(ovr: int) -> int:
    market = _MARKET_BY_OVR or {}
    if ovr in market:
        return market[ovr]
    # interpolate between nearest known OVRs
    lower = max((k for k in market if k <= ovr), default=None)
    upper = min((k for k in market if k >= ovr), default=None)
    if lower is None and upper is None:
        return _fallback_anchor(ovr)
    if lower is None:
        return market[upper]
    if upper is None:
        return market[lower]
    if lower == upper:
        return market[lower]
    t = (ovr - lower) / (upper - lower)
    return int(market[lower] * (1 - t) + market[upper] * t)


def _curve(ovr: int, pot: int, age: int, gk: bool) -> int:
    ovr = max(40, min(99, int(ovr or 0)))
    pot = max(ovr, min(99, int(pot or ovr)))
    age = int(age or 24)
    leftover = min(12, pot - ovr)
    # Catalog medians already embed typical leftover (~3–5). Extra pot above 4
    # is a mild upside; below average pot is a mild discount.
    pot_m = 1.0 + 0.03 * (leftover - 4)
    pot_m = max(0.85, min(1.35, pot_m))
    gk_m = 0.78 if gk else 1.0
    raw = _anchor_value(ovr) * _age_mult(age) * pot_m * gk_m
    return max(25_000, int(raw))


def _scale_from_catalog(ovr, pot, age, cat: dict, gk: bool) -> int:
    """Nudge a known catalog price when the save ratings drifted."""
    v0 = int(cat["value"])
    o0 = max(1, int(cat["ovr"]))
    p0 = max(o0, int(cat.get("pot") or o0))
    a0 = int(cat.get("age") or age or 24)
    age = int(age or a0)
    ovr = int(ovr or o0)
    pot = max(ovr, int(pot or ovr))

    # Mild exponents — old **5.2 exploded after a few OVR points of growth.
    scale = (ovr / o0) ** 3.0
    scale *= (max(1, pot) / p0) ** 0.9
    scale *= (_age_mult(age) / max(0.15, _age_mult(a0)))
    scale = min(2.5, max(0.35, scale))
    return max(25_000, int(v0 * scale))


def current_value(ovr, pot, age, catalog: dict | None, gk: bool) -> int:
    """
    Prefer catalog ID when ratings are still near the dump (same player).
    Otherwise use the empirical market curve (needed for generated/youth IDs).
    """
    curve = _curve(int(ovr or 0), int(pot or 0), int(age or 24), bool(gk))
    if not catalog or not catalog.get("value") or not catalog.get("ovr"):
        return curve

    o0 = int(catalog["ovr"])
    a0 = int(catalog.get("age") or age or 24)
    # Wrong-ID / regenerated player guard: if OVR drifted hard, ignore catalog.
    if abs(int(ovr or o0) - o0) > 8 or abs(int(age or a0) - a0) > 4:
        return curve

    scaled = _scale_from_catalog(ovr, pot, age, catalog, bool(gk))
    # Blend toward curve so one bad catalog row cannot dominate.
    return max(25_000, int(0.7 * scaled + 0.3 * curve))


def fmt_eur(n: int | None) -> str:
    if n is None:
        return ""
    n = int(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}k"
    return str(n)

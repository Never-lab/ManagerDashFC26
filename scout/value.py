"""Estimate in-game transfer value.

Career saves have no market-value field. We estimate from catalog medians
by OVR (age 22–25 anchor), with young high-potential players priced off an
*effective OVR* (OVR + fraction of leftover potential) — closer to FC 26
in-game transfer values than a flat OVR lookup.
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from datetime import date, timedelta

# Median catalog value (EUR) by overall, for age band 22–25 (anchor).
_MARKET_BY_OVR: dict[int, int] | None = None


def _age_mult(age: int) -> float:
    """Decline-only multipliers. Youth upside is modeled via effective OVR."""
    if age <= 25:
        return 1.0
    if age <= 29:
        return 0.72
    if age <= 33:
        return 0.52
    return 0.22


def _youth_pot_weight(age: int) -> float:
    """How much of (POT − OVR) counts toward effective OVR (in-game style)."""
    if age <= 19:
        return 0.50
    if age <= 21:
        return 0.42
    if age <= 23:
        return 0.40
    if age <= 25:
        return 0.25
    if age <= 28:
        return 0.10
    return 0.0


def age_from_birth(birthdate: int | None, season: int) -> int | None:
    if not birthdate:
        return None
    born = date(1582, 10, 15) + timedelta(days=int(birthdate) - 1)
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
    return {o: int(statistics.median(vs)) for o, vs in buckets.items() if len(vs) >= 3}


def set_market_from_catalog(catalog: dict[str, dict] | None) -> None:
    global _MARKET_BY_OVR
    _MARKET_BY_OVR = build_market(catalog)


def _fallback_anchor(ovr: int) -> int:
    o = max(45, min(99, ovr))
    return int(math.exp(7.677 + 0.00905 * o + 0.001341 * o * o))


def _anchor_value(ovr: float) -> int:
    """Lookup / interpolate catalog median for (possibly fractional) OVR."""
    market = _MARKET_BY_OVR or {}
    if not market:
        return _fallback_anchor(int(round(ovr)))

    lo = int(math.floor(ovr))
    hi = int(math.ceil(ovr))
    lo = max(45, min(99, lo))
    hi = max(45, min(99, hi))

    def exact(o: int) -> int | None:
        if o in market:
            return market[o]
        lower = max((k for k in market if k <= o), default=None)
        upper = min((k for k in market if k >= o), default=None)
        if lower is None and upper is None:
            return None
        if lower is None:
            return market[upper]
        if upper is None:
            return market[lower]
        if lower == upper:
            return market[lower]
        t = (o - lower) / (upper - lower)
        return int(market[lower] * (1 - t) + market[upper] * t)

    a = exact(lo)
    b = exact(hi)
    if a is None and b is None:
        return _fallback_anchor(lo)
    if a is None:
        return b
    if b is None or lo == hi:
        return a
    t = ovr - lo
    return int(a * (1 - t) + b * t)


def _curve(ovr: int, pot: int, age: int, gk: bool) -> int:
    ovr = max(40, min(99, int(ovr or 0)))
    pot = max(ovr, min(99, int(pot or ovr)))
    age = int(age or 24)
    leftover = min(15, pot - ovr)
    # In-game prices young high-pot players closer to a higher OVR tier.
    eff = min(99.0, ovr + leftover * _youth_pot_weight(age))
    raw = _anchor_value(eff) * _age_mult(age) * (0.78 if gk else 1.0)
    return max(25_000, int(raw))


def _scale_from_catalog(ovr, pot, age, cat: dict) -> int:
    """Nudge a known catalog price when save ratings only drifted slightly."""
    v0 = int(cat["value"])
    o0 = max(1, int(cat["ovr"]))
    p0 = max(o0, int(cat.get("pot") or o0))
    a0 = int(cat.get("age") or age or 24)
    age = int(age or a0)
    ovr = int(ovr or o0)
    pot = max(ovr, int(pot or ovr))

    # Compare effective-OVR estimates so pot growth is not ignored.
    v_now = _curve(ovr, pot, age, False)
    v_then = _curve(o0, p0, a0, False)
    if v_then <= 0:
        return max(25_000, v0)
    scale = v_now / v_then
    scale = min(3.0, max(0.4, scale))
    return max(25_000, int(v0 * scale))


def current_value(ovr, pot, age, catalog: dict | None, gk: bool) -> int:
    """
    Use the empirical curve always. If catalog ID still matches ratings closely,
    blend with a scaled catalog price; if OVR drifted hard (career growth),
    ignore the stale dump row entirely.
    """
    curve = _curve(int(ovr or 0), int(pot or 0), int(age or 24), bool(gk))
    if not catalog or not catalog.get("value") or not catalog.get("ovr"):
        return curve

    o0 = int(catalog["ovr"])
    a0 = int(catalog.get("age") or age or 24)
    if abs(int(ovr or o0) - o0) > 6 or abs(int(age or a0) - a0) > 3:
        return curve

    scaled = _scale_from_catalog(ovr, pot, age, catalog)
    return max(25_000, int(0.55 * scaled + 0.45 * curve))


def fmt_eur(n: int | None) -> str:
    if n is None:
        return ""
    n = int(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}k"
    return str(n)

"""Estimate in-game transfer value. The career save has no market-value field."""

from __future__ import annotations

from datetime import date, timedelta


def age_from_birth(birthdate: int | None, season: int) -> int | None:
    if not birthdate:
        return None
    born = date(1582, 10, 15) + timedelta(days=int(birthdate) - 1)
    year = 2024 + int(season or 1)
    return max(15, min(45, year - born.year))


def _curve(ovr: int, pot: int, age: int, gk: bool) -> int:
    ovr = max(40, min(99, int(ovr or 0)))
    pot = max(ovr, min(99, int(pot or ovr)))
    age = int(age or 24)
    leftover = min(12, pot - ovr)
    if age <= 21:
        age_m = 1.2
    elif age <= 24:
        age_m = 1.1
    elif age <= 28:
        age_m = 1.0
    elif age <= 31:
        age_m = 0.72
    elif age <= 34:
        age_m = 0.45
    else:
        age_m = 0.22
    gk_m = 0.8 if gk else 1.0
    millions = (ovr / 48) ** 7
    return int(millions * 1_000_000 * age_m * gk_m * (1 + 0.028 * leftover))


def current_value(ovr, pot, age, catalog: dict | None, gk: bool) -> int:
    if catalog and catalog.get("value") and catalog.get("ovr"):
        v0 = int(catalog["value"])
        o0 = max(1, int(catalog["ovr"]))
        p0 = max(o0, int(catalog.get("pot") or o0))
        a0 = int(catalog.get("age") or age or 24)
        age = age or a0
        scale = (max(1, int(ovr or o0)) / o0) ** 5.2
        scale *= (max(1, int(pot or ovr or p0)) / p0) ** 1.15
        scale *= (max(16, 36 - (age or a0)) / max(16, 36 - a0)) ** 1.05
        scale = min(4.0, max(0.2, scale))
        return max(25000, int(v0 * scale))
    return max(25000, _curve(int(ovr or 0), int(pot or 0), int(age or 24), gk))


def fmt_eur(n: int | None) -> str:
    if n is None:
        return ""
    n = int(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}k"
    return str(n)

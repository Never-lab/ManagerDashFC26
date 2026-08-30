"""Fit ruoli (sigle italiane) da posizioni preferite + attributi."""

from __future__ import annotations

# Sigle italiane usate in tabella / filtri
POS = {
    0: "POR",
    2: "TD",   # RWB → terzino/esterno destro
    3: "TD",
    4: "DC",
    5: "DC",
    6: "DC",
    7: "TS",
    8: "TS",   # LWB
    9: "CDC",
    10: "CDC",
    11: "CDC",
    12: "ED",
    13: "CC",
    14: "CC",
    15: "CC",
    16: "ES",
    17: "COC",
    18: "COC",
    19: "COC",
    20: "ATT",
    21: "ATT",
    22: "ATT",
    23: "AD",
    24: "ATT",
    25: "ATT",
    26: "ATT",
    27: "AS",
}

ROLE_LABELS = {
    "POR": "Portiere",
    "TS": "Terzino sinistro",
    "DC": "Difensore centrale",
    "TD": "Terzino destro",
    "CDC": "Mediano (CDC)",
    "CC": "Centrocampista centrale",
    "COC": "Trequartista (COC)",
    "ES": "Esterno sinistro",
    "ED": "Esterno destro",
    "AS": "Ala sinistra",
    "AD": "Ala destra",
    "ATT": "Attaccante",
}

# Game preferredposition IDs that count as "natural" for a role
SLOT_POS = {
    "POR": {0},
    "TS": {7, 8},
    "DC": {4, 5, 6},
    "TD": {2, 3},
    "CDC": {9, 10, 11},
    "CC": {13, 14, 15, 9, 10, 11},
    "COC": {17, 18, 19},
    "ES": {16, 8},
    "ED": {12, 2},
    "AS": {16, 22, 27},
    "AD": {12, 20, 23},
    "ATT": {20, 21, 24, 25, 26},
}

SLOT_ATTRS = {
    "POR": ("gkdiving", "gkhandling", "gkreflexes", "gkpositioning", "reactions"),
    "TS": ("acceleration", "sprintspeed", "stamina", "defensiveawareness", "standingtackle", "crossing"),
    "TD": ("acceleration", "sprintspeed", "stamina", "defensiveawareness", "standingtackle", "crossing"),
    "DC": ("defensiveawareness", "standingtackle", "slidingtackle", "headingaccuracy", "strength", "interceptions"),
    "CDC": ("shortpassing", "longpassing", "interceptions", "defensiveawareness", "stamina", "standingtackle"),
    "CC": ("shortpassing", "longpassing", "vision", "stamina", "ballcontrol", "interceptions"),
    "COC": ("shortpassing", "vision", "dribbling", "ballcontrol", "finishing", "longpassing"),
    "ES": ("acceleration", "sprintspeed", "crossing", "dribbling", "stamina", "ballcontrol"),
    "ED": ("acceleration", "sprintspeed", "crossing", "dribbling", "stamina", "ballcontrol"),
    "AS": ("acceleration", "sprintspeed", "dribbling", "crossing", "ballcontrol", "finishing"),
    "AD": ("acceleration", "sprintspeed", "dribbling", "crossing", "ballcontrol", "finishing"),
    "ATT": ("finishing", "positioning", "shotpower", "headingaccuracy", "acceleration", "sprintspeed"),
}

SLOTS = ("POR", "TS", "DC", "TD", "CDC", "CC", "COC", "ES", "ED", "AS", "AD", "ATT")

FORMATIONS = {
    "4-3-3": ("POR", "TS", "DC", "TD", "CC", "AS", "ATT", "AD"),
    "4-4-2": ("POR", "TS", "DC", "TD", "ES", "CC", "ED", "ATT"),
    "4-2-3-1": ("POR", "TS", "DC", "TD", "CDC", "COC", "AS", "ATT", "AD"),
}


def preferred_positions(player: dict) -> list[int]:
    out = []
    for i in range(1, 8):
        v = player.get(f"preferredposition{i}")
        if v is None or v < 0:
            continue
        out.append(int(v))
    return out


def preferred_roles(player: dict) -> list[str]:
    """Unique Italian roles from preferred positions, primary first."""
    seen: list[str] = []
    for pid in preferred_positions(player):
        role = POS.get(pid)
        if role and role not in seen:
            seen.append(role)
    return seen


def _mean(player: dict, fields: tuple[str, ...]) -> float:
    vals = []
    for f in fields:
        v = player.get(f)
        if isinstance(v, (int, float)):
            vals.append(float(v))
    return sum(vals) / len(vals) if vals else 0.0


def slot_fit(player: dict, slot: str) -> int:
    ovr = float(player.get("overallrating") or 0)
    positions = preferred_positions(player)
    allowed = SLOT_POS[slot]
    if positions and positions[0] in allowed:
        pos_w = 1.0
    elif any(p in allowed for p in positions):
        pos_w = 0.72
    else:
        pos_w = 0.22
    attrs = _mean(player, SLOT_ATTRS[slot])
    return int(round(0.45 * ovr * pos_w + 0.55 * attrs * pos_w))


def all_fits(player: dict) -> dict[str, int]:
    return {s: slot_fit(player, s) for s in SLOTS}


def best_slot(player: dict, formation: str = "4-3-3") -> str:
    roles = preferred_roles(player)
    if roles:
        return roles[0]
    slots = FORMATIONS.get(formation, FORMATIONS["4-3-3"])
    fits = {s: slot_fit(player, s) for s in slots}
    return max(fits, key=fits.get)


def is_natural(player: dict, slot: str, primary_only: bool = False) -> bool:
    """True if preferred positions include this role."""
    positions = preferred_positions(player)
    allowed = SLOT_POS.get(slot, set())
    if not positions or not allowed:
        return False
    if primary_only:
        return positions[0] in allowed
    return any(p in allowed for p in positions)

"""4-3-3 role fit from preferred positions + key attributes (0-99 scale)."""

from __future__ import annotations

POS = {
    0: "GK",
    2: "RWB",
    3: "RB",
    4: "RCB",
    5: "CB",
    6: "LCB",
    7: "LB",
    8: "LWB",
    9: "RDM",
    10: "CDM",
    11: "LDM",
    12: "RM",
    13: "RCM",
    14: "CM",
    15: "LCM",
    16: "LM",
    17: "RAM",
    18: "CAM",
    19: "LAM",
    20: "RF",
    21: "CF",
    22: "LF",
    23: "RW",
    24: "RS",
    25: "ST",
    26: "LS",
    27: "LW",
}

SLOT_POS = {
    "GK": {0},
    "LB": {7, 8},
    "CB": {4, 5, 6},
    "RB": {2, 3},
    "CM": {9, 10, 11, 13, 14, 15, 17, 18, 19},
    "LW": {16, 22, 27},
    "ST": {20, 21, 24, 25, 26},
    "RW": {12, 20, 23},
}

SLOT_ATTRS = {
    "GK": ("gkdiving", "gkhandling", "gkreflexes", "gkpositioning", "reactions"),
    "LB": ("acceleration", "sprintspeed", "stamina", "defensiveawareness", "standingtackle", "crossing"),
    "RB": ("acceleration", "sprintspeed", "stamina", "defensiveawareness", "standingtackle", "crossing"),
    "CB": ("defensiveawareness", "standingtackle", "slidingtackle", "headingaccuracy", "strength", "interceptions"),
    "CM": ("shortpassing", "longpassing", "vision", "stamina", "ballcontrol", "interceptions"),
    "LW": ("acceleration", "sprintspeed", "dribbling", "crossing", "ballcontrol", "finishing"),
    "RW": ("acceleration", "sprintspeed", "dribbling", "crossing", "ballcontrol", "finishing"),
    "ST": ("finishing", "positioning", "shotpower", "headingaccuracy", "acceleration", "sprintspeed"),
}

SLOTS = ("GK", "LB", "CB", "RB", "CM", "LW", "ST", "RW")


def preferred_positions(player: dict) -> list[int]:
    out = []
    for i in range(1, 8):
        v = player.get(f"preferredposition{i}")
        if v is None or v < 0:
            continue
        out.append(int(v))
    return out


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


def best_slot(player: dict) -> str:
    fits = all_fits(player)
    return max(fits, key=fits.get)

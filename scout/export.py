"""Dump career scout payload as JSON on stdout. Logs go to stderr."""

from __future__ import annotations

import json
import sys

from scout.build import apply_growth, rows_from_world
from scout.career import latest_career_save, open_career
from scout.names import load_catalog, load_ea_names
from scout.score import FORMATIONS, ROLE_LABELS, SLOTS
from scout.snapshot import previous_mine, save_snapshot


def build_payload(formation: str = "4-3-3") -> dict:
    if formation not in FORMATIONS:
        formation = "4-3-3"
    save = latest_career_save()
    print(f"Save: {save}", file=sys.stderr)
    ea = load_ea_names()
    catalog = load_catalog()
    print(f"Names: {len(ea)}  catalog: {len(catalog)}", file=sys.stderr)
    path, career, world = open_career(save)
    players, meta = rows_from_world(career, world, ea, catalog)
    sid = save_snapshot(meta, players, save.name)
    apply_growth(players, previous_mine(meta["club"], sid))
    meta["formation"] = formation
    meta["save"] = save.name
    meta["path"] = str(path)
    named = sum(1 for p in players if p.get("named"))
    print(
        f"Players: {len(players)} named={named} club={meta['club']} snapshot={sid}",
        file=sys.stderr,
    )
    return {
        "meta": meta,
        "players": players,
        "slots": list(FORMATIONS[formation]),
        "all_roles": list(SLOTS),
        "role_labels": dict(ROLE_LABELS),
        "formations": {k: list(v) for k, v in FORMATIONS.items()},
        "snapshot_id": sid,
    }


def main() -> None:
    formation = sys.argv[1] if len(sys.argv) > 1 else "4-3-3"
    payload = build_payload(formation)
    # Windows consoles are often cp1252; write UTF-8 bytes to stdout buffer.
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    sys.stdout.buffer.write(raw)


if __name__ == "__main__":
    main()

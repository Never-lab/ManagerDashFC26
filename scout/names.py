"""playerid -> display name. Local cache from SoFIFA dump (same IDs as the save)."""

from __future__ import annotations

import csv
import json
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
CACHE = DATA / "ea_names.json"
CSV_URL = "https://raw.githubusercontent.com/ismailoksuz/EAFC26-DataHub/main/data/players.csv"
CSV_PATH = DATA / "players.csv"


def _from_csv(path: Path) -> tuple[dict[str, str], dict[str, dict]]:
    names: dict[str, str] = {}
    catalog: dict[str, dict] = {}
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = (row.get("player_id") or "").strip()
            if not pid:
                continue
            names[pid] = (row.get("short_name") or row.get("long_name") or pid).strip()
            def _i(key):
                raw = (row.get(key) or "").strip()
                if not raw:
                    return None
                try:
                    return int(float(raw))
                except ValueError:
                    return None
            catalog[pid] = {
                "value": _i("value_eur"),
                "wage": _i("wage_eur"),
                "ovr": _i("overall"),
                "pot": _i("potential"),
                "age": _i("age"),
            }
    return names, catalog


def download_names(dest: Path = CACHE) -> dict[str, str]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not CSV_PATH.exists():
        urllib.request.urlretrieve(CSV_URL, CSV_PATH)
    names, catalog = _from_csv(CSV_PATH)
    dest.write_text(json.dumps(names, ensure_ascii=False), encoding="utf-8")
    (DATA / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
    return names


def load_catalog() -> dict[str, dict]:
    p = DATA / "catalog.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    if not CSV_PATH.exists():
        download_names()
    else:
        _, catalog = _from_csv(CSV_PATH)
        p.write_text(json.dumps(catalog), encoding="utf-8")
        return catalog
    return json.loads((DATA / "catalog.json").read_text(encoding="utf-8"))


def load_ea_names(dest: Path = CACHE) -> dict[str, str]:
    if dest.exists():
        return json.loads(dest.read_text(encoding="utf-8"))
    return download_names(dest)

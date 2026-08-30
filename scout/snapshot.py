"""SQLite snapshots of each scout run (read-only vs the game save)."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB = Path(__file__).resolve().parent / "data" / "scout.db"


def connect(path: Path = DB) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            save_name TEXT,
            club TEXT,
            season INTEGER
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS snapshot_players (
            snapshot_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            name TEXT,
            ovr INTEGER,
            pot INTEGER,
            value INTEGER,
            wage INTEGER,
            pos TEXT,
            club TEXT,
            mine INTEGER,
            PRIMARY KEY (snapshot_id, player_id)
        )
        """
    )
    return con


def save_snapshot(meta: dict, players: list[dict], save_name: str, path: Path = DB) -> int:
    con = connect(path)
    cur = con.execute(
        "INSERT INTO snapshots (created_at, save_name, club, season) VALUES (?,?,?,?)",
        (
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
            save_name,
            meta.get("club"),
            meta.get("season"),
        ),
    )
    sid = int(cur.lastrowid)
    con.executemany(
        """
        INSERT INTO snapshot_players
        (snapshot_id, player_id, name, ovr, pot, value, wage, pos, club, mine)
        VALUES (?,?,?,?,?,?,?,?,?,?)
        """,
        [
            (
                sid,
                p["id"],
                p.get("name"),
                p.get("ovr"),
                p.get("pot"),
                p.get("value"),
                p.get("wage"),
                p.get("pos"),
                p.get("club"),
                1 if p.get("mine") else 0,
            )
            for p in players
        ],
    )
    con.commit()
    con.close()
    return sid


def previous_mine(club: str, current_id: int, path: Path = DB) -> dict[int, dict]:
    con = connect(path)
    row = con.execute(
        """
        SELECT id FROM snapshots
        WHERE club = ? AND id < ?
        ORDER BY id DESC LIMIT 1
        """,
        (club, current_id),
    ).fetchone()
    if not row:
        con.close()
        return {}
    prev_id = row["id"]
    rows = con.execute(
        """
        SELECT player_id, ovr, pot, value, wage
        FROM snapshot_players
        WHERE snapshot_id = ? AND mine = 1
        """,
        (prev_id,),
    ).fetchall()
    con.close()
    return {
        int(r["player_id"]): {
            "ovr": r["ovr"],
            "pot": r["pot"],
            "value": r["value"],
            "wage": r["wage"],
        }
        for r in rows
    }

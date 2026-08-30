"""Read-only FC 26 career save (FBCHUNKS / T3DB). Never writes the save."""

from __future__ import annotations

import os
import struct
from pathlib import Path

from fc26_mcp.fifa_squad import DB_HEADER, SquadFile, load_meta

SETTINGS = Path(os.environ.get("LOCALAPPDATA", "")) / "EA SPORTS FC 26" / "settings"


class DbSlice(SquadFile):
    """Same table parser as SquadFile, but bound to the Nth T3DB in the file."""

    def __init__(self, path: Path, meta_path: Path, raw: bytearray, db_index: int):
        self.path = Path(path)
        self.meta_path = Path(meta_path)
        self.table_names, self.field_names, self.field_range, self.field_depth, self.field_type = load_meta(meta_path)
        self.raw = raw
        found: list[int] = []
        idx = 0
        while True:
            i = raw.find(DB_HEADER, idx)
            if i < 0:
                break
            found.append(i)
            idx = i + 4
        if db_index >= len(found):
            raise ValueError(f"DB {db_index} missing (found {len(found)})")
        self.db_offset = found[db_index]
        self.db_size = struct.unpack_from("<I", self.raw, self.db_offset + 8)[0]
        self.db_data = self.raw[self.db_offset : self.db_offset + self.db_size]
        self.tables_meta = self._read_table_index()
        self._records = {}
        self._table_fields = {}
        self._dirty = set()

    def save(self, output_path=None):
        raise RuntimeError("career scout is read-only")


def latest_career_save(settings: Path = SETTINGS) -> Path:
    files = sorted(settings.glob("CmMgrC*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise FileNotFoundError(f"No CmMgrC save in {settings}")
    return files[0]


def meta_path() -> Path:
    import fc26_mcp

    return Path(fc26_mcp.__file__).parent / "data" / "fifa_ng_db-meta-fc26.xml"


def open_career(path: Path | None = None) -> tuple[Path, DbSlice, DbSlice]:
    path = path or latest_career_save()
    raw = bytearray(path.read_bytes())
    meta = meta_path()
    career = DbSlice(path, meta, raw, 0)
    world = DbSlice(path, meta, raw, 1)
    return path, career, world

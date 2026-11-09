"""SQLite (mode WAL) partagée entre le worker et l'app Streamlit."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from periods import half_day_of, now_utc

DEFAULT_PATH = Path(os.environ.get("DEMO_DB", Path(__file__).resolve().parent / "data" / "demo.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS avis (
  id             INTEGER PRIMARY KEY,
  created_at     TEXT NOT NULL,
  event_ts       TEXT NOT NULL,
  demi_journee   TEXT NOT NULL,
  transcript     TEXT NOT NULL,
  langue         TEXT,
  duree_s        REAL,
  borne_id       TEXT NOT NULL,
  source         TEXT NOT NULL CHECK (source IN ('borne','app')),
  lat            REAL NOT NULL,
  lon            REAL NOT NULL,
  profil         TEXT, origine TEXT, groupe TEXT, mode_venue TEXT,
  affluence      TEXT, revenir TEXT,
  note           REAL CHECK (note BETWEEN 1 AND 5),
  classif_status TEXT NOT NULL CHECK (classif_status IN ('pending','ok','error')),
  classif_error  TEXT,
  jev_model      TEXT,
  jev_raw        TEXT,
  is_init        INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_avis_dj ON avis(demi_journee);

CREATE TABLE IF NOT EXISTS live_state (
  id             INTEGER PRIMARY KEY CHECK (id = 1),
  status         TEXT NOT NULL DEFAULT 'offline',
  committed_text TEXT NOT NULL DEFAULT '',
  partial_text   TEXT NOT NULL DEFAULT '',
  langue         TEXT,
  borne_id       TEXT,
  source         TEXT,
  message        TEXT,
  heartbeat_at   TEXT,
  updated_at     TEXT
);
INSERT OR IGNORE INTO live_state (id) VALUES (1);

CREATE TABLE IF NOT EXISTS control (
  id                INTEGER PRIMARY KEY,
  cmd               TEXT NOT NULL CHECK (cmd IN ('start','stop','reclassify')),
  borne_id          TEXT,
  source            TEXT,
  event_ts_override TEXT,
  is_init           INTEGER NOT NULL DEFAULT 0,
  avis_id           INTEGER,
  created_at        TEXT NOT NULL,
  consumed          INTEGER NOT NULL DEFAULT 0
);
"""

CLASSIF_COLUMNS = ("profil", "origine", "groupe", "mode_venue", "affluence", "revenir", "note")


def connect(path: Path | str = DEFAULT_PATH) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.executescript(SCHEMA)
    return conn


@contextmanager
def tx(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


def _iso(ts: datetime) -> str:
    return ts.isoformat(timespec="seconds")


# --- avis -------------------------------------------------------------------

def insert_avis(conn: sqlite3.Connection, *, transcript: str, langue: str | None, duree_s: float,
                borne_id: str, source: str, lat: float, lon: float,
                event_ts: datetime | None = None, is_init: bool = False) -> int:
    created = now_utc()
    event = event_ts or created
    cur = conn.execute(
        """INSERT INTO avis (created_at, event_ts, demi_journee, transcript, langue, duree_s,
                             borne_id, source, lat, lon, classif_status, is_init)
           VALUES (?,?,?,?,?,?,?,?,?,?,'pending',?)""",
        (_iso(created), _iso(event), half_day_of(event).key, transcript, langue, duree_s,
         borne_id, source, lat, lon, int(is_init)),
    )
    return int(cur.lastrowid)


def set_classification(conn: sqlite3.Connection, avis_id: int, cols: dict[str, Any], raw: dict[str, Any], model: str) -> None:
    values = [cols.get(c) for c in CLASSIF_COLUMNS]
    conn.execute(
        f"""UPDATE avis SET {', '.join(f'{c} = ?' for c in CLASSIF_COLUMNS)},
               classif_status = 'ok', classif_error = NULL, jev_model = ?, jev_raw = ?
            WHERE id = ?""",
        (*values, model, json.dumps(raw, ensure_ascii=False), avis_id),
    )


def set_classification_error(conn: sqlite3.Connection, avis_id: int, error: str) -> None:
    conn.execute("UPDATE avis SET classif_status = 'error', classif_error = ? WHERE id = ?", (error[:500], avis_id))


def set_pending(conn: sqlite3.Connection, avis_id: int) -> None:
    conn.execute("UPDATE avis SET classif_status = 'pending', classif_error = NULL WHERE id = ?", (avis_id,))


def get_avis(conn: sqlite3.Connection, avis_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM avis WHERE id = ?", (avis_id,)).fetchone()


def latest_avis(conn: sqlite3.Connection, n: int = 10) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM avis ORDER BY id DESC LIMIT ?", (n,)).fetchall()


def avis_in_window(conn: sqlite3.Connection, demi_journee: str | None) -> list[sqlite3.Row]:
    """Avis d'une demi-journée (clé), ou de tout le passé si None."""
    if demi_journee is None:
        return conn.execute("SELECT * FROM avis ORDER BY event_ts").fetchall()
    return conn.execute("SELECT * FROM avis WHERE demi_journee = ? ORDER BY event_ts", (demi_journee,)).fetchall()


def half_days_with_data(conn: sqlite3.Connection) -> list[str]:
    return [r[0] for r in conn.execute("SELECT DISTINCT demi_journee FROM avis ORDER BY demi_journee")]


# --- live_state -------------------------------------------------------------

def get_live(conn: sqlite3.Connection) -> sqlite3.Row:
    return conn.execute("SELECT * FROM live_state WHERE id = 1").fetchone()


def set_live(conn: sqlite3.Connection, **fields: Any) -> None:
    fields["updated_at"] = _iso(now_utc())
    conn.execute(
        f"UPDATE live_state SET {', '.join(f'{k} = ?' for k in fields)} WHERE id = 1",
        tuple(fields.values()),
    )


def heartbeat(conn: sqlite3.Connection) -> None:
    conn.execute("UPDATE live_state SET heartbeat_at = ? WHERE id = 1", (_iso(now_utc()),))


# --- control ----------------------------------------------------------------

def push_command(conn: sqlite3.Connection, cmd: str, **fields: Any) -> int:
    fields = {"cmd": cmd, "created_at": _iso(now_utc()), **fields}
    cur = conn.execute(
        f"INSERT INTO control ({', '.join(fields)}) VALUES ({', '.join('?' * len(fields))})",
        tuple(fields.values()),
    )
    return int(cur.lastrowid)


def pop_commands(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    with tx(conn):
        rows = conn.execute("SELECT * FROM control WHERE consumed = 0 ORDER BY id").fetchall()
        if rows:
            conn.execute(f"UPDATE control SET consumed = 1 WHERE id IN ({','.join('?' * len(rows))})",
                         [r["id"] for r in rows])
    return rows

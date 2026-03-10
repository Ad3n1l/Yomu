"""
yomu · db.py
SQLite storage for watch history, download log, and watchlist.
Stored at ~/.yomu/yomu.db
"""

import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path.home() / ".yomu" / "yomu.db"


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _init(conn)
    return conn


def _init(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            source      TEXT NOT NULL,
            anime_id    TEXT NOT NULL,
            anime_title TEXT NOT NULL,
            episode     TEXT,
            watched_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS downloads (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            source        TEXT NOT NULL,
            anime_id      TEXT NOT NULL,
            anime_title   TEXT NOT NULL,
            episode       TEXT,
            quality       TEXT,
            audio         TEXT,
            sub_mode      TEXT,
            file_path     TEXT,
            downloaded_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS watchlist (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            source      TEXT NOT NULL,
            anime_id    TEXT NOT NULL,
            anime_title TEXT NOT NULL,
            added_at    TEXT NOT NULL,
            UNIQUE(source, anime_id)
        );
    """)
    conn.commit()


# ── History ───────────────────────────────────────────────────────────────────

def add_history(source, anime_id, anime_title, episode=None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO history (source,anime_id,anime_title,episode,watched_at) VALUES (?,?,?,?,?)",
            (source, anime_id, anime_title, episode, datetime.now().isoformat())
        )

def get_history(limit=50):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM history ORDER BY watched_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]

def clear_history():
    with get_conn() as conn:
        conn.execute("DELETE FROM history")


# ── Downloads ─────────────────────────────────────────────────────────────────

def add_download(source, anime_id, anime_title, episode, quality="", audio="", sub_mode="", file_path=""):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO downloads
               (source,anime_id,anime_title,episode,quality,audio,sub_mode,file_path,downloaded_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (source, anime_id, anime_title, episode, quality, audio, sub_mode, file_path,
             datetime.now().isoformat())
        )

def get_downloads(limit=50):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM downloads ORDER BY downloaded_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


# ── Watchlist ─────────────────────────────────────────────────────────────────

def add_watchlist(source, anime_id, anime_title):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO watchlist (source,anime_id,anime_title,added_at) VALUES (?,?,?,?)",
            (source, anime_id, anime_title, datetime.now().isoformat())
        )

def remove_watchlist(source, anime_id):
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM watchlist WHERE source=? AND anime_id=?", (source, anime_id)
        )

def get_watchlist():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM watchlist ORDER BY added_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]

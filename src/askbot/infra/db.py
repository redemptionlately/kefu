"""sqlite 会话持久化占位,后续替换 Redis/DB."""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path("data/askbot.db")


def init_db(path: Path = DB_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS sessions"
            "(key TEXT PRIMARY KEY, updated_at REAL, history TEXT)"
        )

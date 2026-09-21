"""sqlite 会话持久化:SessionStore 供 SessionManager 可选挂载."""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

DB_PATH = Path("data/askbot.db")


def init_db(path: Path = DB_PATH) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS sessions"
            "(key TEXT PRIMARY KEY, updated_at REAL, history TEXT)"
        )


class SessionStore:
    """极简 sqlite 存取,key=会话标识."""

    def __init__(self, path: Path = DB_PATH) -> None:
        self.path = Path(path)
        init_db(self.path)

    def save(self, key: str, history: list[dict], updated_at: float | None = None) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO sessions(key, updated_at, history) VALUES(?,?,?)",
                (key, updated_at or time.time(), json.dumps(history, ensure_ascii=False)),
            )

    def load(self, key: str) -> tuple[list[dict], float] | None:
        with sqlite3.connect(self.path) as conn:
            row = conn.execute(
                "SELECT history, updated_at FROM sessions WHERE key=?", (key,)
            ).fetchone()
        if not row:
            return None
        try:
            return json.loads(row[0]), float(row[1])
        except (json.JSONDecodeError, ValueError, TypeError):
            return None

    def prune(self, ttl_seconds: float) -> int:
        with sqlite3.connect(self.path) as conn:
            cur = conn.execute(
                "DELETE FROM sessions WHERE updated_at < ?",
                (time.time() - ttl_seconds,),
            )
            return cur.rowcount

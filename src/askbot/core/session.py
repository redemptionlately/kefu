"""会话管理:内存+TTL,key=platform:user/group."""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class Session:
    key: str
    history: list[dict] = field(default_factory=list)
    updated_at: float = field(default_factory=time.time)


class SessionManager:
    def __init__(self, ttl_seconds: int = 1800, max_history: int = 20) -> None:
        self.ttl = ttl_seconds
        self.max_history = max_history
        self._store: dict[str, Session] = {}

    @staticmethod
    def key(platform: str, user_id: str, group_id: str | None) -> str:
        scope = group_id or user_id
        return f"{platform}:{scope}:{user_id}"

    def get(self, key: str) -> Session:
        s = self._store.get(key)
        now = time.time()
        if s and now - s.updated_at < self.ttl:
            return s
        s = Session(key=key)
        self._store[key] = s
        return s

    def append(self, key: str, role: str, content: str) -> None:
        s = self.get(key)
        s.history.append({"role": role, "content": content})
        s.history = s.history[-self.max_history :]
        s.updated_at = time.time()

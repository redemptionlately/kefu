"""会话管理:内存+TTL,可选挂载 store(sqlite)做持久化.

store 只需实现 save(key, history)/load(key) 两个方法(见 infra/db.py:SessionStore),
core 不直接 import infra,保持可测试.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Session:
    key: str
    history: list[dict] = field(default_factory=list)
    updated_at: float = field(default_factory=time.time)
    data: dict = field(default_factory=dict)  # playbook 状态等结构化数据


class SessionManager:
    def __init__(
        self, ttl_seconds: int = 1800, max_history: int = 20, store: Any = None
    ) -> None:
        self.ttl = ttl_seconds
        self.max_history = max_history
        self.store = store
        self._store: dict[str, Session] = {}

    @staticmethod
    def key(
        platform: str, user_id: str, group_id: str | None, thread_id: str | None = None
    ) -> str:
        if thread_id:  # 同客同品优先:不同商品互不串话
            return f"{platform}:{thread_id}:{user_id}"
        scope = group_id or user_id
        return f"{platform}:{scope}:{user_id}"

    def get(self, key: str) -> Session:
        s = self._store.get(key)
        now = time.time()
        if s and now - s.updated_at < self.ttl:
            return s
        history: list[dict] = []
        data: dict = {}
        if self.store is not None:
            loaded = self.store.load(key)
            if loaded and now - loaded[1] < self.ttl:
                history = loaded[0][-self.max_history :]
                data = loaded[2] if len(loaded) > 2 else {}
        s = Session(key=key, history=history, data=data)
        self._store[key] = s
        return s

    def append(self, key: str, role: str, content: str) -> None:
        s = self.get(key)
        s.history.append({"role": role, "content": content})
        s.history = s.history[-self.max_history :]
        s.updated_at = time.time()
        self.persist(key)

    def persist(self, key: str) -> None:
        """只落盘(供 playbook 改 data 后调用,不追加消息)."""
        s = self._store.get(key)
        if s is None:
            return
        if self.store is not None:
            self.store.save(key, s.history, s.updated_at, s.data)

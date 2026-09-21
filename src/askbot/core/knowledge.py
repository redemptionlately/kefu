"""本地 FAQ 知识库:JSON 文件加载 + 关键词最长命中."""
from __future__ import annotations

import json
from pathlib import Path


class KnowledgeBase:
    def __init__(self, faq: dict[str, str] | None = None) -> None:
        self.faq = faq or {}

    @classmethod
    def from_json(cls, path: str | Path) -> KnowledgeBase:
        p = Path(path)
        if not p.exists():
            return cls()
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return cls()
        if isinstance(data, dict):
            faq = {str(k): str(v) for k, v in data.items()}
        elif isinstance(data, list):
            faq = {
                str(i.get("q", "")): str(i.get("a", ""))
                for i in data
                if isinstance(i, dict) and i.get("q")
            }
        else:
            faq = {}
        return cls(faq)

    def search(self, query: str) -> str | None:
        best: str | None = None
        best_len = 0
        for kw, answer in self.faq.items():
            if kw and kw in query and len(kw) > best_len:
                best, best_len = answer, len(kw)
        return best

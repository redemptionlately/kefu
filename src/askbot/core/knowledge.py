"""本地 FAQ 知识库 stub,下一步接向量检索."""
from __future__ import annotations


class KnowledgeBase:
    def __init__(self, faq: dict[str, str] | None = None) -> None:
        self.faq = faq or {}

    def search(self, query: str) -> str | None:
        for kw, answer in self.faq.items():
            if kw in query:
                return answer
        return None

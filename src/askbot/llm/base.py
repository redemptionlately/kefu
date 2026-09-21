"""LLM 抽象."""
from __future__ import annotations

from typing import Protocol


class LLMClient(Protocol):
    async def chat(
        self, messages: list[dict], system: str = "", images: list[str] | None = None
    ) -> str: ...

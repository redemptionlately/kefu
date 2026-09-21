"""OpenAI兼容客户端:当前 echo stub,下一步接真实 httpx 调用."""
from __future__ import annotations

import httpx
from askbot.config import settings
from askbot.infra.logger import logger


class OpenAICompatClient:
    def __init__(self, base_url: str = "", api_key: str = "", model: str = "") -> None:
        self.base_url = (base_url or settings.llm_base_url).rstrip("/")
        self.api_key = api_key or settings.llm_api_key
        self.model = model or settings.llm_model

    async def chat(self, messages: list[dict], system: str = "") -> str:
        # stub:无 key 时直接回显,避免开发期报错
        if not self.api_key or self.api_key.startswith("sk-please"):
            last = messages[-1]["content"] if messages else ""
            return f"[stub:{self.model}] 收到:{last}"
        try:
            msgs = ([{"role": "system", "content": system}] if system else []) + messages
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"model": self.model, "messages": msgs},
                )
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]
        except Exception:
            logger.exception("LLM call failed")
            return "抱歉,服务暂时繁忙,请稍后再试。"

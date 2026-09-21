"""OpenAI兼容客户端:无 key 时 stub 回显,有 key 时真实调用+重试."""
from __future__ import annotations

import asyncio

import httpx
from askbot.config import settings
from askbot.infra.logger import logger


class OpenAICompatClient:
    def __init__(
        self,
        base_url: str = "",
        api_key: str = "",
        model: str = "",
        timeout: float = 30.0,
        retries: int = 2,
    ) -> None:
        self.base_url = (base_url or settings.llm_base_url).rstrip("/")
        self.api_key = api_key or settings.llm_api_key
        self.model = model or settings.llm_model
        self.timeout = timeout
        self.retries = retries

    def is_stub(self) -> bool:
        return not self.api_key or self.api_key.startswith("sk-please")

    async def chat(self, messages: list[dict], system: str = "") -> str:
        if self.is_stub():
            last = messages[-1]["content"] if messages else ""
            return f"[stub:{self.model}] 收到:{last}"
        msgs = ([{"role": "system", "content": system}] if system else []) + messages
        last_err: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as c:
                    r = await c.post(
                        f"{self.base_url}/chat/completions",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json={"model": self.model, "messages": msgs},
                    )
                    r.raise_for_status()
                    content = r.json()["choices"][0]["message"]["content"]
                    return str(content).strip()
            except Exception as e:
                last_err = e
                logger.warning("LLM 调用失败(第{}次): {}", attempt + 1, e)
                if attempt < self.retries:
                    await asyncio.sleep(1.0 * (attempt + 1))
        logger.exception("LLM 调用最终失败: {}", last_err)
        return "抱歉,服务暂时繁忙,请稍后再试。"

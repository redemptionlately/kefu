"""编排: session→护栏→router→knowledge→llm."""
from __future__ import annotations

from askbot.adapters.base import MessageEvent
from askbot.core import guardrails
from askbot.core.knowledge import KnowledgeBase
from askbot.core.router import route
from askbot.core.session import SessionManager
from askbot.llm.base import LLMClient

SYSTEM_PROMPT = "你是 AskBot 智能客服,回答简洁、礼貌,解决用户问题。"


class ReplyEngine:
    def __init__(
        self,
        sessions: SessionManager,
        llm: LLMClient,
        kb: KnowledgeBase | None = None,
        max_length: int = 800,
        rate_limit: int = 3,
    ) -> None:
        self.sessions = sessions
        self.llm = llm
        self.kb = kb or KnowledgeBase()
        self.max_length = max_length
        self.rate_limit = rate_limit

    async def handle(self, event: MessageEvent) -> str | None:
        key = SessionManager.key(event.platform, event.user_id, event.group_id)
        if event.group_id and guardrails.should_ignore_group(event.text, event.at_bot):
            return None
        if not guardrails.check_rate_limit(key, self.rate_limit):
            return "您发送得太快了,请稍后再试。"
        self.sessions.append(key, "user", event.text)

        r = route(event.text)
        if r.action in ("reply", "handoff"):
            reply = r.text
        else:
            hit = self.kb.search(event.text)
            if hit:
                reply = hit
            else:
                history = self.sessions.get(key).history
                reply = await self.llm.chat(history, system=SYSTEM_PROMPT)

        reply = guardrails.sanitize(reply, self.max_length)
        self.sessions.append(key, "assistant", reply)
        return reply

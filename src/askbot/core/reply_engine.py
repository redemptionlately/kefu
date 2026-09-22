"""编排: session→护栏→router→knowledge→llm."""
from __future__ import annotations

from askbot.adapters.base import MessageEvent
from askbot.core import guardrails
from askbot.core.knowledge import KnowledgeBase
from askbot.core.playbook import PlaybookEngine
from askbot.core.router import route
from askbot.core.session import SessionManager
from askbot.core.style import StyleCorpus, split_message
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
        group_only_on_at: bool = True,
        playbooks: PlaybookEngine | None = None,
        style: StyleCorpus | None = None,
    ) -> None:
        self.sessions = sessions
        self.llm = llm
        self.kb = kb or KnowledgeBase()
        self.max_length = max_length
        self.rate_limit = rate_limit
        self.group_only_on_at = group_only_on_at
        self.playbooks = playbooks
        self.style = style or StyleCorpus()

    def system_prompt(self) -> str:
        return self.style.apply_system(SYSTEM_PROMPT)

    @staticmethod
    def bubbles(reply: str) -> list[str]:
        return split_message(reply)

    async def handle(self, event: MessageEvent) -> str | None:
        key = SessionManager.key(event.platform, event.user_id, event.group_id, event.thread_id)
        if event.group_id and guardrails.should_ignore_group(
            event.text, event.at_bot, self.group_only_on_at
        ):
            return None
        if not guardrails.check_rate_limit(key, self.rate_limit):
            return "您发送得太快了,请稍后再试。"
        self.sessions.append(key, "user", event.text)

        r = route(event.text)
        if r.action == "handoff":
            reply = r.text
        else:
            session = self.sessions.get(key)
            pb_reply = None
            if self.playbooks is not None:
                pb_reply = await self.playbooks.handle(
                    event, session, self.llm, lambda: self.sessions.persist(key)
                )
            if pb_reply is not None:
                reply = pb_reply
            elif r.action == "reply":
                reply = r.text
            else:
                hit = self.kb.search(event.text)
                if hit:
                    reply = hit
                else:
                    history = session.history
                    reply = await self.llm.chat(
                        history,
                        system=self.system_prompt(),
                        images=event.images or None,
                    )

        reply = guardrails.sanitize(reply, self.max_length)
        self.sessions.append(key, "assistant", reply)
        return reply

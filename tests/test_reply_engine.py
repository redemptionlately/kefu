import asyncio

from askbot.adapters.base import MessageEvent
from askbot.core.reply_engine import ReplyEngine
from askbot.core.session import SessionManager


class FakeLLM:
    async def chat(
        self, messages: list[dict], system: str = "", images: list[str] | None = None
    ) -> str:
        return "fake-llm-reply"


def run(engine: ReplyEngine, **kw) -> str | None:
    event = MessageEvent(platform="qq", user_id=kw.pop("user", "u1"), text=kw.pop("text", "hi"), **kw)
    return asyncio.run(engine.handle(event))


def test_keyword_path():
    e = ReplyEngine(SessionManager(), FakeLLM())
    assert "智能客服" in run(e, text="你好,在吗")


def test_handoff_path():
    e = ReplyEngine(SessionManager(), FakeLLM())
    assert "人工" in run(e, text="转人工谢谢")


def test_llm_fallback_path():
    e = ReplyEngine(SessionManager(), FakeLLM())
    assert run(e, text="请解释一下量子纠缠xyz") == "fake-llm-reply"


def test_group_no_at_ignored():
    e = ReplyEngine(SessionManager(), FakeLLM())
    assert run(e, user="g1", text="大家好", group_id="99", at_bot=False) is None


def test_rate_limit_second_blocked():
    e = ReplyEngine(SessionManager(), FakeLLM(), rate_limit=1)
    assert run(e, user="rl-u9", text="第一句") is not None
    assert "太快" in run(e, user="rl-u9", text="第二句")

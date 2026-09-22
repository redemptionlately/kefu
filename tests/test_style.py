from askbot.core.reply_engine import ReplyEngine
from askbot.core.session import SessionManager
from askbot.core.style import HUMAN_RULES, StyleCorpus, split_message


class FakeLLM:
    def __init__(self):
        self.last_system = ""

    async def chat(self, messages, system="", images=None):
        self.last_system = system
        return "ok"


def test_corpus_loads_and_applies():
    c = StyleCorpus.from_dir("data/style")
    assert len(c.examples) >= 5
    sys = c.apply_system("BASE")
    assert "BASE" in sys and HUMAN_RULES[:10] in sys
    assert "改简历88起" in sys  # 学到真人话术


def test_engine_passes_style_to_llm():
    import asyncio

    e = ReplyEngine(SessionManager(), FakeLLM(), style=StyleCorpus.from_dir("data/style"))
    asyncio.run(e.handle(__import__("askbot.adapters.base", fromlist=["MessageEvent"]).MessageEvent(
        platform="qq", user_id="s1", text="讲个冷笑话xyz")))
    assert "改简历88起" in e.llm.last_system


def test_split_short_stays_one():
    assert split_message("你好呀") == ["你好呀"]


def test_split_long_into_bubbles():
    parts = split_message("第一句。第二句很长" + "x" * 200 + "。第三句。")
    assert 2 <= len(parts) <= 3
    assert all(len(p) <= 120 for p in parts)

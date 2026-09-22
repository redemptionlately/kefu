import asyncio

from askbot.adapters.base import MessageEvent
from askbot.adapters.xianyu import XianyuAdapter
from askbot.core.playbook import PlaybookEngine
from askbot.core.reply_engine import ReplyEngine
from askbot.core.session import SessionManager


class ScriptLLM:
    """按调用内容路由:提取类返回队列里的 JSON,初稿返回固定文本,其余回显."""

    def __init__(self, extracts: list[dict]):
        self.extracts = list(extracts)

    async def chat(self, messages: list[dict], system: str = "", images=None) -> str:
        last = messages[-1]["content"]
        if "只返回JSON" in last:
            import json

            return json.dumps(self.extracts.pop(0), ensure_ascii=False)
        if "初稿框架" in last:
            return "【初稿】姓名xx/学历xx/经历xx/目标xx"
        return "free-talk"


def ev(user="u1", text="", thread="u1:itemA", product="简历代写"):
    return MessageEvent(
        platform="xianyu", user_id=user, text=text, thread_id=thread, product=product
    )


def run(engine, event):
    return asyncio.run(engine.handle(event))


def make_engine(slots: list[dict]):
    pb = PlaybookEngine.from_dir("data/playbooks")
    assert "resume" in pb.playbooks
    return ReplyEngine(SessionManager(), ScriptLLM(slots), playbooks=pb, rate_limit=100)


def test_thread_isolation():
    assert SessionManager.key("xianyu", "u1", None, "u1:A") != SessionManager.key(
        "xianyu", "u1", None, "u1:B"
    )
    assert SessionManager.key("qq", "u1", None) == "qq:u1:u1"


def test_xianyu_parse_requires_thread_fields():
    x = XianyuAdapter()
    e = x.parse_webhook({"buyer": "b1", "item_id": "i9", "content": "在吗"})
    assert e and e.thread_id == "b1:i9"
    assert x.parse_webhook({"buyer": "b1", "content": "在吗"}) is None
    assert x.available() is False


def test_resume_full_flow():
    slots = [
        {"name": "", "education": "", "experience": "", "target": "", "contact": ""},
        {"name": "阿强", "education": "", "experience": "", "target": "", "contact": ""},
        {"name": "", "education": "本科XX大学", "experience": "", "target": "", "contact": ""},
        {"name": "", "education": "", "experience": "3年运营", "target": "", "contact": ""},
        {"name": "", "education": "", "experience": "", "target": "产品经理", "contact": ""},
        {"name": "", "education": "", "experience": "", "target": "", "contact": "13800000000"},
    ]
    e = make_engine(slots)
    assert "用来做什么" in run(e, ev(text="你好,想改简历"))
    assert "怎么称呼" in run(e, ev(text="求职用的"))
    assert "学历" in run(e, ev(text="我叫阿强"))
    assert "工作几年" in run(e, ev(text="本科XX大学"))
    assert "目标岗位" in run(e, ev(text="3年运营"))
    assert "联系方式" in run(e, ev(text="产品经理"))
    assert run(e, ev(text="13800000000")).startswith("【初稿】")
    # done 后回到通用链路
    assert run(e, ev(text="谢谢,随便聊聊量子力学xyz")) == "free-talk"


def test_same_user_other_product_starts_over():
    e = make_engine([])
    run(e, ev(text="改简历"))
    run(e, ev(text="求职用的"))
    # 同人另一商品:全新 demand
    out = run(e, ev(text="这个也改改简历", thread="u1:itemB", product="简历优化"))
    assert "用来做什么" in out

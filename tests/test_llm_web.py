import asyncio

from askbot.llm.deepseek_web import FALLBACK, DeepSeekWebClient


def test_lazy_no_browser_on_construct():
    c = DeepSeekWebClient(profile_dir="data/not-exist-profile", headless=True)
    assert c.is_stub() is False


def test_failure_returns_fallback_not_raise():
    c = DeepSeekWebClient(profile_dir="data/not-exist-profile", headless=True)
    c._chat_sync = lambda messages, system: (_ for _ in ()).throw(RuntimeError("boom"))
    out = asyncio.run(c.chat([{"role": "user", "content": "hi"}]))
    assert out == FALLBACK


def test_provider_switch_builds_web_client(monkeypatch):
    from askbot.app import build_engine
    from askbot.config import settings

    monkeypatch.setattr(settings, "llm_provider", "deepseek-web")
    engine = build_engine()
    assert isinstance(engine.llm, DeepSeekWebClient)


def test_build_prompt_persona_and_budget():
    from askbot.llm.deepseek_web import DeepSeekWebClient as W

    msgs = [
        {"role": "user", "content": "旧问题" + "x" * 200},
        {"role": "assistant", "content": "旧回答"},
        {"role": "user", "content": "新问题"},
    ]
    out = W.build_prompt(msgs, system="你是客服", max_chars=60)
    assert out.startswith("你是客服")
    assert "新问题" in out  # 最后一条恒保留
    assert "旧问题" not in out  # 超预算旧的被裁


def test_build_prompt_empty():
    from askbot.llm.deepseek_web import DeepSeekWebClient as W

    assert W.build_prompt([], system="S") == "S"


class _FakeBtn:
    def __init__(self, pressed: str | None):
        self._pressed = pressed
        self.clicks = 0

    def get_attribute(self, name: str):
        return self._pressed if name == "aria-pressed" else None

    def click(self):
        self.clicks += 1


class _FakeSpan:
    def __init__(self, btn: _FakeBtn):
        self._btn = btn

    def locator(self, _sel: str):
        return self._btn


class _FakeFound:
    def __init__(self, btn: _FakeBtn):
        self._btn = btn

    @property
    def first(self):
        return _FakeSpan(self._btn)


class _FakePage:
    def __init__(self, think_pressed: str | None, search_pressed: str | None):
        self.states = {"深度思考": _FakeBtn(think_pressed), "智能搜索": _FakeBtn(search_pressed)}

    def get_by_text(self, name: str, exact: bool = False):
        return _FakeFound(self.states[name])

    def wait_for_timeout(self, _ms: int):
        pass


def test_ensure_modes_clicks_only_on_mismatch():
    from askbot.llm.deepseek_web import DeepSeekWebClient as W

    c = W(headless=True)
    page = _FakePage(think_pressed="false", search_pressed="true")
    c._ensure_modes(page, think=True, search=True)
    assert page.states["深度思考"].clicks == 1
    assert page.states["智能搜索"].clicks == 0

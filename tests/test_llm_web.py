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

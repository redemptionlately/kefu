from askbot.core.router import route


def test_keyword():
    assert route("你好,在吗").action == "reply"


def test_handoff():
    r = route("转人工谢谢")
    assert r.action == "handoff"


def test_llm_fallback():
    assert route("这是一个复杂问题xyz").action == "llm"

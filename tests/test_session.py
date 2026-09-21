from askbot.core import guardrails
from askbot.core.session import SessionManager


def test_session_ttl_and_history():
    sm = SessionManager(ttl_seconds=60, max_history=2)
    sm.append("k1", "user", "a")
    sm.append("k1", "user", "b")
    sm.append("k1", "user", "c")
    assert len(sm.get("k1").history) == 2


def test_rate_limit():
    guardrails.reset_rate_limit()
    k = "u-test"
    assert all(guardrails.check_rate_limit(k, 3) for _ in range(3))
    assert not guardrails.check_rate_limit(k, 3)

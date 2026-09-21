from askbot.core import guardrails


def test_sanitize_truncates():
    assert guardrails.sanitize("abc", max_length=2) == "ab"


def test_sanitize_blocked():
    assert "人工" in guardrails.sanitize("我的密码忘了")


def test_group_ignore():
    assert guardrails.should_ignore_group("大家好", at_bot=False) is True
    assert guardrails.should_ignore_group("@机器人 大家好", at_bot=False) is False
    assert guardrails.should_ignore_group("大家好", at_bot=True) is False
    assert guardrails.should_ignore_group("大家好", at_bot=False, group_only_on_at=False) is False

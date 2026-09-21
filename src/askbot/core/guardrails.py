"""护栏:限流/长度截断/群聊@过滤.保持纯函数可测试."""
from __future__ import annotations

import time

_BLOCKED = ("密码", "身份证")
_hits: dict[str, list[float]] = {}


def check_rate_limit(key: str, limit: int = 3, window: float = 10.0) -> bool:
    """True=允许,False=超限."""
    now = time.time()
    arr = [t for t in _hits.get(key, []) if now - t < window]
    if len(arr) >= limit:
        _hits[key] = arr
        return False
    arr.append(now)
    _hits[key] = arr
    return True


def reset_rate_limit() -> None:
    _hits.clear()


def sanitize(text: str, max_length: int = 800) -> str:
    t = text.strip()[:max_length]
    for w in _BLOCKED:
        if w in t:
            return "涉及敏感信息,请联系人工客服处理。"
    return t


def should_ignore_group(text: str, at_bot: bool, group_only_on_at: bool = True) -> bool:
    return group_only_on_at and not at_bot and "@" not in text

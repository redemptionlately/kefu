"""关键词路由:命中走固定回复,否则 fallback=llm;转人工短路."""
from __future__ import annotations

from dataclasses import dataclass

KEYWORD_ROUTES: dict[str, str] = {
    "你好": "您好,这里是智能客服,请问有什么可以帮您?",
    "营业时间": "我们的营业时间是每天 9:00-21:00。",
    "退款": "退款请提供订单号,我们将在1-3个工作日内处理。",
}

HANDOFF_KEYWORDS = ("转人工", "人工客服", "找人")


@dataclass
class RouteResult:
    action: str  # "reply" | "handoff" | "llm"
    text: str = ""


def route(text: str) -> RouteResult:
    t = text.strip()
    if any(k in t for k in HANDOFF_KEYWORDS):
        return RouteResult(action="handoff", text="已为您转接人工客服,请稍候。")
    for kw, reply in KEYWORD_ROUTES.items():
        if kw in t:
            return RouteResult(action="reply", text=reply)
    return RouteResult(action="llm")

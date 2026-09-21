"""FastAPI: /healthz, /webhook/onebot(QQ), /webhook/wechat."""
from __future__ import annotations

from fastapi import FastAPI, Request

from askbot.adapters.qq import QQAdapter
from askbot.adapters.wechat import WeChatAdapter
from askbot.config import settings
from askbot.core.knowledge import KnowledgeBase
from askbot.core.reply_engine import ReplyEngine
from askbot.core.session import SessionManager
from askbot.llm.openai_compat import OpenAICompatClient

app = FastAPI(title="AskBot")
_qq = QQAdapter()
_wechat = WeChatAdapter()
_engine = ReplyEngine(SessionManager(), OpenAICompatClient(), KnowledgeBase())


@app.get("/healthz")
async def healthz() -> dict:
    return {"ok": True, "wechat_available": _wechat.available()}


@app.post("/webhook/onebot")
async def onebot_webhook(req: Request) -> dict:
    payload = await req.json()
    event = _qq.parse_webhook(payload)
    if not event:
        return {"ignored": True}
    reply = await _engine.handle(event)
    if reply:
        await _qq.send(event.user_id, reply, event.group_id)
    return {"ok": True}


@app.post("/webhook/wechat")
async def wechat_webhook(req: Request) -> dict:
    payload = await req.json()
    event = _wechat.parse_webhook(payload)
    if not event:
        return {"ignored": True}
    reply = await _engine.handle(event)
    if reply:
        await _wechat.send(event.user_id, reply, event.group_id)
    return {"ok": True, "reply": reply}

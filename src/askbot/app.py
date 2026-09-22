"""FastAPI: /healthz, /webhook/onebot(QQ NapCat), /webhook/wechat."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from askbot.adapters.qq import QQAdapter, authorized
from askbot.adapters.wechat import WeChatAdapter
from askbot.config import settings
from askbot.core.knowledge import KnowledgeBase
from askbot.core.playbook import PlaybookEngine
from askbot.core.reply_engine import ReplyEngine
from askbot.core.session import SessionManager
from askbot.core.style import StyleCorpus
from askbot.infra.db import SessionStore
from askbot.infra.logger import logger
from askbot.llm.base import LLMClient
from askbot.llm.openai_compat import OpenAICompatClient


def build_engine() -> ReplyEngine:
    cfg = settings.load_yaml()
    reply_cfg = cfg.get("reply", {})
    rate_cfg = cfg.get("rate_limit", {})
    sess_cfg = cfg.get("session", {})
    kb_cfg = cfg.get("knowledge", {})
    store: SessionStore | None = None
    if cfg.get("session", {}).get("persist", True):
        try:
            store = SessionStore()
        except Exception:
            logger.exception("SessionStore 初始化失败,降级为纯内存")
    sessions = SessionManager(
        ttl_seconds=int(sess_cfg.get("ttl_seconds", 1800)),
        max_history=int(sess_cfg.get("max_history", 20)),
        store=store,
    )
    kb = KnowledgeBase.from_json(kb_cfg.get("faq_path", "data/faq.json"))
    logger.info("知识库加载 faq 条数={}", len(kb.faq))
    pb_cfg = cfg.get("playbooks", {})
    playbooks = PlaybookEngine.from_dir(pb_cfg.get("dir", "data/playbooks"))
    logger.info("话术 playbook 加载={}", list(playbooks.playbooks))
    style_cfg = cfg.get("style", {})
    style = StyleCorpus.from_dir(style_cfg.get("dir", "data/style"))
    logger.info("人味语料条数={}", len(style.examples))
    if settings.llm_provider == "deepseek-web":
        from askbot.llm.deepseek_web import DeepSeekWebClient

        llm: LLMClient = DeepSeekWebClient()
    else:
        llm = OpenAICompatClient()
    return ReplyEngine(
        sessions,
        llm,
        kb,
        max_length=int(reply_cfg.get("max_length", 800)),
        rate_limit=int(rate_cfg.get("per_user_per_10s", 3)),
        group_only_on_at=bool(reply_cfg.get("group_only_on_at", True)),
        playbooks=playbooks,
        style=style,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.engine = build_engine()
    app.state.qq = QQAdapter()
    app.state.wechat = WeChatAdapter()
    await app.state.qq.start()
    await app.state.wechat.start()
    yield
    await app.state.qq.stop()
    await app.state.wechat.stop()


app = FastAPI(title="AskBot", lifespan=lifespan)


def _engine(req: Request) -> ReplyEngine:
    if not hasattr(req.app.state, "engine"):
        req.app.state.engine = build_engine()
    return req.app.state.engine


@app.get("/healthz")
async def healthz(req: Request) -> dict:
    llm = req.app.state.engine.llm if hasattr(req.app.state, "engine") else None
    return {
        "ok": True,
        "wechat_available": WeChatAdapter().available(),
        "llm_stub": llm.is_stub() if hasattr(llm, "is_stub") else True,
    }


@app.post("/webhook/onebot")
async def onebot_webhook(req: Request) -> JSONResponse:
    if not authorized(req.headers):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    payload = await req.json()
    qq: QQAdapter = getattr(req.app.state, "qq", QQAdapter())
    event = qq.parse_webhook(payload)
    if not event:
        return JSONResponse({"ignored": True})
    reply = await _engine(req).handle(event)
    if reply:
        engine = _engine(req)
        for i, bubble in enumerate(engine.bubbles(reply)):
            if i:
                await asyncio.sleep(0.8)  # 真人打字节奏
            await qq.send(event.user_id, bubble, event.group_id)
    return JSONResponse({"ok": True})


@app.post("/webhook/wechat")
async def wechat_webhook(req: Request) -> dict:
    payload = await req.json()
    wechat: WeChatAdapter = getattr(req.app.state, "wechat", WeChatAdapter())
    event = wechat.parse_webhook(payload)
    if not event:
        return {"ignored": True}
    reply = await _engine(req).handle(event)
    if reply:
        engine = _engine(req)
        for i, bubble in enumerate(engine.bubbles(reply)):
            if i:
                await asyncio.sleep(0.8)
            await wechat.send(event.user_id, bubble, event.group_id)
    return {"ok": True, "reply": reply}


@app.get("/")
async def index() -> dict:
    return {"service": "AskBot", "health": "/healthz", "docs": "/docs"}

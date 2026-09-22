"""CLI: serve / doctor / send-test."""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from askbot.adapters.base import MessageEvent
from askbot.config import settings


def cmd_doctor() -> int:
    cfg = settings.load_yaml()
    issues: list[str] = []
    if settings.llm_provider == "deepseek-web":
        issues.append(
            f"LLM 网页版模式(headless={settings.deepseek_headless},"
            f"profile={settings.deepseek_profile},预算={settings.deepseek_max_chars},"
            f"深度思考={settings.deepseek_think},联网={settings.deepseek_search})"
        )
    elif settings.llm_api_key.startswith("sk-please"):
        issues.append("LLM_API_KEY 未配置(当前 stub 回显模式)")
    try:
        import fastapi, uvicorn, httpx  # noqa: F401
    except ImportError as e:
        issues.append(f"依赖缺失: {e}")
    issues.append("微信个人号通道已下线(固定 log 模式,不收发)")
    faq_path = cfg.get("knowledge", {}).get("faq_path", "data/faq.json")
    p = Path(faq_path)
    if not p.exists():
        issues.append(f"知识库缺失: {faq_path}")
    else:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            n = len(data) if isinstance(data, (dict, list)) else 0
            issues.append(f"知识库 OK: {faq_path}({n} 条)")
        except Exception as e:
            issues.append(f"知识库解析失败: {e}")
    try:
        from askbot.infra.db import init_db

        init_db()
        issues.append("sqlite 会话库 OK: data/askbot.db")
    except Exception as e:
        issues.append(f"sqlite 初始化失败: {e}")
    print(f"config: {settings.askbot_config} yaml_keys={list(cfg)}")
    print("doctor:")
    for i in issues:
        print(f" - {i}")
    return 0


def cmd_serve(port: int) -> int:
    import uvicorn

    uvicorn.run("askbot.app:app", host=settings.askbot_host, port=port, reload=False)
    return 0


def cmd_send_test(platform: str, target: str, text: str) -> int:
    from askbot.app import build_engine

    async def _run() -> None:
        engine = build_engine()
        event = MessageEvent(platform=platform, user_id=target, text=text)
        reply = await engine.handle(event)
        print(f"in : [{platform}] {target}: {text}")
        for b in engine.bubbles(reply or ""):
            print(f"out: {b}")

    asyncio.run(_run())
    return 0


def main() -> None:
    p = argparse.ArgumentParser(prog="askbot")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor")
    s = sub.add_parser("serve")
    s.add_argument("--port", type=int, default=settings.askbot_port)
    t = sub.add_parser("send-test")
    t.add_argument("--platform", default="qq")
    t.add_argument("--target", default="123")
    t.add_argument("--text", default="你好")
    a = p.parse_args()
    if a.cmd == "doctor":
        raise SystemExit(cmd_doctor())
    if a.cmd == "serve":
        raise SystemExit(cmd_serve(a.port))
    if a.cmd == "send-test":
        raise SystemExit(cmd_send_test(a.platform, a.target, a.text))

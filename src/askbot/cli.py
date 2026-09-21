"""CLI: serve / doctor / send-test / listen."""
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
    if settings.llm_api_key.startswith("sk-please"):
        issues.append("LLM_API_KEY 未配置(当前 stub 回显模式)")
    try:
        import fastapi, uvicorn, httpx  # noqa: F401
    except ImportError as e:
        issues.append(f"依赖缺失: {e}")
    try:
        from askbot.adapters.wechat import WeChatAdapter

        issues.append(f"微信 mode={settings.wechat_mode} available={WeChatAdapter().available()}")
    except Exception as e:  # pragma: no cover
        issues.append(f"微信适配器自检失败: {e}")
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
        print(f"out: {reply}")

    asyncio.run(_run())
    return 0


def cmd_listen() -> int:
    """微信 ferry 模式轮询:收→引擎→回. Ctrl+C 退出."""
    from askbot.adapters.wechat import WeChatAdapter
    from askbot.app import build_engine

    async def _run() -> None:
        adapter = WeChatAdapter()
        await adapter.start()
        if adapter._wcf is None:
            print(f"微信 mode={adapter.mode} 无真实客户端,无法监听(先装依赖或配 Ferry)")
            return
        engine = build_engine()
        print("微信监听中,Ctrl+C 退出…")
        try:
            while True:
                event = await adapter.recv_once()
                if event is None:
                    await asyncio.sleep(0.2)
                    continue
                reply = await engine.handle(event)
                if reply:
                    await adapter.send(event.user_id, reply, event.group_id)
        except KeyboardInterrupt:
            pass
        finally:
            await adapter.stop()

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
    sub.add_parser("listen")
    a = p.parse_args()
    if a.cmd == "doctor":
        raise SystemExit(cmd_doctor())
    if a.cmd == "serve":
        raise SystemExit(cmd_serve(a.port))
    if a.cmd == "send-test":
        raise SystemExit(cmd_send_test(a.platform, a.target, a.text))
    if a.cmd == "listen":
        raise SystemExit(cmd_listen())

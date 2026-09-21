"""CLI: serve / doctor / send-test."""
from __future__ import annotations

import argparse

from askbot.config import settings


def cmd_doctor() -> int:
    settings.load_yaml()
    issues: list[str] = []
    if settings.llm_api_key.startswith("sk-please"):
        issues.append("LLM_API_KEY 未配置(当前 stub 回显模式)")
    try:
        import fastapi, uvicorn, httpx  # noqa: F401
    except ImportError as e:
        issues.append(f"依赖缺失: {e}")
    try:
        import wcferry  # noqa: F401
    except ImportError:
        issues.append("wcferry 未安装:微信走日志降级模式(仅开发)")
    print(f"config: {settings.askbot_config} yaml_keys={list(settings.yaml_config)}")
    if issues:
        print("doctor 发现:")
        for i in issues:
            print(f" - {i}")
    else:
        print("doctor OK")
    return 0


def cmd_serve(port: int) -> int:
    import uvicorn

    uvicorn.run("askbot.app:app", host=settings.askbot_host, port=port, reload=False)
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
    t.add_argument("--text", default="hi")
    a = p.parse_args()
    if a.cmd == "doctor":
        raise SystemExit(cmd_doctor())
    if a.cmd == "serve":
        raise SystemExit(cmd_serve(a.port))
    print(f"[{a.platform}] send -> {a.target}: {a.text} (日志模式,未真实发送)")

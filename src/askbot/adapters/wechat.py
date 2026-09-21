"""微信适配器(个人号通道已下线,见 docs/DEPLOY.md §2).

保留最小实现:parse_webhook(协议解析,供以后企微/云 API 复用)+日志发送.
available()恒 False,任何 mode 都强制降级为 log,不阻断启动.
"""
from __future__ import annotations

from askbot.adapters.base import Adapter, MessageEvent
from askbot.config import settings
from askbot.infra.logger import logger


class WeChatAdapter(Adapter):
    platform = "wechat"

    def __init__(self, mode: str = "") -> None:
        m = (mode or settings.wechat_mode).lower()
        if m != "log":
            logger.warning("微信个人号通道已下线,mode={} 强制降级为 log", m)
        self.mode = "log"

    def available(self) -> bool:
        return False

    async def start(self) -> None:
        logger.info("WeChatAdapter 日志模式(个人号通道已下线)")

    async def stop(self) -> None:
        pass

    def parse_webhook(self, payload: dict) -> MessageEvent | None:
        text = str(payload.get("content", "")).strip()
        if not text:
            return None
        room = payload.get("roomid") or None
        return MessageEvent(
            platform="wechat",
            user_id=str(payload.get("sender", "")),
            group_id=room,
            text=text,
            msg_id=str(payload.get("msgid", "")),
            raw=payload,
        )

    async def send(self, target_id: str, text: str, group_id: str | None = None) -> bool:
        logger.info(
            "WeChat[log] send -> {}|{}: {}",
            group_id or target_id, target_id, text[:100],
        )
        return True

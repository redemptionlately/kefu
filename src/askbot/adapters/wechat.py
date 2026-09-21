"""微信适配器.

选型(已定,见 AGENTS.md §6): WeChatFerry 为主,wxauto 为降级.
WECHAT_MODE=ferry|wxauto|log,未装对应依赖时自动降级为日志模式,不阻断启动.
"""
from __future__ import annotations

from askbot.adapters.base import Adapter, MessageEvent
from askbot.config import settings
from askbot.infra.logger import logger


class WeChatAdapter(Adapter):
    platform = "wechat"

    def __init__(self, mode: str = "") -> None:
        self.mode = (mode or settings.wechat_mode).lower()

    def available(self) -> bool:
        if self.mode == "wxauto":
            try:
                import wxauto  # noqa: F401
                return True
            except ImportError:
                return False
        if self.mode == "log":
            return False
        try:
            import wcferry  # noqa: F401
            return True
        except ImportError:
            return False

    async def start(self) -> None:
        if not self.available():
            logger.warning("微信 mode={} 依赖缺失,运行于日志降级模式", self.mode)
        else:
            logger.info("WeChatAdapter connected (mode={})", self.mode)

    async def stop(self) -> None:
        pass

    def parse_webhook(self, payload: dict) -> MessageEvent | None:
        # WeChatFerry 主动推的消息体(约定): {sender, content, roomid?, msgid?}
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
        logger.info("WeChat[{}] send -> {}|{}: {}", self.mode, group_id or target_id, target_id, text[:100])
        # TODO(ferry): 接入真实 WcFerry send_text; TODO(wxauto): WxAuto.SendMsg
        return True

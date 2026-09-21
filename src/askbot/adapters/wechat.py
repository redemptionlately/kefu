"""微信适配器.

选型(已定,见 AGENTS.md §6): WeChatFerry 为主,wxauto 为降级.
WECHAT_MODE=ferry|wxauto|log.对应依赖缺失时自动降级为日志模式,不阻断启动.

依赖(可选安装,不进 requirements):
  pip install wcferry   # ferry 模式,需匹配版本微信客户端(3.9.x)
  pip install wxauto     # wxauto 模式,UI 自动化,仅实现发送;接收走 Ferry/HTTP 回调
"""
from __future__ import annotations

import asyncio

from askbot.adapters.base import Adapter, MessageEvent
from askbot.config import settings
from askbot.infra.logger import logger


class WeChatAdapter(Adapter):
    platform = "wechat"

    def __init__(self, mode: str = "") -> None:
        self.mode = (mode or settings.wechat_mode).lower()
        self._wcf = None
        self._wx = None

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
        if self.mode == "wxauto":
            try:
                from wxauto import WeChat

                self._wx = await asyncio.to_thread(WeChat)
                logger.info("WeChatAdapter wxauto 就绪")
                return
            except ImportError:
                logger.warning("wxauto 未安装,微信运行于日志降级模式")
                return
        if self.mode == "log":
            logger.info("WeChatAdapter 日志模式")
            return
        try:
            from wcferry import Wcf

            self._wcf = await asyncio.to_thread(Wcf)
            await asyncio.to_thread(self._wcf.enable_receiving_msg, False)
            logger.info("WeChatAdapter ferry 就绪 login={}", self._wcf.is_login())
        except ImportError:
            logger.warning("wcferry 未安装,微信运行于日志降级模式")

    async def stop(self) -> None:
        if self._wcf is not None:
            try:
                await asyncio.to_thread(self._wcf.cleanup)
            except Exception:
                logger.exception("Wcf cleanup 失败")
            self._wcf = None

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

    def parse_wcf_msg(self, msg: object) -> MessageEvent | None:
        """解析 wcferry WxMsg(对象或字典),文本类消息转事件,其他返回 None."""
        if isinstance(msg, dict):
            mtype = msg.get("type", 1)
            content = str(msg.get("content", "") or "")
            sender = str(msg.get("sender", "") or "")
            room = msg.get("roomid") or None
            mid = str(msg.get("id", "") or "")
        else:
            mtype = getattr(msg, "type", 1)
            content = str(getattr(msg, "content", "") or "")
            sender = str(getattr(msg, "sender", "") or "")
            room = getattr(msg, "roomid", None) or None
            mid = str(getattr(msg, "id", "") or "")
        if mtype != 1 or not content.strip() or sender.endswith("@chatroom"):
            return None
        return MessageEvent(
            platform="wechat", user_id=sender, group_id=room,
            text=content.strip(), msg_id=mid, raw={},
        )

    async def recv_once(self) -> MessageEvent | None:
        """ferry 模式阻塞取一条消息(线程池),无客户端返回 None."""
        if self._wcf is None:
            return None
        msg = await asyncio.to_thread(self._wcf.get_msg)
        if not msg:
            return None
        return self.parse_wcf_msg(msg)

    async def send(self, target_id: str, text: str, group_id: str | None = None) -> bool:
        if self._wcf is not None:
            try:
                await asyncio.to_thread(self._wcf.send_text, text, group_id or target_id)
                return True
            except Exception:
                logger.exception("Ferry 发送失败")
                return False
        if self._wx is not None:
            try:
                await asyncio.to_thread(self._wx.SendMsg, text, group_id or target_id)
                return True
            except Exception:
                logger.exception("wxauto 发送失败")
                return False
        logger.info("WeChat[{}] send -> {}|{}: {}", self.mode, group_id or target_id, target_id, text[:100])
        return True

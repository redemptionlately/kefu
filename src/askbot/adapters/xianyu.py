"""闲鱼适配器(占位,log 模式).

现状:闲鱼无官方客服 API,业内做法是安卓无障碍 RPA 或第三方协议,
两者都有封号风险,生产用之前必须小号长期试水.
本适配器只定协议:上游(不论 RPA/协议)把消息转成 MessageEvent,
关键字段:
  user_id   买家标识
  thread_id 必须填 "buyer:item" 格式,同客同品会话隔离就靠它
  product   商品标题,用于 playbook 匹配
  text      消息文本
合规红线:频率比 QQ 更严(建议单用户 30s 内 ≤2 条)、首交流量人工审、
敏感品类(简历代写涉及个人信息)绝不索要身份证/银行卡,不在聊天发外链.
"""
from __future__ import annotations

from askbot.adapters.base import Adapter, MessageEvent
from askbot.infra.logger import logger


class XianyuAdapter(Adapter):
    platform = "xianyu"

    def available(self) -> bool:
        return False

    async def start(self) -> None:
        logger.info("XianyuAdapter 日志模式(等 RPA/协议上游对接)")

    async def stop(self) -> None:
        pass

    def parse_webhook(self, payload: dict) -> MessageEvent | None:
        """上游约定: {buyer, item_id, item_title?, content, msgid?}."""
        text = str(payload.get("content", "")).strip()
        buyer = str(payload.get("buyer", ""))
        item = str(payload.get("item_id", ""))
        if not text or not buyer or not item:
            return None
        return MessageEvent(
            platform="xianyu",
            user_id=buyer,
            text=text,
            msg_id=str(payload.get("msgid", "")),
            thread_id=f"{buyer}:{item}",
            product=str(payload.get("item_title", "") or ""),
            raw=payload,
        )

    async def send(self, target_id: str, text: str, group_id: str | None = None) -> bool:
        logger.info("Xianyu[log] send -> {}: {}", target_id, text[:100])
        return True

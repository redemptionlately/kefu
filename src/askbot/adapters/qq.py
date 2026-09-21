"""QQ 适配器.选型(已定,见 AGENTS.md §6): NapCatQQ OneBot11.

收: NapCat HTTP POST → parse_webhook; 发: POST {ONEBOT_HTTP_URL}/send_msg.
go-cqhttp 已归档不用;Lagrange 留作 Linux 服务端备选.
"""
from __future__ import annotations

import httpx
from askbot.adapters.base import Adapter, MessageEvent
from askbot.config import settings
from askbot.infra.logger import logger


def authorized(headers: dict | object) -> bool:
    """OneBot 上报鉴权:未配 token 直接放行,否则校验 Authorization 头."""
    token = settings.onebot_access_token
    if not token:
        return True
    get = headers.get if hasattr(headers, "get") else dict(headers).get
    return get("authorization", "") == f"Bearer {token}"


def _extract_text(payload: dict) -> str:
    msg = payload.get("message")
    if isinstance(msg, str):
        return msg.strip()
    if isinstance(msg, list):
        parts = [seg.get("data", {}).get("text", "") for seg in msg if seg.get("type") == "text"]
        return "".join(parts).strip()
    return str(payload.get("raw_message", "")).strip()


def _extract_images(payload: dict) -> list[str]:
    """OneBot 消息段里的图片直链,供识图;非 http 全部丢弃."""
    msg = payload.get("message")
    out: list[str] = []
    if isinstance(msg, list):
        for seg in msg:
            if isinstance(seg, dict) and seg.get("type") == "image":
                url = str(seg.get("data", {}).get("url", "") or "")
                if url.startswith("http"):
                    out.append(url)
    return out


class QQAdapter(Adapter):
    platform = "qq"

    async def start(self) -> None:
        logger.info("QQAdapter ready (onebot={})", settings.onebot_http_url)

    async def stop(self) -> None:
        pass

    def parse_webhook(self, payload: dict) -> MessageEvent | None:
        if payload.get("post_type") != "message":
            return None
        text = _extract_text(payload)
        images = _extract_images(payload)
        if not text and not images:
            return None
        msg_type = payload.get("message_type", "private")
        group_id = str(payload["group_id"]) if msg_type == "group" else None
        return MessageEvent(
            platform="qq",
            user_id=str(payload.get("user_id", "")),
            group_id=group_id,
            text=text,
            msg_id=str(payload.get("message_id", "")),
            raw=payload,
            images=images,
        )

    async def send(self, target_id: str, text: str, group_id: str | None = None) -> bool:
        message_type = "group" if group_id else "private"
        target = group_id or target_id
        url = settings.onebot_http_url.rstrip("/") + "/send_msg"
        headers = (
            {"Authorization": f"Bearer {settings.onebot_access_token}"}
            if settings.onebot_access_token
            else {}
        )
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.post(
                    url,
                    headers=headers,
                    json={"message_type": message_type, "user_id": target, "group_id": target, "message": text},
                )
                r.raise_for_status()
            return True
        except Exception:
            logger.exception("QQ send failed")
            return False

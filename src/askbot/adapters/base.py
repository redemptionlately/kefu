"""Adapter 抽象:所有平台必须实现 parse_webhook + send."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from time import time


@dataclass
class MessageEvent:
    platform: str  # "wechat" | "qq"
    user_id: str
    text: str
    msg_id: str = ""
    group_id: str | None = None
    ts: float = field(default_factory=time)
    raw: dict = field(default_factory=dict)
    at_bot: bool = True  # 群聊是否@机器人,微信私聊恒True
    images: list[str] = field(default_factory=list)  # 图片 URL,供识图
    thread_id: str | None = None  # 同客同品会话域(如咸鱼 user:item),有则会话按它隔离
    product: str | None = None  # 商品/服务标题,用于 playbook 匹配


class Adapter(ABC):
    platform: str = "base"

    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...

    @abstractmethod
    async def send(self, target_id: str, text: str, group_id: str | None = None) -> bool: ...

    @abstractmethod
    def parse_webhook(self, payload: dict) -> MessageEvent | None: ...

    def available(self) -> bool:
        return True

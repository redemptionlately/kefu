"""服务话术 playbook:按商品/意图走多阶段流程(需求→收资→初稿).

状态存 session.data,切商品靠 thread_id 隔离,天然不串话.
core 只做确定性流转(LLM 仅用于字段提取和初稿生成),可单元测试.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import yaml

from askbot.adapters.base import MessageEvent
from askbot.core.session import Session
from askbot.infra.logger import logger


@dataclass
class Playbook:
    id: str
    name: str = ""
    match_keywords: list[str] = field(default_factory=list)
    stages: list[dict] = field(default_factory=list)


class PlaybookEngine:
    def __init__(self, playbooks: list[Playbook] | None = None) -> None:
        self.playbooks = {p.id: p for p in (playbooks or [])}

    @classmethod
    def from_dir(cls, path: str | Path) -> PlaybookEngine:
        books: list[Playbook] = []
        d = Path(path)
        if d.is_dir():
            for f in sorted(d.glob("*.yaml")) + sorted(d.glob("*.yml")):
                try:
                    raw = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
                    books.append(
                        Playbook(
                            id=str(raw.get("id", f.stem)),
                            name=str(raw.get("name", "")),
                            match_keywords=[str(k) for k in raw.get("match_keywords", [])],
                            stages=list(raw.get("stages", [])),
                        )
                    )
                except Exception:
                    logger.exception("playbook 加载失败: {}", f)
        return cls(books)

    def pick(self, event: MessageEvent) -> Playbook | None:
        hay = f"{event.product or ''} {event.text}"
        for pb in self.playbooks.values():
            if any(kw and kw in hay for kw in pb.match_keywords):
                return pb
        return None

    async def handle(
        self,
        event: MessageEvent,
        session: Session,
        llm: Any,
        persist: Callable[[], None],
    ) -> str | None:
        """返回回复文本;None 表示不接管,走通用链路."""
        st: dict = session.data.get("playbook") or {}
        pb = self.playbooks.get(st.get("id", "")) if st else self.pick(event)
        if not pb or not pb.stages:
            return None
        if st.get("done"):
            return None
        if not st:
            st = {"id": pb.id, "stage": 0, "slots": {}, "asked": 0}
            session.data["playbook"] = st
        return await self._step(pb, st, event, llm, persist)

    async def _step(
        self,
        pb: Playbook,
        st: dict,
        event: MessageEvent,
        llm: Any,
        persist: Callable[[], None],
    ) -> str:
        stage = pb.stages[st["stage"]]
        sid = stage.get("id", "")
        # 收资阶段:先提取本轮字段
        if sid == "collect":
            extracted = await self._extract(llm, stage.get("slots", []), event.text)
            st["slots"].update({k: v for k, v in extracted.items() if v})
            persist()
            missing = [s for s in stage.get("slots", []) if not st["slots"].get(s["key"])]
            if not missing:
                st["stage"] += 1
                return await self._finish(pb, st, llm, persist)
            nxt = missing[0]
            return nxt.get("ask", "请补充一下相关信息。")
        # 初稿阶段
        if sid == "draft":
            return await self._finish(pb, st, llm, persist)
        # 需求阶段:命中类型词就往下走
        adv = [k for k in stage.get("advance_keywords", []) if k in event.text]
        if adv:
            st["slots"][stage.get("slot", "type")] = adv[0]
            st["stage"] += 1
            st["asked"] = 0
            persist()
            return await self._step(pb, st, event, llm, persist)
        asks: list[str] = stage.get("ask", ["请详细说说您的需求。"])
        out = asks[st.get("asked", 0) % len(asks)]
        st["asked"] = st.get("asked", 0) + 1
        persist()
        return out

    async def _finish(self, pb: Playbook, st: dict, llm: Any, persist: Callable[[], None]) -> str:
        st["stage"] = len(pb.stages) - 1
        slots = st.get("slots", {})
        prompt = (
            "你是资深简历顾问。根据已收集的客户信息,直接输出给客户看的简历初稿框架"
            "(分模块,每模块2-3条要点,语气专业热情)。\n已收集信息:"
            f"{json.dumps(slots, ensure_ascii=False)}"
        )
        try:
            draft = await llm.chat(
                [{"role": "user", "content": prompt}], system="你是资深简历顾问。"
            )
        except Exception:
            logger.exception("初稿生成失败")
            draft = "信息已记下,顾问稍后为您出初稿,请稍候。"
        st["done"] = True
        persist()
        return draft

    @staticmethod
    async def _extract(llm: Any, slots: list[dict], text: str) -> dict:
        keys = [s["key"] for s in slots]
        if not keys:
            return {}
        prompt = (
            "从客户回复中提取字段,只返回JSON对象,缺失填空字符串,不要解释。"
            f"字段:{keys}。客户回复:{text}"
        )
        try:
            raw = await llm.chat([{"role": "user", "content": prompt}])
            m = re.search(r"\{.*\}", raw, re.S)
            data = json.loads(m.group(0)) if m else {}
            return {k: str(data.get(k, "")).strip() for k in keys}
        except Exception:
            logger.warning("字段提取失败,转人工追问")
            return {}

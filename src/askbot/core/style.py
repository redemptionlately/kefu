"""人味三件套:话术语料(few-shot)+短句分条.

语料=data/style/*.json,每条 {user, assistant},学的是真人客服的说话方式,
拼进 system prompt。分条:长回复拆成多条短消息,模拟真人打字节奏.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HUMAN_RULES = (
    "说话像真人:每条只讲一件事、只问一个问题;多用短句,少用长段落;"
    "禁用AI腔(很高兴为您服务/亲爱的用户/根据分析);"
    "允许口语(嗯嗯/哈/亲~/),但别每句都带;先共情再办事,不确定就问,别编."
)


class StyleCorpus:
    def __init__(self, examples: list[dict] | None = None, max_examples: int = 8) -> None:
        self.examples = (examples or [])[:max_examples]

    @classmethod
    def from_dir(cls, path: str | Path, max_examples: int = 8) -> StyleCorpus:
        out: list[dict] = []
        d = Path(path)
        if d.is_dir():
            for f in sorted(d.glob("*.json")):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    if isinstance(data, list):
                        out.extend(
                            e for e in data if isinstance(e, dict) and e.get("user")
                        )
                except (json.JSONDecodeError, OSError):
                    continue
        return cls(out, max_examples)

    def apply_system(self, base: str) -> str:
        parts = [base, HUMAN_RULES]
        for e in self.examples:
            parts.append(f"比如客户说:{e['user']} / 你回:{e.get('assistant', '')}")
        return "\n".join(parts)


def split_message(text: str, max_len: int = 120, max_parts: int = 3) -> list[str]:
    """按句切分,超长再硬切,最多 max_parts 条,多的合并进最后一条."""
    chunks = [c.strip() for c in re.split(r"(?<=[。！？\n])", text) if c.strip()]
    parts: list[str] = []
    for c in chunks:
        while len(c) > max_len:
            parts.append(c[:max_len])
            c = c[max_len:]
        if c:
            if parts and len(parts[-1]) + len(c) <= max_len // 2:
                parts[-1] += c
            else:
                parts.append(c)
    if len(parts) > max_parts:
        parts = parts[: max_parts - 1] + ["".join(parts[max_parts - 1 :])]
    return parts or [text]

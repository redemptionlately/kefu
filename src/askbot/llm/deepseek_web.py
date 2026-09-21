"""DeepSeek 网页版适配:Playwright 驱动 chat.deepseek.com.

用户明确要求网页版(不用 API key).风险:非官方接口,改版/限流/封号自担;
chat() 永不抛异常,失败返回提示语,客服链路不断.
首次使用:DEEPSEEK_HEADLESS=false 跑一次,手动扫码登录,会话持久化到 profile 目录.
"""
from __future__ import annotations

import asyncio
import time

from askbot.config import settings
from askbot.infra.logger import logger

LOGIN_URL = "https://chat.deepseek.com/"
FALLBACK = "抱歉,AI 网页端暂时不可用,请稍后再试或转人工。"
NEED_LOGIN = "DeepSeek 网页未登录:请先 DEEPSEEK_HEADLESS=false 跑一次 send-test 手动登录。"

# 按优先级尝试,DeepSeek 改版时只改这里
TEXTAREA_SELECTORS = [
    'textarea[placeholder*="给 DeepSeek"]',
    'textarea[placeholder*="deepseek" i]',
    "div[contenteditable='true']",
    "textarea",
]
ASSISTANT_SELECTORS = [
    ".ds-markdown",
    "[data-role='assistant']",
    ".message-assistant",
]
STOP_SELECTORS = ["button:has-text('停止')", "button:has-text('stop' i)"]


class DeepSeekWebClient:
    def __init__(
        self,
        profile_dir: str = "",
        headless: bool | None = None,
        timeout_s: int = 150,
    ) -> None:
        self.profile_dir = profile_dir or settings.deepseek_profile
        self.headless = settings.deepseek_headless if headless is None else headless
        self.timeout_s = timeout_s
        self._lock = asyncio.Lock()

    def is_stub(self) -> bool:
        return False

    async def chat(self, messages: list[dict], system: str = "") -> str:
        try:
            async with self._lock:
                return await asyncio.to_thread(self._chat_sync, messages, system)
        except Exception:
            logger.exception("DeepSeek 网页端异常")
            return FALLBACK

    # ---- 同步部分(跑在线程池) ----
    def _chat_sync(self, messages: list[dict], system: str) -> str:
        from playwright.sync_api import sync_playwright

        user_text = messages[-1]["content"] if messages else ""
        if system and messages and len(messages) <= 2:
            user_text = f"{system}\n\n{user_text}"
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                self.profile_dir,
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"],
            )
            try:
                page = ctx.pages[0] if ctx.pages else ctx.new_page()
                page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3000)
                if self._is_login_page(page):
                    return NEED_LOGIN
                box = self._find_textarea(page)
                if not box:
                    logger.warning("找不到网页输入框,候选全灭")
                    return FALLBACK
                before = self._assistant_texts(page)
                box.click()
                box.fill(user_text)
                page.wait_for_timeout(500)
                page.keyboard.press("Enter")
                return self._wait_reply(page, before)
            finally:
                ctx.close()

    def _is_login_page(self, page) -> bool:
        try:
            url = (page.url or "").lower()
            if "login" in url or "sign_in" in url or "signin" in url:
                return True
            btn = page.query_selector("button:has-text('登录'), button:has-text('Log in')")
            return btn is not None and btn.is_visible()
        except Exception:
            return False

    def _find_textarea(self, page):
        for sel in TEXTAREA_SELECTORS:
            try:
                loc = page.query_selector(sel)
                if loc and loc.is_visible():
                    return loc
            except Exception:
                continue
        return None

    def _assistant_texts(self, page) -> list[str]:
        for sel in ASSISTANT_SELECTORS:
            try:
                els = page.query_selector_all(sel)
                texts = [e.inner_text().strip() for e in els]
                texts = [t for t in texts if t]
                if texts:
                    return texts
            except Exception:
                continue
        try:
            n_md = page.locator("div[class*='mark']").count()
            n_msg = page.locator("div[class*='mess']").count()
            logger.debug("assistant 候选全空(mark={},mess={}) url={}", n_md, n_msg, page.url)
        except Exception:
            pass
        return []

    def _wait_reply(self, page, before: list[str]) -> str:
        deadline = time.time() + self.timeout_s
        last: list[str] = before
        stable = 0
        while time.time() < deadline:
            page.wait_for_timeout(2000)
            try:
                cur = self._assistant_texts(page)
            except Exception:
                continue
            if cur and cur != before and cur == last:
                stable += 1
                stopping = any(
                    self._visible(page, s) for s in STOP_SELECTORS
                )
                if stable >= 2 and not stopping:
                    return cur[-1]
            elif cur and cur != before:
                stable = 0
            last = cur if cur else last
        return last[-1] if last and last != before else FALLBACK

    @staticmethod
    def _visible(page, sel: str) -> bool:
        try:
            el = page.query_selector(sel)
            return el is not None and el.is_visible()
        except Exception:
            return False

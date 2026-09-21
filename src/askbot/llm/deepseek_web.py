"""DeepSeek 网页版适配:Playwright 驱动 chat.deepseek.com.

用户明确要求网页版(不用 API key).风险:非官方接口,改版/限流/封号自担;
chat() 永不抛异常,失败返回提示语,客服链路不断.
首次使用:DEEPSEEK_HEADLESS=false 跑一次,手动扫码登录,会话持久化到 profile 目录.

能力开关(环境变量):
  DEEPSEEK_THINK=true   深度思考(R1)
  DEEPSEEK_SEARCH=true  智能搜索(联网)
  DEEPSEEK_MAX_CHARS=100000  上下文预算,超了从旧往新裁
人设:调用方 system 参数每轮前置,网页无 system 位就这么喂.
识图:images 传 QQ 图片 URL,下载后走文件上传;失败则纯文本继续.
"""
from __future__ import annotations

import asyncio
import time
from pathlib import Path
from tempfile import gettempdir

from askbot.config import settings
from askbot.infra.logger import logger

LOGIN_URL = "https://chat.deepseek.com/"
FALLBACK = "抱歉,AI 网页端暂时不可用,请稍后再试或转人工。"
NEED_LOGIN = "DeepSeek 网页未登录:请先 DEEPSEEK_HEADLESS=false 跑一次 send-test 手动登录。"

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
TOGGLE_BUTTON_XPATH = "xpath=ancestor::div[contains(@class,'ds-toggle-button')][1]"


class DeepSeekWebClient:
    def __init__(
        self,
        profile_dir: str = "",
        headless: bool | None = None,
        timeout_s: int = 150,
        max_chars: int | None = None,
        think: bool | None = None,
        search: bool | None = None,
    ) -> None:
        self.profile_dir = profile_dir or settings.deepseek_profile
        self.headless = settings.deepseek_headless if headless is None else headless
        self.timeout_s = timeout_s
        self.max_chars = settings.deepseek_max_chars if max_chars is None else max_chars
        self.think = settings.deepseek_think if think is None else think
        self.search = settings.deepseek_search if search is None else search
        self._lock = asyncio.Lock()

    def is_stub(self) -> bool:
        return False

    @staticmethod
    def build_prompt(messages: list[dict], system: str = "", max_chars: int = 100000) -> str:
        """拼发往网页的文本:人设前置 + 按预算从旧往新裁,恒保留最后一条."""
        turns: list[str] = []
        for m in messages:
            role = "用户" if m.get("role") == "user" else "助手"
            turns.append(f"{role}:{m.get('content', '')}")
        if not turns:
            return system
        # 从新往旧累积,超预算就丢旧的
        kept: list[str] = []
        used = len(system)
        for t in reversed(turns):
            if kept and used + len(t) > max_chars:
                break
            kept.append(t)
            used += len(t)
        kept.reverse()
        body = "\n".join(kept)
        return f"{system}\n\n{body}" if system else body

    async def chat(
        self, messages: list[dict], system: str = "", images: list[str] | None = None
    ) -> str:
        try:
            async with self._lock:
                return await asyncio.to_thread(self._chat_sync, messages, system, images or [])
        except Exception:
            logger.exception("DeepSeek 网页端异常")
            return FALLBACK

    # ---- 同步部分(跑在线程池) ----
    def _chat_sync(self, messages: list[dict], system: str, images: list[str]) -> str:
        from playwright.sync_api import sync_playwright

        prompt = self.build_prompt(messages, system, self.max_chars)
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
                self._ensure_modes(page, self.think, self.search)
                n_img = self._upload_images(page, images)
                if n_img:
                    prompt = f"[已发{n_img}张图]\n{prompt}" if not prompt else prompt
                box = self._find_textarea(page)
                if not box:
                    logger.warning("找不到网页输入框,候选全灭")
                    return FALLBACK
                before = self._assistant_texts(page)
                box.click()
                box.fill(prompt)
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

    def _ensure_modes(self, page, think: bool, search: bool) -> None:
        for name, want in (("深度思考", think), ("智能搜索", search)):
            try:
                btn = page.get_by_text(name, exact=False).first.locator(TOGGLE_BUTTON_XPATH)
                pressed = btn.get_attribute("aria-pressed") == "true"
                if pressed != want:
                    btn.click()
                    page.wait_for_timeout(800)
                logger.info("网页模式 {} -> {}", name, want)
            except Exception as e:
                logger.warning("模式开关 {} 失败: {}", name, e)

    def _upload_images(self, page, images: list[str]) -> int:
        if not images:
            return 0
        paths: list[str] = []
        for url in images[:4]:
            try:
                paths.append(self._download(url))
            except Exception:
                logger.warning("图片下载失败,跳过: {}", url[:80])
        if not paths:
            return 0
        try:
            page.locator("input[type='file']").first.set_input_files(paths)
            page.wait_for_timeout(4000)
            return len(paths)
        except Exception:
            logger.warning("网页图片上传失败,转纯文本")
            return 0

    @staticmethod
    def _download(url: str) -> str:
        import httpx

        d = Path(gettempdir()) / "opencode" / "ds_uploads"
        d.mkdir(parents=True, exist_ok=True)
        suffix = ".jpg"
        low = url.lower()
        for ext in (".png", ".gif", ".webp", ".jpeg", ".bmp"):
            if ext in low:
                suffix = ".jpg" if ext == ".jpeg" else ext
                break
        target = d / f"{abs(hash(url)) % 10**10}{suffix}"
        if not target.exists():
            r = httpx.get(url, timeout=30, follow_redirects=True)
            r.raise_for_status()
            target.write_bytes(r.content)
        return str(target)

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
                stopping = any(self._visible(page, s) for s in STOP_SELECTORS)
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

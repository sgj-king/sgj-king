"""Playwright 小红书自动发布服务（最小可用骨架）

注意：小红书前端结构会频繁变化。这里的实现优先保证：
- 可以在失败时输出足够的诊断材料（截图/HTML）
- 发布队列可以稳定推进（成功/失败/可重试）

后续如果需要更高成功率，建议：
- 把关键 selector 抽到配置（或录制脚本）
- 引入“半自动确认模式”（用户确认最后一步点击发布）
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from playwright.async_api import async_playwright, Browser, BrowserContext, Page


@dataclass
class PublishResult:
    ok: bool
    note_id: Optional[str] = None
    note_url: Optional[str] = None
    error: Optional[str] = None
    debug_dir: Optional[str] = None


class XiaohongshuPublisher:
    def __init__(self, *, headless: bool = True, timeout_ms: int = 30000, debug_dir: str = "/tmp/redflow_publish"):
        self.headless = headless
        self.timeout_ms = timeout_ms
        self.debug_dir = debug_dir

        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._playwright = None

    async def __aenter__(self):
        await self.init()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def init(self):
        os.makedirs(self.debug_dir, exist_ok=True)

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

    async def _new_context_with_cookies(self, cookies: List[Dict]):
        if not self._browser:
            await self.init()

        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )

        if cookies:
            await self._context.add_cookies(cookies)

        self._page = await self._context.new_page()
        self._page.set_default_timeout(self.timeout_ms)

    async def close(self):
        try:
            if self._context:
                await self._context.close()
        finally:
            self._context = None

        try:
            if self._browser:
                await self._browser.close()
        finally:
            self._browser = None

        try:
            if self._playwright:
                await self._playwright.stop()
        finally:
            self._playwright = None

    async def _dump_debug(self, name: str) -> str:
        """保存截图与 HTML，返回本次 debug 子目录"""
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", name)[:60]
        out_dir = os.path.join(self.debug_dir, f"{ts}_{safe}")
        os.makedirs(out_dir, exist_ok=True)

        if self._page:
            try:
                await self._page.screenshot(path=os.path.join(out_dir, "page.png"), full_page=True)
            except Exception:
                pass
            try:
                html = await self._page.content()
                with open(os.path.join(out_dir, "page.html"), "w", encoding="utf-8") as f:
                    f.write(html)
            except Exception:
                pass

        return out_dir

    async def login_with_cookies(self, cookies: List[Dict]) -> Tuple[bool, Optional[str]]:
        await self._new_context_with_cookies(cookies)

        try:
            assert self._page
            await self._page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded")
            await self._page.wait_for_timeout(1500)

            is_logged_in = await self._page.evaluate(
                """() => {
                    return document.cookie.includes('web_session') || !!document.querySelector('[data-userid]');
                }"""
            )

            if not is_logged_in:
                debug_dir = await self._dump_debug("login_failed")
                return False, f"Cookie 登录失败（可能已失效/需要验证码）。debug={debug_dir}"

            return True, None

        except Exception as exc:
            debug_dir = await self._dump_debug("login_exception")
            return False, f"登录异常：{exc}. debug={debug_dir}"

    async def publish_note(self, *, cookies: List[Dict], title: str, body: str, tags: List[str] | None = None) -> PublishResult:
        """发布笔记（占位实现）

        说明：由于缺少你当前可用的发布页面/流程信息，这里先把框架搭好。
        接下来需要你提供：
        - 手动发布路径（从 explore 到发布页）
        - 发布页关键元素的截图或 HTML（用 debug 输出即可）

        我会据此补齐 selector，实现真正可用的自动发布。
        """

        ok, err = await self.login_with_cookies(cookies)
        if not ok:
            return PublishResult(ok=False, error=err)

        try:
            assert self._page

            # TODO: 这里需要根据实际页面实现：进入发布页 -> 填充内容 -> 上传图片 -> 添加话题 -> 点击发布
            # 先输出一份 debug，便于你提供页面结构。
            debug_dir = await self._dump_debug("before_publish_not_implemented")

            return PublishResult(
                ok=False,
                error="发布流程未实现：需要根据发布页 selector 补齐自动化步骤",
                debug_dir=debug_dir,
            )

        except Exception as exc:
            debug_dir = await self._dump_debug("publish_exception")
            return PublishResult(ok=False, error=f"发布异常：{exc}", debug_dir=debug_dir)

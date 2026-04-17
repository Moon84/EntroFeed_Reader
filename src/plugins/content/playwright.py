# -*- coding: utf-8 -*-
"""Playwright Content Retrieval Plugin for EntroFeed."""

import asyncio
from logging import getLogger
from typing import ClassVar, Optional

from playwright.async_api import Playwright, Route, async_playwright, Browser

from src.constants import USER_AGENT
from src.handlers import ContentRetrievalHandler
from src.plugins.content import ContentPluginBase, ContentPluginRegistry

logger = getLogger("uvicorn.error")

# Module-level browser instance for reuse
_browser: Optional[Browser] = None
_browser_lock = asyncio.Lock()


class PlaywrightContentRetriever(ContentPluginBase, ContentRetrievalHandler):
    id: ClassVar[str] = "playwright"

    @staticmethod
    async def _block_common_with_script(route: Route):
        excluded_resource_types = ["stylesheet", "image", "font"]
        if route.request.resource_type in excluded_resource_types:
            await route.abort()
        else:
            await route.continue_()

    @staticmethod
    async def _block_common(route: Route):
        excluded_resource_types = ["stylesheet", "image", "font", "script"]
        if route.request.resource_type in excluded_resource_types:
            await route.abort()
        else:
            await route.continue_()

    @staticmethod
    async def _get_browser() -> Browser:
        """Get or create a reusable browser instance."""
        global _browser
        async with _browser_lock:
            if _browser is None or not _browser.is_connected():
                logger.info("Launching new Playwright browser instance")
                pw = await async_playwright().start()
                _browser = await pw.chromium.launch()
                # Store playwright reference for cleanup
                _browser._playwright = pw
            return _browser

    @staticmethod
    async def _retrieve(url: str, use_script: bool = False) -> str:
        browser = await PlaywrightContentRetriever._get_browser()
        page = await browser.new_page(user_agent=USER_AGENT)

        try:
            retriever = (
                PlaywrightContentRetriever._block_common_with_script
                if use_script
                else PlaywrightContentRetriever._block_common
            )

            await page.route("**/*", retriever)
            await page.goto(url, wait_until="domcontentloaded")

            return await page.content()
        finally:
            await page.close()

    async def get_html(self, url: str, use_script: bool = False) -> str:
        return await self._retrieve(url=url, use_script=use_script)


ContentPluginRegistry.register(PlaywrightContentRetriever)

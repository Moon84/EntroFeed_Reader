# -*- coding: utf-8 -*-
"""RSSHub Content Retrieval Plugin for EntroFeed."""

import os
from logging import getLogger
from typing import ClassVar

import httpx

from src.constants import USER_AGENT
from src.handlers import ContentRetrievalHandler
from src.plugins.content import ContentPluginBase, ContentPluginRegistry

logger = getLogger("uvicorn.error")


class RSSHubContentRetriever(ContentPluginBase, ContentRetrievalHandler):
    id: ClassVar[str] = "rsshub"
    headers: ClassVar[dict] = {"User-Agent": USER_AGENT}

    def __init__(self):
        self.base_url = os.getenv("RSSHUB_HOST", "http://localhost:1200")

    async def get_html(self, url: str, use_script: bool = False) -> str:
        """Fetch HTML content via RSSHub render endpoint with fallback to direct fetch."""
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                # Try RSSHub render first
                render_url = f"{self.base_url}/render"
                params = {"url": url, "mode": "pc"}

                try:
                    response = await client.get(
                        render_url,
                        params=params,
                        headers=self.headers,
                    )

                    if response.status_code == 200 and response.text:
                        return response.text
                    logger.warning(f"RSSHub render failed for {url}: status={response.status_code}")
                except httpx.RequestError as rsshub_error:
                    logger.warning(f"RSSHub render error for {url}: {rsshub_error}")

                # Fallback: try direct fetch of the URL
                try:
                    response = await client.get(
                        url,
                        headers=self.headers,
                    )
                    if response.status_code == 200 and response.text:
                        return response.text
                except httpx.RequestError as direct_error:
                    logger.warning(f"Direct fetch failed for {url}: {direct_error}")

                return None
        except Exception as e:
            logger.warning(f"RSSHub content retrieval failed for {url}: {e}")
            return None

    async def is_available(self) -> bool:
        """Check if RSSHub is available."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/")
                return response.status_code == 200
        except Exception:
            return False


ContentPluginRegistry.register(RSSHubContentRetriever)

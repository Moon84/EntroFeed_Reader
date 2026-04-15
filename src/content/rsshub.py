# -*- coding: utf-8 -*-
"""RSSHub Content Retriever - Fetch content via RSSHub."""

import os
from typing import ClassVar

import requests

from src.constants import USER_AGENT
from src.handlers import ContentRetrievalHandler


class RSSHubContentRetriever(ContentRetrievalHandler):
    """Content retriever that uses RSSHub for JavaScript-rendered sites.

    RSSHub provides a unified API to fetch content from sites that require
    JavaScript rendering or have anti-bot measures.
    """

    id: ClassVar[str] = "rsshub"
    headers: ClassVar[dict] = {"User-Agent": USER_AGENT}

    def __init__(self):
        """Initialize RSSHub retriever."""
        self.base_url = os.getenv("RSSHUB_HOST", "http://localhost:1200")

    async def get_html(self, url: str, use_script: bool = False) -> str:
        """Fetch content via RSSHub render endpoint.

        Args:
            url: Target URL to fetch
            use_script: Whether to use JavaScript rendering (ignored, always uses RSSHub)

        Returns:
            HTML content of the page
        """
        try:
            # RSSHub render endpoint
            render_url = f"{self.base_url}/render"
            params = {"url": url, "mode": "pc"}  # pc mode for desktop view

            response = requests.get(
                render_url,
                params=params,
                headers=self.headers,
                timeout=30
            )

            if response.status_code == 200 and response.text:
                return response.text
            else:
                return None
        except Exception:
            return None

    def is_available(self) -> bool:
        """Check if RSSHub is available.

        Returns:
            True if RSSHub is reachable
        """
        try:
            response = requests.get(
                f"{self.base_url}/",
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False


__all__ = ["RSSHubContentRetriever"]

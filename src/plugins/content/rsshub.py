# -*- coding: utf-8 -*-
"""RSSHub Content Retrieval Plugin for EntroFeed."""

import os
from typing import ClassVar

import requests

from src.constants import USER_AGENT
from src.handlers import ContentRetrievalHandler
from src.plugins.content import ContentPluginBase, ContentPluginRegistry


class RSSHubContentRetriever(ContentPluginBase, ContentRetrievalHandler):
    id: ClassVar[str] = "rsshub"
    headers: ClassVar[dict] = {"User-Agent": USER_AGENT}

    def __init__(self):
        self.base_url = os.getenv("RSSHUB_HOST", "http://localhost:1200")

    async def get_html(self, url: str, use_script: bool = False) -> str:
        try:
            render_url = f"{self.base_url}/render"
            params = {"url": url, "mode": "pc"}

            response = requests.get(
                render_url,
                params=params,
                headers=self.headers,
                timeout=30
            )

            if response.status_code == 200 and response.text:
                return response.text
            return None
        except Exception:
            return None

    def is_available(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            return response.status_code == 200
        except Exception:
            return False


ContentPluginRegistry.register(RSSHubContentRetriever)

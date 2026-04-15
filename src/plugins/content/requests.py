# -*- coding: utf-8 -*-
"""Requests Content Retrieval Plugin for EntroFeed."""

import requests as req
from typing import ClassVar

from src.constants import USER_AGENT
from src.handlers import ContentRetrievalHandler
from src.plugins.content import ContentPluginBase, ContentPluginRegistry


class RequestsContentRetriever(ContentPluginBase, ContentRetrievalHandler):
    id: ClassVar[str] = "requests"
    headers: ClassVar[dict] = {"User-Agent": USER_AGENT}

    async def get_html(self, url: str, use_script: bool = False) -> str:
        try:
            page = req.get(url, headers=self.headers)
            if page.text == "":
                return None
            return page.text
        except Exception:
            return None


ContentPluginRegistry.register(RequestsContentRetriever)

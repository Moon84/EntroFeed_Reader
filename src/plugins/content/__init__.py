# -*- coding: utf-8 -*-
"""Content Retrieval Plugin module - Base class and registry for EntroFeed."""

from abc import abstractmethod
from typing import Callable, ClassVar

from src.handlers import ContentRetrievalHandler as OldContentRetrievalHandler
from src.kernel.registry import PluginBase, PluginRegistry
from src.models.feed import EntryContent, Feed, FeedEntry


class ContentPluginBase(PluginBase, OldContentRetrievalHandler):
    """Base class for all content retrieval plugins."""

    id: ClassVar[str] = "base_content"

    @classmethod
    def get_plugin_type(cls) -> str:
        """Return the plugin type string."""
        return "content"

    @abstractmethod
    async def get_html(self, url: str, use_script: bool) -> str:
        """Fetch HTML content from URL."""
        pass


class ContentPluginRegistry:
    """Registry for content retrieval plugins."""

    _handlers = {}

    @classmethod
    def register(cls, handler_cls: type) -> None:
        cls._handlers[handler_cls.id] = handler_cls
        PluginRegistry.register("content", handler_cls)

    @classmethod
    def list_handlers(cls) -> list:
        return list(cls._handlers.keys())

    @classmethod
    def get_handler(cls, handler_id: str):
        return cls._handlers.get(handler_id)


# Import all content plugins to trigger auto-registration
from src.plugins.content import requests, playwright, rsshub

# Re-export handler classes for convenient import
from src.plugins.content.playwright import PlaywrightContentRetriever
from src.plugins.content.requests import RequestsContentRetriever
from src.plugins.content.rsshub import RSSHubContentRetriever


__all__ = [
    "ContentPluginBase",
    "ContentPluginRegistry",
    "PlaywrightContentRetriever",
    "RequestsContentRetriever",
    "RSSHubContentRetriever",
]

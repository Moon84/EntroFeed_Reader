# -*- coding: utf-8 -*-
"""Null LLM Plugin for EntroFeed - no-op implementation."""

from typing import ClassVar

from src.handlers import LLMHandler
from src.models import Feed, FeedEntry
from src.plugins.llm import ModelWrapperBase, LLMPluginRegistry


class NullLLMHandler(ModelWrapperBase, LLMHandler):
    """Null handler that returns None."""

    id: ClassVar[str] = "null_llm"

    def chat(self, messages, **kwargs):
        """Return None."""
        return None

    def summarize(self, feed: Feed, entry: FeedEntry, mk: str) -> None:
        """Return None."""
        return None


# Auto-register on import
LLMPluginRegistry.register(NullLLMHandler)

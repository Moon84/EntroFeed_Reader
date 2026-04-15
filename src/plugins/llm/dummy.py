# -*- coding: utf-8 -*-
"""Dummy LLM Plugin for EntroFeed - for testing."""

from typing import ClassVar

from pydantic import Field

from src.handlers import LLMHandler
from src.models import Feed, FeedEntry
from src.plugins.llm import ModelWrapperBase, LLMPluginRegistry


class DummyLLMHandler(ModelWrapperBase, LLMHandler):
    """Dummy handler that returns "cool story bro"."""

    id: ClassVar[str] = "dummy_llm"
    temerity: int = Field(default=5)

    def chat(self, messages, **kwargs):
        """Return dummy response."""
        return "cool story bro"

    def summarize(self, feed: Feed, entry: FeedEntry, mk: str) -> str:
        """Return dummy summary."""
        return "cool story bro"


# Auto-register on import
LLMPluginRegistry.register(DummyLLMHandler)

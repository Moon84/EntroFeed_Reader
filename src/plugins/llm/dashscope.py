# -*- coding: utf-8 -*-
"""DashScope LLM Plugin for EntroFeed - Alibaba's Qwen models."""

import os
from typing import Any, ClassVar, List, Dict, Optional

from openai import OpenAI
from pydantic import Field

from src.handlers import LLMHandler
from src.models import Feed, FeedEntry
from src.plugins.llm import ModelWrapperBase, LLMPluginRegistry


class DashScopeLLMHandler(ModelWrapperBase, LLMHandler):
    """DashScope handler for Alibaba Qwen models."""

    model: str = Field(default="qwen-plus")
    api_key: Optional[str] = Field(default=None)
    base_url: str = Field(default="https://dashscope.aliyuncs.com/compatible-mode/v1")
    system: Optional[str] = Field(default=None)
    temperature: float = Field(default=0.2)
    max_tokens: int = Field(default=4000)

    id: ClassVar[str] = "dashscope"

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Make chat completion call to DashScope."""
        api_key = self.api_key or os.getenv("DASHSCOPE_API_KEY")

        if not api_key:
            raise ValueError("DASHSCOPE_API_KEY not set")

        client = OpenAI(api_key=api_key, base_url=self.base_url)

        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            **kwargs
        )

        return response.choices[0].message.content

    def summarize(self, feed: Feed, entry: FeedEntry, mk: str) -> str:
        """Summarize content using DashScope."""
        system = self.system if self.system else self.summarization_system_prompt
        return self._make_chat_call(
            system=system,
            prompt=self.get_summarization_prompt(mk)
        )


class DashScopeVisionHandler(ModelWrapperBase, LLMHandler):
    """DashScope handler for vision models (Qwen-VL)."""

    model: str = Field(default="qwen-vl-max")
    api_key: Optional[str] = Field(default=None)
    base_url: str = Field(default="https://dashscope.aliyuncs.com/compatible-mode/v1")

    id: ClassVar[str] = "dashscope_vision"

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Make chat completion call to DashScope vision model."""
        api_key = self.api_key or os.getenv("DASHSCOPE_API_KEY")

        if not api_key:
            raise ValueError("DASHSCOPE_API_KEY not set")

        client = OpenAI(api_key=api_key, base_url=self.base_url)

        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            **kwargs
        )

        return response.choices[0].message.content

    def summarize(self, feed: Feed, entry: FeedEntry, mk: str) -> str:
        """Summarize/describe image using DashScope vision model."""
        return self.chat([
            {"role": "user", "content": [
                {"type": "text", "text": self.get_summarization_prompt(mk)}
            ]}
        ])


# Auto-register on import
LLMPluginRegistry.register(DashScopeLLMHandler)
LLMPluginRegistry.register(DashScopeVisionHandler)

# -*- coding: utf-8 -*-
"""DashScope LLM Handler - Alibaba's Qwen models via DashScope API."""

import os
from typing import Any, ClassVar, Mapping, Optional

from openai import OpenAI
from pydantic import BaseModel

from src.handlers import LLMHandler
from src.models import Feed, FeedEntry


class DashScopeLLMHandler(LLMHandler, BaseModel):
    """DashScope handler for Alibaba Qwen models."""

    model: str = "qwen-plus"
    api_key: Optional[str] = None
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    system: str = None
    temperature: float = 0.2
    max_tokens: int = 4000

    id: ClassVar[str] = "dashscope"

    def _make_chat_call(self, system: str, prompt: str) -> str:
        """Make chat completion call to DashScope."""
        api_key = self.api_key or os.getenv("DASHSCOPE_API_KEY")

        if not api_key:
            raise ValueError("DASHSCOPE_API_KEY not set")

        client = OpenAI(
            api_key=api_key,
            base_url=self.base_url,
        )

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        return response.choices[0].message.content

    def summarize(self, feed: Feed, entry: FeedEntry, mk: str) -> str:
        """Summarize content using DashScope."""
        system = self.system if self.system else self.summarization_system_prompt
        return self._make_chat_call(
            system=system, prompt=self.get_summarization_prompt(mk)
        )


class DashScopeVisionHandler(LLMHandler, BaseModel):
    """DashScope handler for vision models (Qwen-VL)."""

    model: str = "qwen-vl-max"
    api_key: Optional[str] = None
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    id: ClassVar[str] = "dashscope_vision"

    def summarize(self, feed: Feed, entry: FeedEntry, mk: str) -> str:
        """Summarize/describe image using DashScope vision model."""
        api_key = self.api_key or os.getenv("DASHSCOPE_API_KEY")

        if not api_key:
            raise ValueError("DASHSCOPE_API_KEY not set")

        client = OpenAI(
            api_key=api_key,
            base_url=self.base_url,
        )

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "user", "content": [
                    {"type": "text", "text": self.get_summarization_prompt(mk)}
                ]}
            ],
        )

        return response.choices[0].message.content


__all__ = ["DashScopeLLMHandler", "DashScopeVisionHandler"]

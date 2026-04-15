# -*- coding: utf-8 -*-
"""OpenAI LLM Plugin for EntroFeed."""

from typing import ClassVar, List, Dict

from openai import OpenAI
from pydantic import Field

from src.handlers import LLMHandler
from src.models import Feed, FeedEntry
from src.plugins.llm import ModelWrapperBase, LLMPluginRegistry


class OpenAILLMHandler(ModelWrapperBase, LLMHandler):
    """OpenAI handler for GPT models."""

    api_key: str = Field(default="")
    model: str = Field(default="gpt-4o-mini")

    id: ClassVar[str] = "openai"

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Make chat completion call to OpenAI."""
        client = OpenAI(api_key=self.api_key)

        completion = client.chat.completions.create(
            messages=messages,
            model=self.model,
            **kwargs
        )

        return completion.choices[0].message.content

    def summarize(self, feed: Feed, entry: FeedEntry, mk: str) -> str:
        """Summarize content using OpenAI."""
        return self._make_chat_call(
            system=self.summarization_system_prompt,
            prompt=self.get_summarization_prompt(mk)
        )


# Auto-register on import
LLMPluginRegistry.register(OpenAILLMHandler)

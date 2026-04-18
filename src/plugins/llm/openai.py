# -*- coding: utf-8 -*-
"""OpenAI LLM Plugin for EntroFeed."""

import time
from typing import ClassVar, Dict, List

from openai import OpenAI
from pydantic import Field

from src.handlers import LLMHandler
from src.metrics import record_llm_request, record_token_usage
from src.models.feed import Feed, FeedEntry
from src.plugins.llm import ModelWrapperBase, LLMPluginRegistry


class OpenAILLMHandler(ModelWrapperBase, LLMHandler):
    """OpenAI handler for GPT models."""

    api_key: str = Field(default="")
    model: str = Field(default="gpt-4o-mini")

    id: ClassVar[str] = "openai"
    required_env: ClassVar[List[str]] = ["OPENAI_API_KEY"]

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Make chat completion call to OpenAI."""
        client = OpenAI(api_key=self.api_key)

        start_time = time.time()
        try:
            completion = client.chat.completions.create(
                messages=messages, model=self.model, **kwargs
            )

            # Record metrics
            usage = completion.usage
            if usage:
                record_token_usage(
                    self.model, usage.prompt_tokens, usage.completion_tokens
                )
            record_llm_request(self.id, self.model, True, time.time() - start_time)

            content = completion.choices[0].message.content
            return content if content is not None else ""
        except Exception:
            record_llm_request(self.id, self.model, False, time.time() - start_time)
            raise

    def summarize(self, feed: Feed, entry: FeedEntry, mk: str) -> str:
        """Summarize content using OpenAI."""
        return self._make_chat_call(
            system=self.summarization_system_prompt,
            prompt=self.get_summarization_prompt(mk),
        )


# Auto-register on import
LLMPluginRegistry.register(OpenAILLMHandler)

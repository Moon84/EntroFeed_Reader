# -*- coding: utf-8 -*-
"""ByteDance Doubao (字节豆包) LLM Plugin for EntroFeed."""

from typing import ClassVar, Dict, List

from openai import OpenAI
from pydantic import Field

from src.handlers import LLMHandler
from src.metrics import record_llm_request, record_token_usage
from src.models.feed import Feed, FeedEntry
from src.plugins.llm import ModelWrapperBase, LLMPluginRegistry


class ByteDanceLLMHandler(ModelWrapperBase, LLMHandler):
    """ByteDance Doubao handler for Doubao models."""

    api_key: str = Field(default="")
    model: str = Field(default="Doubao-pro-32k")
    base_url: str = Field(default="https://ark.cn-beijing.volces.com/api/v3")

    id: ClassVar[str] = "bytedance"
    required_env: ClassVar[List[str]] = ["BYTEDANCE_API_KEY"]

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Make chat completion call to ByteDance Doubao."""
        client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

        start_time = self._last_call_start = self._get_time()
        try:
            completion = client.chat.completions.create(
                messages=messages, model=self.model, **kwargs
            )

            # Extract usage info for metrics
            usage = completion.usage
            input_tokens = getattr(usage, "prompt_tokens", 0)
            output_tokens = getattr(usage, "completion_tokens", 0)

            if input_tokens or output_tokens:
                record_token_usage(self.model, input_tokens, output_tokens)

            duration = self._get_time() - start_time
            record_llm_request(self.id, self.model, True, duration)

            content = completion.choices[0].message.content
            return content if content is not None else ""
        except Exception:
            duration = self._get_time() - start_time
            record_llm_request(self.id, self.model, False, duration)
            raise

    def summarize(self, feed: Feed, entry: FeedEntry, mk: str) -> str:
        """Summarize content using ByteDance Doubao."""
        return self._make_chat_call(
            system=self.summarization_system_prompt,
            prompt=self.get_summarization_prompt(mk),
        )

    def _get_time(self) -> float:
        """Get current time for metrics."""
        import time

        return time.time()


# Auto-register on import
LLMPluginRegistry.register(ByteDanceLLMHandler)

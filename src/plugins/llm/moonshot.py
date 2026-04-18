# -*- coding: utf-8 -*-
"""Moonshot (月之暗面/Kimi) LLM Plugin for EntroFeed."""

from typing import ClassVar, Dict, List

from openai import OpenAI
from pydantic import Field

from src.handlers import LLMHandler
from src.metrics import record_llm_request, record_token_usage
from src.models.feed import Feed, FeedEntry
from src.plugins.llm import ModelWrapperBase, LLMPluginRegistry


class MoonshotLLMHandler(ModelWrapperBase, LLMHandler):
    """Moonshot/Kimi handler for Kimi models."""

    api_key: str = Field(default="")
    model: str = Field(default="moonshot-v1-128k")
    base_url: str = Field(default="https://api.moonshot.cn/v1")

    id: ClassVar[str] = "moonshot"
    required_env: ClassVar[List[str]] = ["MOONSHOT_API_KEY"]

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Make chat completion call to Moonshot/Kimi."""
        client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

        start_time = self._last_call_start = self._get_time()
        try:
            completion = client.chat.completions.create(
                messages=messages,
                model=self.model,
                **kwargs
            )
            
            # Extract usage info for metrics
            usage = completion.usage
            input_tokens = getattr(usage, "prompt_tokens", 0)
            output_tokens = getattr(usage, "completion_tokens", 0)
            
            if input_tokens or output_tokens:
                record_token_usage(self.model, input_tokens, output_tokens)
            
            duration = self._get_time() - start_time
            record_llm_request(self.id, self.model, True, duration)
            
            return completion.choices[0].message.content
        except Exception:
            duration = self._get_time() - start_time
            record_llm_request(self.id, self.model, False, duration)
            raise

    def summarize(self, feed: Feed, entry: FeedEntry, mk: str) -> str:
        """Summarize content using Moonshot/Kimi."""
        return self._make_chat_call(
            system=self.summarization_system_prompt,
            prompt=self.get_summarization_prompt(mk)
        )

    def _get_time(self) -> float:
        """Get current time for metrics."""
        import time
        return time.time()


# Auto-register on import
LLMPluginRegistry.register(MoonshotLLMHandler)

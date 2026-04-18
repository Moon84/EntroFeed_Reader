# -*- coding: utf-8 -*-
"""DashScope LLM Plugin for EntroFeed - Alibaba's Qwen models."""

import os
import time
from typing import Any, ClassVar, Dict, List, Optional

from openai import OpenAI
from pydantic import Field

from src.handlers import LLMHandler
from src.metrics import record_llm_request, record_token_usage
from src.models.feed import Feed, FeedEntry
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
    required_env: ClassVar[List[str]] = ["DASHSCOPE_API_KEY"]

    @classmethod
    def _check_api_connectivity(cls) -> bool:
        """Check if DashScope API is reachable."""
        import requests

        try:
            resp = requests.get(
                "https://dashscope.aliyuncs.com/compatible-mode/v1/models",
                timeout=5,
                headers={
                    "Authorization": f"Bearer {os.getenv('DASHSCOPE_API_KEY', '')}"
                },
            )
            return resp.status_code in (200, 401)
        except requests.RequestException:
            return False

    _check_fn: ClassVar = _check_api_connectivity

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Make chat completion call to DashScope."""
        api_key = self.api_key or os.getenv("DASHSCOPE_API_KEY")

        if not api_key:
            raise ValueError("DASHSCOPE_API_KEY not set")

        client = OpenAI(api_key=api_key, base_url=self.base_url)

        start_time = time.time()
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                **kwargs,
            )

            # Record metrics
            usage = response.usage
            if usage:
                record_token_usage(
                    self.model, usage.prompt_tokens, usage.completion_tokens
                )
            record_llm_request(self.id, self.model, True, time.time() - start_time)

            content = response.choices[0].message.content
            return content if content is not None else ""
        except Exception:
            record_llm_request(self.id, self.model, False, time.time() - start_time)
            raise

    def summarize(self, feed: Feed, entry: FeedEntry, mk: str) -> str:
        """Summarize content using DashScope."""
        system = self.system if self.system else self.summarization_system_prompt
        return self._make_chat_call(
            system=system, prompt=self.get_summarization_prompt(mk)
        )

    def chat_with_tools(
        self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]], **kwargs
    ) -> Dict[str, Any]:
        """Chat with function calling support for DashScope."""
        api_key = self.api_key or os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            raise ValueError("DASHSCOPE_API_KEY not set")

        client = OpenAI(api_key=api_key, base_url=self.base_url)

        # Convert tools to DashScope format
        dashscope_tools = []
        for tool in tools:
            func = tool.get("function", {})
            dashscope_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": func.get("name"),
                        "description": func.get("description"),
                        "parameters": func.get(
                            "parameters", {"type": "object", "properties": {}}
                        ),
                    },
                }
            )

        start_time = time.time()
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=dashscope_tools,
                tool_choice="auto",
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                **kwargs,
            )

            # Record metrics
            usage = response.usage
            if usage:
                record_token_usage(
                    self.model, usage.prompt_tokens, usage.completion_tokens
                )
            record_llm_request(self.id, self.model, True, time.time() - start_time)

            message = response.choices[0].message
            result: Dict[str, Any] = {"content": message.content or ""}

            if message.tool_calls:
                result["tool_calls"] = [
                    {
                        "id": tc.id,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ]

            return result
        except Exception:
            record_llm_request(self.id, self.model, False, time.time() - start_time)
            raise


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

        start_time = time.time()
        try:
            response = client.chat.completions.create(
                model=self.model, messages=messages, **kwargs
            )

            # Record metrics
            usage = response.usage
            if usage:
                record_token_usage(
                    self.model, usage.prompt_tokens, usage.completion_tokens
                )
            record_llm_request(self.id, self.model, True, time.time() - start_time)

            content = response.choices[0].message.content
            return content if content is not None else ""
        except Exception:
            record_llm_request(self.id, self.model, False, time.time() - start_time)
            raise

    def summarize(self, feed: Feed, entry: FeedEntry, mk: str) -> str:
        """Summarize/describe image using DashScope vision model."""
        return self.chat(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.get_summarization_prompt(mk)}
                    ],
                }
            ]
        )


# Auto-register on import
LLMPluginRegistry.register(DashScopeLLMHandler)
LLMPluginRegistry.register(DashScopeVisionHandler)

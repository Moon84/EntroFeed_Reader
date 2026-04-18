# -*- coding: utf-8 -*-
"""Ollama LLM Plugin for EntroFeed."""

import time
from typing import Any, ClassVar, Dict, List, Mapping

from ollama import ChatResponse, Client, Message, Options
from pydantic import Field

from src.handlers import LLMHandler
from src.metrics import record_llm_request
from src.models.feed import Feed, FeedEntry
from src.plugins.llm import ModelWrapperBase, LLMPluginRegistry


class OllamaLLMHandler(ModelWrapperBase, LLMHandler):
    """Ollama handler for local LLM models."""

    base_url: str = Field(default="http://localhost:11434")
    model: str = Field(default="llama3")
    system: str = Field(default=None)
    options: Mapping[str, Any] = Field(default_factory=lambda: {"temperature": 0.2})

    id: ClassVar[str] = "ollama"
    required_env: ClassVar[List[str]] = []  # Ollama is local, no API key needed

    @classmethod
    def _check_ollama_running(cls) -> bool:
        """Check if Ollama server is running."""
        import requests
        try:
            resp = requests.get("http://localhost:11434/api/tags", timeout=3)
            return resp.status_code == 200
        except requests.RequestException:
            return False

    _check_fn: ClassVar = _check_ollama_running

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Make chat completion call to Ollama."""
        client = Client(host=self.base_url)

        ollama_messages = [Message(role=m["role"], content=m["content"]) for m in messages]

        start_time = time.time()
        try:
            response: ChatResponse = client.chat(
                model=self.model,
                messages=ollama_messages,
                options=Options(**self.options),
                **kwargs
            )

            record_llm_request(self.id, self.model, True, time.time() - start_time)
            return response["message"]["content"]
        except Exception:
            record_llm_request(self.id, self.model, False, time.time() - start_time)
            raise

    def summarize(self, feed: Feed, entry: FeedEntry, mk: str) -> str:
        """Summarize content using Ollama."""
        system = self.system if self.system else self.summarization_system_prompt
        return self._make_chat_call(
            system=system,
            prompt=self.get_summarization_prompt(mk)
        )


# Auto-register on import
LLMPluginRegistry.register(OllamaLLMHandler)

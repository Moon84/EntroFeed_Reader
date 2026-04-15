# -*- coding: utf-8 -*-
"""Ollama LLM Plugin for EntroFeed."""

from typing import Any, ClassVar, List, Dict, Mapping

from ollama import ChatResponse, Client, Message, Options
from pydantic import Field

from src.handlers import LLMHandler
from src.models import Feed, FeedEntry
from src.plugins.llm import ModelWrapperBase, LLMPluginRegistry


class OllamaLLMHandler(ModelWrapperBase, LLMHandler):
    """Ollama handler for local LLM models."""

    base_url: str = Field(default="http://localhost:11434")
    model: str = Field(default="llama3")
    system: str = Field(default=None)
    options: Mapping[str, Any] = Field(default_factory=lambda: {"temperature": 0.2})

    id: ClassVar[str] = "ollama"

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Make chat completion call to Ollama."""
        client = Client(host=self.base_url)

        ollama_messages = [Message(role=m["role"], content=m["content"]) for m in messages]

        response: ChatResponse = client.chat(
            model=self.model,
            messages=ollama_messages,
            options=Options(**self.options),
            **kwargs
        )

        return response["message"]["content"]

    def summarize(self, feed: Feed, entry: FeedEntry, mk: str) -> str:
        """Summarize content using Ollama."""
        system = self.system if self.system else self.summarization_system_prompt
        return self._make_chat_call(
            system=system,
            prompt=self.get_summarization_prompt(mk)
        )


# Auto-register on import
LLMPluginRegistry.register(OllamaLLMHandler)

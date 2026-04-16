# -*- coding: utf-8 -*-
"""LLM Plugin module - Model wrapper base and registry for EntroFeed."""

import os
from abc import abstractmethod
from typing import Any, ClassVar, Dict, List, Optional, Type

from pydantic import BaseModel

from src.kernel.registry import PluginBase, PluginRegistry
from src.models.feed import Feed, FeedEntry


class ModelWrapperBase(PluginBase):
    """Base class for all LLM providers."""

    id: ClassVar[str] = "base_llm"

    @classmethod
    def get_plugin_type(cls) -> str:
        """Return the plugin type string."""
        return "llm"

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        pass

    @abstractmethod
    def summarize(self, feed: Feed, entry: FeedEntry, mk: str) -> str:
        pass

    def _make_chat_call(self, system: str, prompt: str, **kwargs) -> str:
        return self.chat([
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ], **kwargs)

    def chat_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        **kwargs
    ) -> Dict[str, Any]:
        """Chat with function calling support.

        Args:
            messages: List of message dicts with role and content
            tools: List of tool definitions in OpenAI format
            **kwargs: Additional arguments

        Returns:
            Dict with 'content' (str) and optionally 'tool_calls' list
        """
        raise NotImplementedError("Subclass must implement chat_with_tools")

    def get_summarization_prompt(self, mk: str) -> str:
        return f"Summarize this article:\n\n{mk}"

    @property
    def summarization_system_prompt(self) -> str:
        return """Your goal is to write a brief but detailed summary of the text given to you.
Only output the summary without any headings or sections.
Provide the summary in markdown."""


class LLMPluginRegistry:
    """Registry for LLM plugins with auto-registration."""

    _handlers: Dict[str, Type[ModelWrapperBase]] = {}
    _provider_defaults: Dict[str, Dict[str, Any]] = {
        "dashscope": {
            "model": "qwen-plus",
            "api_key": os.getenv("DASHSCOPE_API_KEY"),
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "temperature": 0.2,
            "max_tokens": 4000,
        },
        "ollama": {
            "model": os.getenv("OLLAMA_MODEL", "llama3"),
            "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            "options": {"temperature": 0.2},
        },
        "openai": {
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "api_key": os.getenv("OPENAI_API_KEY", ""),
        },
    }
    _provider_aliases: Dict[str, str] = {
        "dummy": "dummy_llm",
        "null": "null_llm",
    }

    @classmethod
    def register(cls, handler_cls: Type[ModelWrapperBase]) -> None:
        cls._handlers[handler_cls.id] = handler_cls
        PluginRegistry.register("llm", handler_cls)

    @classmethod
    def get_handler(cls, handler_id: str) -> Optional[Type[ModelWrapperBase]]:
        return cls._handlers.get(handler_id)

    @classmethod
    def list_handlers(cls) -> List[str]:
        return list(cls._handlers.keys())

    @classmethod
    def create(
        cls,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> ModelWrapperBase:
        provider = provider or os.getenv("DEFAULT_LLM_PROVIDER", "dashscope")
        
        # Resolve aliases
        handler_id = cls._provider_aliases.get(provider, provider)
        handler_cls = cls._handlers.get(handler_id)
        
        if not handler_cls:
            raise ValueError(f"Unknown LLM provider: {provider}")

        defaults = cls._provider_defaults.get(handler_id, {})
        config = {**defaults, **kwargs}
        if model:
            config["model"] = model

        return handler_cls(**config)


def create_llm_handler(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs
) -> ModelWrapperBase:
    return LLMPluginRegistry.create(provider=provider, model=model, **kwargs)


def get_default_provider() -> str:
    return os.getenv("DEFAULT_LLM_PROVIDER", "dashscope")


# Import all plugins to trigger auto-registration
from src.plugins.llm import openai, ollama, dashscope, dummy, null


__all__ = [
    "ModelWrapperBase",
    "LLMPluginRegistry",
    "create_llm_handler",
    "get_default_provider",
]

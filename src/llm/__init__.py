# -*- coding: utf-8 -*-
"""LLM module - Unified LLM interface for EntroFeed.

This module re-exports from the new plugins/llm/ location for backward compatibility.
New code should import from src.plugins.llm directly.
"""

# Re-export from new location
from src.plugins.llm import (
    ModelWrapperBase,
    LLMPluginRegistry,
    create_llm_handler,
    get_default_provider,
)

# Re-export handler classes for direct import compatibility
from src.plugins.llm.openai import OpenAILLMHandler
from src.plugins.llm.ollama import OllamaLLMHandler
from src.plugins.llm.dashscope import DashScopeLLMHandler, DashScopeVisionHandler
from src.plugins.llm.dummy import DummyLLMHandler
from src.plugins.llm.null import NullLLMHandler

__all__ = [
    # Core exports
    "create_llm_handler",
    "get_default_provider",
    "ModelWrapperBase",
    "LLMPluginRegistry",
    # Handler classes
    "OpenAILLMHandler",
    "OllamaLLMHandler",
    "DashScopeLLMHandler",
    "DashScopeVisionHandler",
    "DummyLLMHandler",
    "NullLLMHandler",
]

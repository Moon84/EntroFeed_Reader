# -*- coding: utf-8 -*-
"""Tests for LLM Plugins and Registry."""

import pytest
import os

from src.plugins.llm import (
    ModelCapability,
    ModelInfo,
    ModelCatalog,
    MODEL_CATALOG,
    LLMPluginRegistry,
    create_llm_handler,
    get_default_provider,
    get_all_models,
    get_provider_models,
)


class TestModelCapability:
    """Test ModelCapability enum."""

    def test_capabilities_exist(self):
        """Test all capabilities are defined."""
        assert ModelCapability.TEXT == "text"
        assert ModelCapability.REASONING == "reasoning"
        assert ModelCapability.VISION == "vision"
        assert ModelCapability.IMAGE_GENERATION == "image_gen"
        assert ModelCapability.FUNCTION_CALLING == "func_call"
        assert ModelCapability.CODE == "code"
        assert ModelCapability.LONG_CONTEXT == "long_ctx"


class TestModelInfo:
    """Test ModelInfo model."""

    def test_create_model_info(self):
        """Test creating ModelInfo."""
        model = ModelInfo(
            name="test-model",
            display_name="Test Model",
            provider="test",
            capabilities=[ModelCapability.TEXT],
        )
        assert model.name == "test-model"
        assert model.provider == "test"
        assert ModelCapability.TEXT in model.capabilities


class TestModelCatalog:
    """Test ModelCatalog."""

    def test_get_all_models(self):
        """Test getting all models."""
        models = MODEL_CATALOG.get_all_models()
        assert len(models) > 0
        assert all(isinstance(m, ModelInfo) for m in models)

    def test_get_model_info(self):
        """Test getting model info by provider and name."""
        info = MODEL_CATALOG.get_model_info("dashscope", "qwen-plus")
        assert info is not None
        assert info.name == "qwen-plus"
        assert info.provider == "dashscope"

    def test_get_model_info_not_found(self):
        """Test getting non-existent model returns None."""
        info = MODEL_CATALOG.get_model_info("unknown", "unknown-model")
        assert info is None

    def test_get_models_by_provider(self):
        """Test getting models by provider."""
        models = MODEL_CATALOG.get_models_by_provider("openai")
        assert len(models) > 0
        assert all(m.provider == "openai" for m in models)

    def test_get_models_by_capability(self):
        """Test getting models by capability."""
        models = MODEL_CATALOG.get_models_by_capability(ModelCapability.VISION)
        assert len(models) > 0
        assert all(ModelCapability.VISION in m.capabilities for m in models)

    def test_get_text_models(self):
        """Test getting text models."""
        models = MODEL_CATALOG.get_text_models()
        assert len(models) > 0
        assert all(ModelCapability.TEXT in m.capabilities for m in models)

    def test_get_vision_models(self):
        """Test getting vision models."""
        models = MODEL_CATALOG.get_vision_models()
        assert len(models) > 0
        assert all(ModelCapability.VISION in m.capabilities for m in models)

    def test_get_reasoning_models(self):
        """Test getting reasoning models."""
        models = MODEL_CATALOG.get_reasoning_models()
        assert len(models) > 0
        assert all(ModelCapability.REASONING in m.capabilities for m in models)


class TestLLMPluginRegistry:
    """Test LLMPluginRegistry."""

    def test_list_handlers(self):
        """Test listing handlers."""
        handlers = LLMPluginRegistry.list_handlers()
        assert "dashscope" in handlers
        assert "openai" in handlers
        assert "ollama" in handlers
        assert "dummy_llm" in handlers
        assert "null_llm" in handlers

    def test_get_handler(self):
        """Test getting handler by ID."""
        handler = LLMPluginRegistry.get_handler("dummy_llm")
        assert handler is not None

    def test_get_handler_not_found(self):
        """Test getting non-existent handler returns None."""
        handler = LLMPluginRegistry.get_handler("nonexistent")
        assert handler is None

    def test_provider_defaults_exist(self):
        """Test provider defaults are configured."""
        defaults = LLMPluginRegistry._provider_defaults
        assert "dashscope" in defaults
        assert "openai" in defaults
        assert "ollama" in defaults

    def test_provider_aliases_exist(self):
        """Test provider aliases are configured."""
        aliases = LLMPluginRegistry._provider_aliases
        assert "qwen" in aliases
        assert "aliyun" in aliases


class TestLLMHelperFunctions:
    """Test LLM helper functions."""

    def test_get_default_provider(self):
        """Test getting default provider."""
        provider = get_default_provider()
        assert isinstance(provider, str)
        assert len(provider) > 0

    def test_get_all_models(self):
        """Test getting all models."""
        models = get_all_models()
        assert len(models) > 0

    def test_get_provider_models(self):
        """Test getting models by provider."""
        models = get_provider_models("dashscope")
        assert len(models) > 0
        assert all(m.provider == "dashscope" for m in models)


class TestDummyLLMHandler:
    """Test Dummy LLM handler."""

    def test_dummy_handler_exists(self):
        """Test dummy handler is registered."""
        handler_cls = LLMPluginRegistry.get_handler("dummy_llm")
        assert handler_cls is not None

    def test_dummy_handler_id(self):
        """Test dummy handler ID."""
        handler_cls = LLMPluginRegistry.get_handler("dummy_llm")
        assert handler_cls.id == "dummy_llm"


class TestNullLLMHandler:
    """Test Null LLM handler."""

    def test_null_handler_exists(self):
        """Test null handler is registered."""
        handler_cls = LLMPluginRegistry.get_handler("null_llm")
        assert handler_cls is not None

    def test_null_handler_id(self):
        """Test null handler ID."""
        handler_cls = LLMPluginRegistry.get_handler("null_llm")
        assert handler_cls.id == "null_llm"

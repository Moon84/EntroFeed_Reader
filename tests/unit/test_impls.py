import os
import pytest
import tempfile
from pathlib import Path

from src.kernel.registry import PluginRegistry
from src.plugins.storage.handler import StorageHandler


def test_plugin_registry_singleton():
    """Test that PluginRegistry properly registers all plugin types."""
    plugin_types = PluginRegistry.list_plugin_types()
    assert "llm" in plugin_types
    assert "notification" in plugin_types
    assert "content" in plugin_types
    assert "storage" in plugin_types


def test_llm_plugins_registered():
    """Test that LLM plugins are registered."""
    llm_plugins = PluginRegistry.list_plugins("llm")
    assert len(llm_plugins) > 0
    # Known LLM handler IDs should be registered
    assert "dummy_llm" in llm_plugins or any("dummy" in k.lower() for k in llm_plugins)


def test_storage_plugins_registered():
    """Test that storage plugins are registered."""
    storage_plugins = PluginRegistry.list_plugins("storage")
    assert len(storage_plugins) > 0
    assert "sqlite" in storage_plugins


def test_load_storage_config():
    """Test that load_storage_config works with proper environment."""
    # Skip this test - it requires full storage initialization
    # which needs a writable data directory. This is an integration test.
    pytest.skip("Integration test - requires writable data directory")

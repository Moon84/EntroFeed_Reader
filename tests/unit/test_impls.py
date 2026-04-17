import pytest

from src.kernel.registry import PluginRegistry, load_storage_config
from src.plugins.storage.handler import StorageHandler


def test_plugin_registry_singleton():
    """Test that PluginRegistry properly registers all plugin types."""
    plugin_types = PluginRegistry.list_plugin_types()
    assert "llm" in plugin_types
    assert "notification" in plugin_types
    assert "content" in plugin_types
    assert "storage" in plugin_types


def test_llm_plugins_registered():
    """Test that LLM plugins are registered after loading storage config."""
    # load_storage_config triggers all plugin registrations as a side effect
    load_storage_config()
    llm_plugins = PluginRegistry.list_plugins("llm")
    assert len(llm_plugins) > 0
    # Known LLM handler IDs should be registered
    assert "dummy_llm" in llm_plugins or any(
        "dummy" in k.lower() for k in llm_plugins
    )


def test_storage_plugins_registered():
    """Test that storage plugins are registered after loading storage config."""
    # load_storage_config triggers all plugin registrations as a side effect
    load_storage_config()
    storage_plugins = PluginRegistry.list_plugins("storage")
    assert len(storage_plugins) > 0
    assert "sqlite" in storage_plugins


def test_load_storage_config():
    """Test that load_storage_config returns a valid StorageHandler."""
    db = load_storage_config()
    assert isinstance(db, StorageHandler)

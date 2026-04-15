# -*- coding: utf-8 -*-
"""Plugin registry for EntroFeed.

Provides a centralized registry for all plugin types:
- llm: LLM providers (OpenAI, Ollama, DashScope, etc.)
- notification: Notification channels (Slack, Matrix, etc.)
- content: Content retrieval (Requests, Playwright, RSSHub)
- storage: Storage backends (TinyDB, SQLite, LMDB)
"""

from typing import Any, Callable, ClassVar, Dict, Optional, Type

from pydantic import BaseModel


class PluginBase(BaseModel):
    """Base class for all plugins."""

    id: ClassVar[str] = "base_plugin"

    @classmethod
    def get_plugin_type(cls) -> str:
        """Return the plugin type string."""
        raise NotImplementedError

    @classmethod
    def get_plugin_id(cls) -> str:
        """Return the unique plugin identifier."""
        return cls.id


class PluginRegistry:
    """Singleton registry for all plugins.

    Provides centralized plugin registration and instantiation.
    Plugins self-register on import via their module's __init__.py.
    """

    _plugins: ClassVar[Dict[str, Dict[str, Type[PluginBase]]]] = {
        "llm": {},
        "notification": {},
        "content": {},
        "storage": {},
    }

    _factories: ClassVar[Dict[str, Callable]] = {}

    @classmethod
    def register(
        cls, plugin_type: str, plugin_cls: Type[PluginBase], *, factory: Optional[Callable] = None
    ) -> None:
        """Register a plugin class.

        Args:
            plugin_type: Category (llm, notification, content, storage)
            plugin_cls: Plugin class inheriting from PluginBase
            factory: Optional factory function for instantiation
        """
        if plugin_type not in cls._plugins:
            cls._plugins[plugin_type] = {}
        
        # Get plugin ID - support both PluginBase subclasses and plain classes
        plugin_id = getattr(plugin_cls, 'id', None)
        if plugin_id is None:
            # Fallback: use class name lowercased
            plugin_id = plugin_cls.__name__.lower().replace('handler', '').replace('storage', '')
        
        cls._plugins[plugin_type][plugin_id] = plugin_cls
        if factory:
            cls._factories[f"{plugin_type}:{plugin_id}"] = factory

    @classmethod
    def get_plugin_cls(cls, plugin_type: str, plugin_id: str) -> Optional[Type[PluginBase]]:
        """Get a plugin class by type and ID."""
        return cls._plugins.get(plugin_type, {}).get(plugin_id)

    @classmethod
    def list_plugins(cls, plugin_type: str) -> Dict[str, Type[PluginBase]]:
        """List all plugins of a given type."""
        return cls._plugins.get(plugin_type, {}).copy()

    @classmethod
    def list_plugin_types(cls) -> list:
        """List all available plugin types."""
        return list(cls._plugins.keys())

    @classmethod
    def create(cls, plugin_type: str, plugin_id: str, **config) -> PluginBase:
        """Create a plugin instance by type and ID."""
        plugin_cls = cls.get_plugin_cls(plugin_type, plugin_id)
        if not plugin_cls:
            raise ValueError(f"Unknown plugin: {plugin_type}:{plugin_id}")

        factory_key = f"{plugin_type}:{plugin_id}"
        if factory_key in cls._factories:
            return cls._factories[factory_key](**config)

        return plugin_cls(**config)

    @classmethod
    def has_plugin(cls, plugin_type: str, plugin_id: str) -> bool:
        """Check if a plugin is registered."""
        return cls.get_plugin_cls(plugin_type, plugin_id) is not None


# Convenience accessors for each plugin type
def get_llm_plugins() -> Dict[str, Type[PluginBase]]:
    return PluginRegistry.list_plugins("llm")


def get_notification_plugins() -> Dict[str, Type[PluginBase]]:
    return PluginRegistry.list_plugins("notification")


def get_content_plugins() -> Dict[str, Type[PluginBase]]:
    return PluginRegistry.list_plugins("content")


def get_storage_plugins() -> Dict[str, Type[PluginBase]]:
    return PluginRegistry.list_plugins("storage")

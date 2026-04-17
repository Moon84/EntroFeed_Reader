# -*- coding: utf-8 -*-
"""Storage Plugin module - Base class and registry for EntroFeed."""

from typing import ClassVar, Dict, Type

from src.kernel.registry import PluginBase, PluginRegistry


class StoragePluginBase(PluginBase):
    """Base class for storage plugins."""

    id: ClassVar[str] = "base_storage"

    @classmethod
    def get_plugin_type(cls) -> str:
        """Return the plugin type string."""
        return "storage"


class StoragePluginRegistry:
    """Registry for storage plugins."""

    _handlers: Dict[str, Type] = {}

    @classmethod
    def register(cls, handler_cls: Type) -> None:
        cls._handlers[handler_cls.id] = handler_cls
        PluginRegistry.register("storage", handler_cls)

    @classmethod
    def list_handlers(cls) -> list:
        return list(cls._handlers.keys())

    @classmethod
    def get_handler(cls, handler_id: str) -> Type:
        return cls._handlers.get(handler_id)


# Import SQLite storage handler and register it
from src.storage.sqlite_storage import SQLiteStorageHandler

SQLiteStorageHandler.id = "sqlite"

# Register storage handler with the plugin registry
StoragePluginRegistry.register(SQLiteStorageHandler)


# Re-export StorageHandler for backward compatibility
from src.plugins.storage.handler import StorageHandler


__all__ = [
    "StoragePluginBase",
    "StoragePluginRegistry",
    "StorageHandler",
]
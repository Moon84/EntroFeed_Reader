# -*- coding: utf-8 -*-
"""Handler implementations registry for EntroFeed.

This module provides backward compatibility by maintaining the handler maps
while gradually migrating to the new PluginRegistry system.
"""

from logging import getLogger
from os import environ
from typing import Type, Union

from src.db import StorageHandler
from src.kernel.registry import PluginRegistry
from src.storage.hybrid import HybridLMDBOfflineStorageHandler
from src.storage.lmdb import LMDBStorageHandler
from src.storage.tinydb import TinyDBStorageHandler
from src.storage.sqlite_storage import SQLiteStorageHandler

logger = getLogger("uvicorn.error")

# Import LLM handlers from new plugins location for registration
from src.llm import (
    DashScopeLLMHandler,
    DashScopeVisionHandler,
    DummyLLMHandler,
    NullLLMHandler,
    OllamaLLMHandler,
    OpenAILLMHandler,
)

# Import notification handlers from plugins
from src.plugins.notification import (
    SlackNotificationHandler,
    MatrixNotificationHandler,
    JiraNotificationHandler,
    NtfyNotificationHandler,
    NullNotificationHandler,
)

# Import content handlers from plugins
from src.plugins.content import (
    PlaywrightContentRetriever,
    RequestsContentRetriever,
    RSSHubContentRetriever,
)

storage_handlers = {
    "tinydb": TinyDBStorageHandler,
    "lmdb": LMDBStorageHandler,
    "hybrid": HybridLMDBOfflineStorageHandler,
    "sqlite": SQLiteStorageHandler,
}

notification_handlers = {
    "matrix": MatrixNotificationHandler,
    "null_notification": NullNotificationHandler,
    "slack": SlackNotificationHandler,
    "jira": JiraNotificationHandler,
    "ntfy": NtfyNotificationHandler,
}

content_retrieval_handlers = {
    "requests": RequestsContentRetriever,
    "playwright": PlaywrightContentRetriever,
    "rsshub": RSSHubContentRetriever,
}

llm_handlers = {
    NullLLMHandler.id: NullLLMHandler,
    OllamaLLMHandler.id: OllamaLLMHandler,
    OpenAILLMHandler.id: OpenAILLMHandler,
    DashScopeLLMHandler.id: DashScopeLLMHandler,
    DashScopeVisionHandler.id: DashScopeVisionHandler,
    DummyLLMHandler.id: DummyLLMHandler,
    # redirect null summarization handler to null llm
    "null_summarization": NullLLMHandler,
}


class ImplMixin:
    """Mixin that provides handler maps for storage handler."""

    handler_map = {
        **llm_handlers,
        **notification_handlers,
        **content_retrieval_handlers,
    }

    engine_map = {
        "llm": llm_handlers,
        "notification": notification_handlers,
        "content": content_retrieval_handlers,
    }

    handler_type_map = {
        **{k: "llm" for k in llm_handlers.keys()},
        **{k: "notification" for k in notification_handlers.keys()},
        **{k: "content" for k in content_retrieval_handlers.keys()},
    }


def _register_plugins() -> None:
    """Register all plugins with the global PluginRegistry."""
    # Register notification handlers
    for handler_cls in notification_handlers.values():
        PluginRegistry.register("notification", handler_cls)

    # Register content retrieval handlers
    for handler_cls in content_retrieval_handlers.values():
        PluginRegistry.register("content", handler_cls)

    # Register storage handlers
    for handler_cls in storage_handlers.values():
        PluginRegistry.register("storage", handler_cls)


# Register plugins on module import
_register_plugins()


def load_storage_config() -> Type[Union[Type[StorageHandler], ImplMixin],]:
    config_type = environ.get("ENTROFEED_STORAGE_HANDLER", "tinydb")
    handler_type = storage_handlers.get(config_type)
    handler = handler_type()

    # for the purpose of managing settings, the db handler needs to know about
    # implementations of other handlers. Here, we modify the signature of the chosen
    # handler to include the other handler impls. Doing it this way avoids creating a
    # circular dependency
    handler_cls_name = handler.__class__.__name__
    handler.__class__ = type(handler_cls_name, (handler_type, ImplMixin), {})

    logger.info(f"loading storage handler of type {config_type}")

    return handler

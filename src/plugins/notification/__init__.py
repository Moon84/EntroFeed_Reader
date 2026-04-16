# -*- coding: utf-8 -*-
"""Notification Plugin module - Base class and registry for EntroFeed."""

from abc import abstractmethod
from typing import ClassVar, List, Optional

from src.handlers import NotificationHandler as OldNotificationHandler
from src.kernel.registry import PluginBase, PluginRegistry
from src.models.feed import Feed, FeedEntry


class NotificationPluginBase(PluginBase, OldNotificationHandler):
    """Base class for all notification plugins.

    Inherits from both PluginBase and the backward-compatible NotificationHandler.
    """

    id: ClassVar[str] = "base_notification"

    @classmethod
    def get_plugin_type(cls) -> str:
        """Return the plugin type string."""
        return "notification"

    @property
    def destinations(self) -> List[str]:
        """List available notification destinations."""
        return []

    async def login(self) -> None:
        """Authenticate with the notification service."""
        pass

    async def logout(self) -> None:
        """Disconnect from the notification service."""
        pass

    @abstractmethod
    async def send_notification(self, feed: Feed, entry: FeedEntry) -> None:
        """Send notification for an entry."""
        pass


class NotificationPluginRegistry:
    """Registry for notification plugins."""

    _handlers: dict = {}

    @classmethod
    def register(cls, handler_cls: type) -> None:
        cls._handlers[handler_cls.id] = handler_cls
        PluginRegistry.register("notification", handler_cls)

    @classmethod
    def list_handlers(cls) -> List[str]:
        return list(cls._handlers.keys())

    @classmethod
    def get_handler(cls, handler_id: str) -> Optional[type]:
        return cls._handlers.get(handler_id)


# Import all notification plugins to trigger auto-registration
from src.plugins.notification import slack, ntfy, null

# Re-export handler classes for convenient import
from src.plugins.notification.slack import SlackNotificationHandler
from src.plugins.notification.ntfy import NtfyNotificationHandler
from src.plugins.notification.null import NullNotificationHandler


__all__ = [
    "NotificationPluginBase",
    "NotificationPluginRegistry",
    "SlackNotificationHandler",
    "NtfyNotificationHandler",
    "NullNotificationHandler",
]

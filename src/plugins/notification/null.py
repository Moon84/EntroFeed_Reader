# -*- coding: utf-8 -*-
"""Null Notification Plugin for EntroFeed - no-op implementation."""

from typing import ClassVar

from src.handlers import NotificationHandler
from src.models import Feed, FeedEntry
from src.plugins.notification import NotificationPluginBase, NotificationPluginRegistry


class NullNotificationHandler(NotificationPluginBase, NotificationHandler):
    id: ClassVar[str] = "null_notification"

    async def send_notification(self, feed: Feed, entry: FeedEntry) -> None:
        return None


NotificationPluginRegistry.register(NullNotificationHandler)

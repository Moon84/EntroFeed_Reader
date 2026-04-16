# -*- coding: utf-8 -*-
"""Ntfy Notification Plugin for EntroFeed."""

from json import dumps
from logging import getLogger
from os import environ
from typing import ClassVar, Optional

import requests
from pydantic import Field

from src.handlers import NotificationHandler
from src.models.feed import Feed, FeedEntry
from src.plugins.notification import NotificationPluginBase, NotificationPluginRegistry

logger = getLogger("uvicorn.error")


class NtfyNotificationHandler(NotificationPluginBase, NotificationHandler):
    """Ntfy.sh notification handler.

    Configure either via environment variables or via the PluginHealth UI.
    """

    id: ClassVar[str] = "ntfy"
    required_env: ClassVar[list] = ["NTFY_TOPIC"]
    root_url: str = Field(
        default_factory=lambda: environ.get("NTFY_ROOT_URL", "https://ntfy.sh/"),
        description="Ntfy server URL (NTFY_ROOT_URL env var)",
    )
    topic: str = Field(
        default_factory=lambda: environ.get("NTFY_TOPIC") or "",
        description="Default ntfy topic name",
    )

    async def send_notification(self, feed: Feed, entry: FeedEntry) -> None:
        if not self.topic:
            logger.warning("NTFY_TOPIC not configured, skipping notification")
            return

        topic = feed.notify_destination or self.topic

        headers = {
            "title": f"{feed.name}: {entry.title}",
            "tags": "newspaper",
            "click": self.make_read_link(entry),
        }

        actions = [
            {"action": "view", "label": "Read in EntroFeed", "url": self.make_read_link(entry)},
            {"action": "view", "label": "View Original", "url": entry.url},
        ]

        message = f"{feed.name} - {entry.title}"

        data = {"topic": topic, **headers, "message": message, "actions": actions}

        logger.debug(f"ntfy request: {data}")

        req = requests.post(url=self.root_url, data=dumps(data))

        logger.debug(f"ntfy response: {req.text}: {req.reason}")


NotificationPluginRegistry.register(NtfyNotificationHandler)

# -*- coding: utf-8 -*-
"""Slack Notification Plugin for EntroFeed."""

from logging import getLogger
from os import environ
from typing import ClassVar, Optional

from pydantic import Field
from slack_sdk.web.async_client import AsyncWebClient

from src.handlers import NotificationHandler
from src.models.feed import Feed, FeedEntry
from src.plugins.notification import NotificationPluginBase, NotificationPluginRegistry

logger = getLogger("uvicorn.error")


class SlackNotificationHandler(NotificationPluginBase, NotificationHandler):
    """Slack notification handler.

    Configure either via environment variables or via the PluginHealth UI.
    """

    id: ClassVar[str] = "slack"
    required_env: ClassVar[list] = ["SLACK_API_TOKEN"]
    token: str = Field(
        description="Slack API token (SLACK_API_TOKEN env var) *",
    )
    channel_name: str = Field(
        default="",
        description="Default Slack channel name (without # prefix)",
    )

    @staticmethod
    def _escape_title(title: str) -> str:
        translation_table = {"&": "&amp;", "<": "&lt;", ">": "&gt;"}
        return "".join(translation_table.get(c, c) for c in title)

    async def send_notification(self, feed: Feed, entry: FeedEntry):
        if not self.token:
            logger.warning("SLACK_API_TOKEN not configured, skipping notification")
            return

        client = AsyncWebClient(token=self.token)
        title = self._escape_title(entry.title)

        msg = f"{feed.name}: <{self.make_read_link(entry)}|{title}>"

        channel = feed.notify_destination or self.channel_name or "general"
        logger.info(f"Sending Slack notification to channel: {channel}")

        await client.chat_postMessage(channel=channel, text=msg, mrkdwn=True)


NotificationPluginRegistry.register(SlackNotificationHandler)

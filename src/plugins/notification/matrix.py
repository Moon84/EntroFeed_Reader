# -*- coding: utf-8 -*-
"""Matrix Notification Plugin for EntroFeed."""

from logging import getLogger
from os import environ
from typing import ClassVar, Mapping

from pydantic import BaseModel, Field
from simplematrixbotlib import Bot, Creds

from src.handlers import NotificationHandler
from src.models import Feed, FeedEntry
from src.plugins.notification import NotificationPluginBase, NotificationPluginRegistry

logger = getLogger("uvicorn.error")


class MatrixNotificationHandler(NotificationPluginBase, NotificationHandler, BaseModel):
    id: ClassVar[str] = "matrix"
    homeserver: str = Field(default="https://matrix.org")
    room_id: str = Field(default="")
    username: str = Field(default="")
    password: str = Field(default="")
    routing: Mapping[str, str] = Field(default_factory=dict)

    _bot: Bot = None

    @property
    def bot(self) -> Bot:
        if not self._bot:
            self._bot = Bot(
                creds=Creds(
                    homeserver=self.homeserver,
                    username=self.username,
                    password=self.password,
                )
            )
        return self._bot

    @property
    def default_room(self) -> str:
        return self.room_id

    async def login(self) -> None:
        await self.bot.api.login()

    async def logout(self) -> None:
        await self.bot.api.async_client.logout()

    async def send_notification(self, feed: Feed, entry: FeedEntry) -> None:
        msg = f"{feed.name}: [{entry.title}]({self.make_read_link(entry)})"

        if feed.notify_destination:
            room = self.routing.get(feed.notify_destination, self.default_room)
            logger.info(f"Sending notification to {feed.notify_destination} - {room}")
        else:
            room = self.default_room
            logger.info(f"Sending notification to default {room}")

        await self.bot.api.send_markdown_message(room_id=room, message=msg)


NotificationPluginRegistry.register(MatrixNotificationHandler)

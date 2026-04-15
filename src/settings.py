from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.handlers import ContentRetrievalHandler, LLMHandler, NotificationHandler


class Themes(str, Enum):
    black = "black"
    coffee = "coffee"
    dark = "dark"
    fantasy = "fantasy"
    forest = "forest"
    lemonade = "lemonade"
    lofi = "lofi"
    luxury = "luxury"
    night = "night"
    nord = "nord"
    pastel = "pastel"
    synthwave = "synthwave"
    winter = "winter"


class GlobalSettings(BaseModel):

    send_notification: bool = True
    theme: Themes = Themes.forest
    refresh_interval: int = 5
    reading_speed: int = 238

    notification_handler_key: str = "null_notification"
    llm_handler_key: str = "null_llm"
    content_retrieval_handler_key: str = "playwright"
    recent_hours: int = 36

    finished_onboarding: bool = False

    db: Any = Field(exclude=True)

    @field_validator("db", mode="before")
    @classmethod
    def validate_db(cls, val):
        from src.db import StorageHandler

        if isinstance(val, type) and issubclass(val, StorageHandler):
            return val
        if issubclass(type(val), StorageHandler):
            return val

        raise TypeError("Wrong type for db, must be subclass of StorageHandler")

    @property
    def notification_handler(self) -> NotificationHandler:
        try:
            config = self.db.get_handler(id=self.notification_handler_key)
            if isinstance(config, dict):
                return self.db.handler_map[self.notification_handler_key](**config)
            elif config:
                return config
        except (IndexError, ValueError):
            pass
        return self.db.handler_map["null_notification"]()

    @property
    def llm_handler(self) -> LLMHandler:
        try:
            config = self.db.get_handler(id=self.llm_handler_key)
            if isinstance(config, dict):
                return self.db.handler_map[self.llm_handler_key](**config)
            elif config:
                return config
        except (IndexError, ValueError):
            pass
        return self.db.handler_map["null_llm"]()

    @property
    def content_retrieval_handler(self) -> ContentRetrievalHandler:
        try:
            config = self.db.get_handler(id=self.content_retrieval_handler_key)
            if isinstance(config, dict):
                return self.db.handler_map[self.content_retrieval_handler_key](**config)
            elif config:
                return config
        except (IndexError, ValueError):
            pass
        return self.db.handler_map["playwright"]()

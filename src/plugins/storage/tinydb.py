# -*- coding: utf-8 -*-
"""TinyDB Storage Plugin for EntroFeed."""

from logging import getLogger
from pathlib import Path
from typing import List, Mapping, Optional, Type

from tinydb import Query, TinyDB

from src.constants import DATA_DIR
from src.db import StorageHandler
from src.models import EntryContent, Feed, FeedEntry
from src.settings import GlobalSettings
from src.plugins.storage import StoragePluginBase, StoragePluginRegistry

logger = getLogger("uvicorn.error")


class TinyDBStorageHandler(StoragePluginBase, StorageHandler):
    id: str = "tinydb"

    def __init__(self):
        super().__init__()

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        db_path = Path(DATA_DIR, "db.json").resolve()
        self.db = TinyDB(db_path)

    def clear_active_feeds(self) -> None:
        self.db.drop_table("feeds")

    def upsert_feed(self, feed: Feed) -> None:
        feeds = self.db.table("feeds")
        query = Query()
        existing = feeds.search(query.id == feed.id)
        if existing:
            feeds.update(feed.model_dump(), query.id == feed.id)
        else:
            feeds.insert(feed.model_dump())

    def insert_feed(self, feed: Feed) -> None:
        feeds = self.db.table("feeds")
        query = Query()
        existing = feeds.search(query.id == feed.id)
        if existing:
            raise ValueError(f"Feed with ID {feed.id} already exists")
        feeds.insert(feed.model_dump())

    def get_feed(self, id: str) -> Feed:
        feeds = self.db.table("feeds")
        query = Query()
        result = feeds.search(query.id == id)
        if not result:
            raise ValueError(f"Feed with ID {id} not found")
        return Feed(**result[0])

    def get_feeds(self) -> List[Feed]:
        feeds = self.db.table("feeds")
        return [Feed(**f) for f in feeds.all()]

    def upsert_feed_entry(self, feed: Feed, entry: FeedEntry) -> None:
        entries = self.db.table("entries")
        query = Query()
        existing = entries.search(query.id == entry.id)
        if existing:
            entries.update(entry.model_dump(), query.id == entry.id)
        else:
            entries.insert(entry.model_dump())

    def get_feed_entry(self, id: str) -> Optional[FeedEntry]:
        entries = self.db.table("entries")
        query = Query()
        result = entries.search(query.id == id)
        if not result:
            return None
        return FeedEntry(**result[0])

    def upsert_entry_content(self, content: EntryContent) -> None:
        content_table = self.db.table("content")
        query = Query()
        existing = content_table.search(query.url == content.url)
        if existing:
            content_table.update(content.model_dump(), query.url == content.url)
        else:
            content_table.insert(content.model_dump())

    def upsert_settings(self, settings: GlobalSettings) -> None:
        settings_table = self.db.table("settings")
        settings_table.truncate()
        settings_table.insert(settings.model_dump())

    def get_settings(self) -> GlobalSettings:
        settings_table = self.db.table("settings")
        all_settings = settings_table.all()
        if not all_settings:
            return GlobalSettings()
        return GlobalSettings(**all_settings[0])

    def upsert_handler(self, handler) -> None:
        handlers = self.db.table("handlers")
        handler_type = getattr(handler, 'id', handler.__class__.__name__.lower())
        handlers.insert({"type": handler_type, "config": handler.model_dump_json()})

    def get_handler(self, id: str):
        handlers = self.db.table("handlers")
        query = Query()
        result = handlers.search(query.type == id)
        if not result:
            return None
        from src.llm import create_llm_handler
        import json
        config = json.loads(result[0]["config"])
        return create_llm_handler(provider=id, **config)

    def get_handlers(self) -> List:
        handlers = self.db.table("handlers")
        return handlers.all()

    def delete_feed(self, feed_id: str) -> None:
        feeds = self.db.table("feeds")
        entries = self.db.table("entries")
        query = Query()
        feeds.remove(query.id == feed_id)
        entries.remove(query.feed_id == feed_id)

    def get_entries(self, feed: Feed) -> List[FeedEntry]:
        entries = self.db.table("entries")
        query = Query()
        results = entries.search(query.feed_id == feed.id)
        return [FeedEntry(**e) for e in results]

    def feed_entry_exists(self, id: str) -> bool:
        entries = self.db.table("entries")
        query = Query()
        return bool(entries.search(query.id == id))

    def entry_content_exists(self, url: str) -> bool:
        content_table = self.db.table("content")
        query = Query()
        return bool(content_table.search(query.url == url))

    def retrieve_entry_content(self, url: str) -> Optional[EntryContent]:
        content_table = self.db.table("content")
        query = Query()
        results = content_table.search(query.url == url)
        if not results:
            return None
        return EntryContent(**results[0])

    def get_poll_state(self, feed_id: str) -> Optional[Mapping]:
        poll_table = self.db.table("poll_state")
        query = Query()
        results = poll_table.search(query.feed_id == feed_id)
        if not results:
            return None
        return results[0]

    def set_feed_start_ts(self, feed_id: str, start_ts: int) -> None:
        poll_table = self.db.table("poll_state")
        query = Query()
        poll_table.upsert(
            {"feed_id": feed_id, "start_ts": start_ts},
            query.feed_id == feed_id
        )

    def get_feed_start_ts(self, feed_id: str) -> int:
        state = self.get_poll_state(feed_id)
        return state.get("start_ts", 0) if state else 0

    def update_poll_state(self, feed_id: str, **kwargs) -> None:
        poll_table = self.db.table("poll_state")
        query = Query()
        existing = poll_table.search(query.feed_id == feed_id)
        if existing:
            poll_table.update(kwargs, query.feed_id == feed_id)
        else:
            poll_table.insert({"feed_id": feed_id, **kwargs})


StoragePluginRegistry.register(TinyDBStorageHandler)

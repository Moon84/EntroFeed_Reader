from __future__ import annotations

from importlib.metadata import version
from json import dumps, loads
from logging import getLogger
from sys import version as py_version
from time import localtime, strftime, time
from typing import List, Mapping, Optional, Type

from pydantic import BaseModel
from textstat import textstat as txt

from src.constants import GITHUB_LINK, IS_DOCKER
from src.errors import InvalidFeedException
from src.models import EntryContent, Feed, FeedEntry, HealthCheck
from src.settings import GlobalSettings

logger = getLogger("uvicorn.error")


class EntroFeedBackend:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def _format_time(time: int) -> str:
        # Return ISO 8601 format with timezone for proper client-side formatting
        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(time, tz=timezone.utc)
        return dt.isoformat()

    async def health_check(self):
        return HealthCheck()

    async def about(self):
        return {
            "version": version("entrofeed"),
            "python_version": py_version,
            "fastapi_version": version("fastapi"),
            "docker": IS_DOCKER,
            "storage_handler": type(self.db).__name__,
            "github": GITHUB_LINK,
        }

    def list_feeds(self, agg=False):
        feeds = self.db.get_feeds()
        entry_list = self.db.get_entries() or []
        entries: List[FeedEntry] = [i["entry"] for i in entry_list]

        if agg:
            entry_agg = {}

            for entry in entries:
                if entry.feed_id in entry_agg:
                    entry_agg[entry.feed_id] += 1
                else:
                    entry_agg[entry.feed_id] = 1

        return [
            {
                "id": feed.id,
                "name": feed.name,
                "category": feed.category,
                "type": feed.type,
                "url": feed.url,
                "preview_only": feed.preview_only,
                "notify": feed.notify,
                "refresh_enabled": feed.refresh_enabled,
                "entry_count": entry_agg.get(feed.id, 0) if agg else False,
            }
            for feed in feeds
        ]

    def list_entries(
        self, feed_id: Feed = None, time: float = time(), recent: bool = False
    ):
        if feed_id:
            feed = self.db.get_feed(id=feed_id)
        else:
            feed = None

        settings: GlobalSettings = self.db.get_settings()
        start_time = time - (settings.recent_hours * 3600)

        if recent:
            entries = self.db.get_entries(feed, after=start_time)
        else:
            entries = self.db.get_entries(feed=feed)

        for entry in entries:
            feed_entry: FeedEntry = entry["entry"]
            if not feed:
                local_feed: Feed = self.db.get_feed(entry["feed_id"])

            yield {
                "feed_name": feed.name if feed else local_feed.name,
                "title": feed_entry.title,
                "url": feed_entry.url,
                "published_at": self._format_time(feed_entry.published_at),
                "updated_at": self._format_time(feed_entry.updated_at),
                "sort_time": feed_entry.published_at,
                "preview": feed_entry.preview,
                "id": entry["id"],
                "feed_id": entry["feed_id"],
                "total_score": feed_entry.total_score,
                "recency_score": feed_entry.recency_score,
                "authority_score": feed_entry.authority_score,
                "relevance_score": feed_entry.relevance_score,
                "impact_score": feed_entry.impact_score,
                "tags": feed_entry.tags,
                "matched_interests": feed_entry.matched_interests,
                "has_ontology_match": feed_entry.has_ontology_match,
                "is_read": feed_entry.is_read,
                "liked": feed_entry.liked,
                "is_favorite": feed_entry.is_favorite,
            }

    async def get_entry_content(self, feed_entry_id, redrive: bool = False):
        entry: FeedEntry = self.db.get_feed_entry(id=feed_entry_id)
        feed: Feed = self.db.get_feed(entry.feed_id)
        settings: GlobalSettings = self.db.get_settings()

        base = {
            "id": feed_entry_id,
            "feed_id": entry.feed_id,
            "feed_name": feed.name,
            "title": entry.title,
            "url": entry.url,
            "published_at": self._format_time(entry.published_at),
            "updated_at": self._format_time(entry.updated_at),
            "byline": ", ".join(entry.authors) if entry.authors else None,
        }

        if feed.preview_only:
            return {**base, "preview": entry.preview, "content": None, "summary": None}
        else:
            content: EntryContent = await self.db.get_entry_content(
                entry=entry, redrive=redrive
            )
            logger.debug(f"Received EntryContent: {content}")
            txt_content = content.content if content.content else ""
            word_count = txt.lexicon_count(txt_content)
            result = {
                **base,
                "unretrievable": content.unretrievable,
                "banned": content.banned,
                "preview": None,
                "content": content.content,
                "summary": content.summary,
                "word_count": word_count,
                "reading_level": int(txt.text_standard(txt_content, float_output=True)),
                "reading_time": int(word_count / settings.reading_speed),
            }

            # Trigger ontology read event to update user interests
            try:
                from src.ontology import get_ontology_registry
                ontology = get_ontology_registry()
                # Calculate content priority from tags if available
                content_priority = 0
                profile = ontology.memory.get_content_profile(feed_entry_id)
                if profile:
                    content_priority = profile.priority
                ontology.on_content_read(feed_entry_id, content_priority=content_priority)
            except Exception as e:
                logger.debug(f"Ontology read event failed: {e}")

            return result

    def update_entry_state(
        self,
        entry_id: str,
        is_read: Optional[bool] = None,
        liked: Optional[int] = None,
        is_favorite: Optional[bool] = None,
    ):
        """Update entry read/like/favorite state in database."""
        self.db.update_feed_entry_state(
            entry_id=entry_id,
            is_read=is_read,
            liked=liked,
            is_favorite=is_favorite,
        )

    def get_handlers(self):
        handlers = self.db.get_handlers()

        return [
            {
                "type": k,
                "handler_type": self.db.handler_type_map[k],
                "config": v.model_dump() if v else None,
            }
            for k, v in handlers.items()
        ]

    def get_handler_config(self, handler: str):
        try:
            handler = self.db.get_handler(id=handler)
            return {"type": handler.id, "config": dumps(handler.model_dump(), indent=4)}

        except IndexError:
            return {"type": handler, "config": None}

    def get_handler_schema(self, handler: str):
        handler_obj: Type[BaseModel] = self.db.handler_map.get(handler)

        return dumps(handler_obj.model_json_schema(), indent=4)

    async def get_settings(self):
        settings: GlobalSettings = self.db.get_settings()

        return settings.model_dump()

    async def get_feed_config(self, id: str) -> Mapping:
        feed: Feed = self.db.get_feed(id=id)

        return {"id": feed.id, **feed.model_dump()}

    async def update_feed(self, feed: Feed):
        if not feed.validate():
            logger.info("feed is invalid!")
            raise InvalidFeedException(
                (
                    f"Feed {feed.name} does not have any entries at url {feed.url}. "
                    "Press back to return to the feed you configured"
                )
            )

        self.db.upsert_feed(feed=feed)
        settings = self.db.get_settings()

        if not settings.finished_onboarding:
            settings.finished_onboarding = True
            self.db.upsert_settings(settings=settings)

    async def update_settings(self, settings: GlobalSettings):
        self.db.upsert_settings(settings=settings)

    async def update_handler(self, handler: str, config: str):
        config_dict = loads(config)
        handler_obj = self.db.reconfigure_handler(id=handler, config=config_dict)
        self.db.upsert_handler(handler=handler_obj)

    async def delete_feed(self, feed_id: str):
        feed = self.db.get_feed(id=feed_id)

        entries = self.db.get_entries(feed=feed)
        for entry_dict in entries:
            entry: FeedEntry = entry_dict.get("entry")
            self.db.delete_feed_entry(feed_entry=entry)

        self.db.delete_feed(feed=feed)

    @staticmethod
    async def list_content_handler_choices():
        from src.impls import content_retrieval_handlers

        return list(content_retrieval_handlers.keys())

    @staticmethod
    async def list_llm_handler_choices():
        from src.impls import llm_handlers

        return list(llm_handlers.keys())

    @staticmethod
    async def list_notification_handler_choices():
        from src.impls import notification_handlers

        return list(notification_handlers.keys())

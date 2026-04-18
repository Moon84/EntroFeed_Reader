from calendar import timegm
from datetime import datetime, timezone
from json import dump, load
from logging import getLogger
from pathlib import Path
from re import sub as re_sub
from tempfile import SpooledTemporaryFile
from typing import List, Mapping, Dict, Any, Optional

from opml import OpmlDocument, OpmlOutline
from ruamel.yaml import YAML

from src.constants import CONFIG_DIR, DATA_DIR
from src.models.feed import EntryContent, Feed, FeedEntry
from src.settings import GlobalSettings

logger = getLogger("uvicorn.error")


def _score_and_tag_entry(
    entry_data: Dict[str, Any],
    feed_entry: Optional[FeedEntry] = None,
    feed: Optional[Feed] = None
) -> Dict[str, Any]:
    """
    为条目评分和打标签（统一流程）

    流程：
    1. 打标签 - 先提取文章标签
    2. 保存 ContentProfile 到 OntologyRegistry
    3. 评分 - 使用提取的标签计算图传播分数

    Args:
        entry_data: 条目数据
        feed_entry: FeedEntry 对象（可选，用于通过 ontology registry 处理）
        feed: Feed 对象（可选）

    Returns:
        添加了评分和标签的条目数据
    """
    try:
        from src.services.ontology.priority_scorer import get_priority_scorer, get_article_tagger
        from src.services.ontology import get_ontology_registry

        scorer = get_priority_scorer()
        tagger = get_article_tagger()

        # 获取用户兴趣用于匹配
        user_interests = scorer._get_user_interests_from_registry()

        # Step 1: 打标签 - 先提取文章标签
        tags_result = tagger.tag_article(entry_data, user_interests)
        extracted_tags = tags_result.get("tags", [])

        # Step 2: 将标签加入 entry_data，用于后续评分
        entry_data_with_tags = {**entry_data, "tags": extracted_tags}

        # Step 3: 保存 ContentProfile 到 OntologyRegistry（用于后续兴趣更新）
        if feed_entry is not None and feed is not None:
            try:
                ontology = get_ontology_registry()
                # 创建 ContentProfile 用于存储
                from src.services.ontology.types import ContentProfile, TagSource
                profile_tags = []
                for t in extracted_tags:
                    if isinstance(t, dict):
                        from src.services.ontology.types import InterestCategory, UnifiedNode
                        cat_str = t.get("category", "other")
                        try:
                            cat = InterestCategory(cat_str)
                        except ValueError:
                            cat = InterestCategory.OTHER
                        profile_tags.append(UnifiedNode(
                            name=t.get("name", ""),
                            category=cat,
                            confidence=t.get("confidence", 0.5),
                            source=TagSource.RSS if t.get("is_rss_tag") else TagSource.RULE,
                            is_interest=False,
                        ))
                profile = ContentProfile(
                    entry_id=feed_entry.id,
                    tags=profile_tags,
                    summary=entry_data.get("summary", "")[:500],
                )
                ontology.memory.save_content_profile(profile)
                logger.debug(f"Ontology profile saved for entry: {profile.entry_id}")
            except Exception as ontology_error:
                logger.warning(f"Failed to save ontology profile: {ontology_error}")

        # Step 4: 评分 - 使用提取的标签计算各项分数
        scores = scorer.score_article(entry_data_with_tags, user_interests)

        # 合并结果
        return {
            **entry_data,
            "total_score": scores.get("total_score", 0),
            "recency_score": scores.get("recency_score", 0),
            "authority_score": scores.get("authority_score", 0),
            "relevance_score": scores.get("relevance_score", 0),
            "impact_score": scores.get("impact_score", 0),
            "tags": extracted_tags,
            "matched_interests": tags_result.get("matched_interests", []),
            "has_ontology_match": tags_result.get("has_ontology_match", False),
        }
    except Exception as e:
        logger.warning(f"Failed to score/tag entry: {e}")
        return entry_data


def _get_entry_time(entry: Mapping) -> int:
    """Get entry timestamp, falling back to updated_parsed or current time."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return timegm(entry.published_parsed)
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        return timegm(entry.updated_parsed)
    return int(datetime.now(tz=timezone.utc).timestamp())


class EntroFeedRSS:
    def __init__(self, db) -> None:
        self.db = db

    def load_feeds(self) -> None:
        feeds_path = Path(CONFIG_DIR, "feeds.yml").resolve()
        logger.info("Loading feeds from config", extra={"path": feeds_path})
        with open(feeds_path, "r") as fp:
            yaml = YAML(typ="safe")
            configs = yaml.load(fp)

        for config in configs:
            feed = Feed(**config)
            logger.info(f"Found feed id {feed.id} with contents {feed.model_dump()}")

            self.db.upsert_feed(feed)

    def load_settings(self) -> None:
        with open(Path(CONFIG_DIR, "settings.yml").resolve(), "r") as fp:
            yaml = YAML(typ="safe")
            configs = yaml.load(fp)

        settings = GlobalSettings(**configs, db=self.db)

        self.db.upsert_settings(settings)

    def load_handlers(self) -> None:
        with open(Path(CONFIG_DIR, "handlers.yml").resolve(), "r") as fp:
            yaml = YAML(typ="safe")
            configs: dict = yaml.load(fp)

        for k, v in configs.items():
            self.db.reconfigure_handler(id=k, config=v)

    async def _process_feed_entry(
        self, entry: Mapping, feed: Feed, start_ts: int
    ) -> True:
        published_time = _get_entry_time(entry)
        content = "".join(i.get("value", "") for i in entry.get("content", []))

        # Clean arXiv summary pollution
        summary = getattr(entry, "summary", None) or entry.get("summary") or ""
        if summary.startswith("arXiv:"):
            # Remove arXiv header pollution: "arXiv:XXXXvN Announce Type: new\nAbstract: ..."
            summary = re_sub(r"^arXiv:\S+\s+Announce Type: \w+\s+Abstract:\s*", "", summary)
            summary = re_sub(r"^arXiv:\S+\s*", "", summary)  # fallback cleaner

        # Capture RSS category tags (feedparser tags field)
        rss_tags = [t.get("term", "") for t in entry.get("tags", []) if t.get("term")]

        # Use getattr for feedparser entries that have attribute access
        entry_title = getattr(entry, "title", None) or entry.get("title", "")
        entry_link = getattr(entry, "link", None) or entry.get("link", "")
        entry_authors = getattr(entry, "authors", None) or entry.get("authors", [])

        feed_entry = FeedEntry(
            **{
                "title": entry_title,
                "url": entry_link,
                "published_at": published_time,
                "updated_at": _get_entry_time(entry),
                "preview": summary,
                "content": content if content != "" else None,
                "feed_id": feed.id,
                "authors": (
                    [i.get("name", "") for i in entry_authors if isinstance(i, dict)]
                ),
            }
        )

        if published_time >= (
            start_ts if start_ts else 0
        ) and not self.db.feed_entry_exists(feed_entry.id):
            # 准备条目数据用于评分和打标签
            entry_data = {
                "title": entry_title,
                "summary": summary,
                "source": feed.url,
                "source_name": feed.name,
                "rss_tags": rss_tags,
                "published_at": published_time,
                "url": entry_link,
                "content": content if content != "" else None,
            }
            # 评分和打标签（通过 ontology registry 处理）
            scored_entry = _score_and_tag_entry(entry_data, feed_entry=feed_entry, feed=feed)

            # 直接设置评分和标签字段
            feed_entry.total_score = scored_entry.get("total_score", 0)
            feed_entry.recency_score = scored_entry.get("recency_score", 0)
            feed_entry.authority_score = scored_entry.get("authority_score", 0)
            feed_entry.relevance_score = scored_entry.get("relevance_score", 0)
            feed_entry.impact_score = scored_entry.get("impact_score", 0)
            feed_entry.tags = scored_entry.get("tags", [])
            feed_entry.matched_interests = scored_entry.get("matched_interests", [])
            feed_entry.has_ontology_match = scored_entry.get("has_ontology_match", False)

            await self.add_feed_entry(feed=feed, entry=feed_entry)
            return True

    async def _check_feed(self, feed: Feed):
        now = int(datetime.now(tz=timezone.utc).timestamp())
        logger.info(f"Polling feed {feed.id}: {feed.name}")

        poll_state = self.db.get_poll_state(feed)
        logger.info(f"Retrieved poll state: {poll_state}")
        if poll_state:
            entries = feed.rss.entries
        else:
            # if we have no history, take the first 5
            entries = feed.rss.entries[0:5]
            earliest_init_entry = min(
                [_get_entry_time(i) for i in entries] + [now]
            )
            self.db.set_feed_start_ts(feed=feed, start_ts=earliest_init_entry)

        logger.info("Starting feed entry retrieval")
        counter = 0
        start_ts = self.db.get_feed_start_ts(feed=feed)
        for entry in entries:
            processed = await self._process_feed_entry(
                entry=entry, feed=feed, start_ts=start_ts
            )
            if processed:
                counter += 1

        self.db.update_poll_state(feed=feed, now=now)

        logger.info(f"Found {counter} new item(s) for feed {feed.name}")

    def _check_feed_sync(self, feed: Feed):
        """Synchronous version of _check_feed for thread pool execution."""
        now = int(datetime.now(tz=timezone.utc).timestamp())
        logger.info(f"Polling feed (sync) {feed.id}: {feed.name}")

        poll_state = self.db.get_poll_state(feed)
        if poll_state:
            entries = feed.rss.entries
        else:
            entries = feed.rss.entries[0:5]
            earliest_init_entry = min(
                [_get_entry_time(i) for i in entries] + [now]
            )
            self.db.set_feed_start_ts(feed=feed, start_ts=earliest_init_entry)

        counter = 0
        start_ts = self.db.get_feed_start_ts(feed=feed)
        for entry in entries:
            processed = self._process_feed_entry_sync(
                entry=entry, feed=feed, start_ts=start_ts
            )
            if processed:
                counter += 1

        self.db.update_poll_state(feed=feed, now=now)
        logger.info(f"Found {counter} new item(s) for feed {feed.name}")

    def _process_feed_entry_sync(self, entry: Mapping, feed: Feed, start_ts: int) -> True:
        """Synchronous version of _process_feed_entry."""
        published_time = _get_entry_time(entry)
        content = "".join(i.get("value", "") for i in entry.get("content", []))

        summary = entry.get("summary") or ""
        if summary.startswith("arXiv:"):
            summary = re_sub(r"^arXiv:\S+\s+Announce Type: \w+\s+Abstract:\s*", "", summary)
            summary = re_sub(r"^arXiv:\S+\s*", "", summary)

        rss_tags = [t.get("term", "") for t in entry.get("tags", []) if t.get("term")]

        # Use getattr for feedparser entries that have attribute access
        entry_title = getattr(entry, "title", None) or entry.get("title", "")
        entry_link = getattr(entry, "link", None) or entry.get("link", "")
        entry_authors = getattr(entry, "authors", None) or entry.get("authors", [])

        feed_entry = FeedEntry(
            **{
                "title": entry_title,
                "url": entry_link,
                "published_at": published_time,
                "updated_at": _get_entry_time(entry),
                "preview": summary,
                "content": content if content != "" else None,
                "feed_id": feed.id,
                "authors": (
                    [i.get("name", "") for i in entry_authors if isinstance(i, dict)]
                ),
            }
        )

        if published_time >= (start_ts if start_ts else 0) and not self.db.feed_entry_exists(feed_entry.id):
            entry_data = {
                "title": entry_title,
                "summary": summary,
                "source": feed.url,
                "source_name": feed.name,
                "rss_tags": rss_tags,
                "published_at": published_time,
                "url": entry_link,
                "content": content if content != "" else None,
            }
            scored_entry = _score_and_tag_entry(entry_data, feed_entry=feed_entry, feed=feed)

            feed_entry.total_score = scored_entry.get("total_score", 0)
            feed_entry.recency_score = scored_entry.get("recency_score", 0)
            feed_entry.authority_score = scored_entry.get("authority_score", 0)
            feed_entry.relevance_score = scored_entry.get("relevance_score", 0)
            feed_entry.impact_score = scored_entry.get("impact_score", 0)
            feed_entry.tags = scored_entry.get("tags", [])
            feed_entry.matched_interests = scored_entry.get("matched_interests", [])
            feed_entry.has_ontology_match = scored_entry.get("has_ontology_match", False)

            # Sync version - upserts and retrieves content
            self._upsert_feed_entry_sync(feed=feed, entry=feed_entry)
            return True

    def _upsert_feed_entry_sync(self, feed: Feed, entry: FeedEntry) -> None:
        """Synchronous version of add_feed_entry - upserts entry and retrieves content."""
        self.db.upsert_feed_entry(feed=feed, entry=entry)

        # Retrieve content after upsert (same as async add_feed_entry does)
        if not feed.preview_only:
            import asyncio
            try:
                # Run async content retrieval in the thread pool
                asyncio.run(self.db.get_entry_content(entry=entry))
            except Exception as e:
                logger.warning(f"Failed to retrieve content for entry {entry.id}: {e}")

    async def check_feeds(self) -> List:
        now = int(datetime.now(tz=timezone.utc).timestamp())
        logger.info(f"Checking feeds starting at time {now}")

        for _feed in self.db.get_feeds():
            if _feed.refresh_enabled:
                await self._check_feed(feed=_feed)
        return []

    def check_feeds_sync(self) -> List:
        """Synchronous version of check_feeds for use in thread pool."""
        now = int(datetime.now(tz=timezone.utc).timestamp())
        logger.info(f"Checking feeds (sync) starting at time {now}")

        for _feed in self.db.get_feeds():
            if _feed.refresh_enabled:
                self._check_feed_sync(feed=_feed)
        return []

    async def check_feed_by_id(self, id: str) -> List:
        feed = self.db.get_feed(id=id)

        logger.info(f"Manual refresh requested for feed {feed.name}")

        await self._check_feed(feed=feed)
        return []

    async def add_feed_entry(self, feed: Feed, entry: FeedEntry) -> None:
        logger.info(f"Upserting entry from {feed.name}: {entry.title} - id {entry.id}")

        self.db.upsert_feed_entry(feed=feed, entry=entry)

        settings: GlobalSettings = self.db.get_settings()

        if not feed.preview_only:
            await self.db.get_entry_content(entry=entry)

        if feed.notify:
            if settings.send_notification:
                await settings.notification_handler.send_notification(
                    feed=feed, entry=entry
                )
            else:
                logger.info(
                    f"skipping notification for {entry.id} because of global setting"
                )

    @staticmethod
    async def get_entry_html(url: str, settings: GlobalSettings) -> str:
        # Get HTML content directly for a URL
        return await settings.content_retrieval_handler.get_html(url=url, use_script=False)

    async def feeds_to_opml(self) -> OpmlDocument:
        feeds = self.db.get_feeds()

        opml = OpmlDocument(
            title="EntroFeed RSS Backup",
            date_created=datetime.now(),
            date_modified=datetime.now(),
        )

        for _feed in feeds:
            opml.add_rss(text=_feed.name, xml_url=_feed.url, categories=[_feed.category])

        str_now = datetime.now().strftime("%Y%m%d%H%M%S")
        file_name = f"entrofeed_{str_now}.opml"
        out_path = Path(DATA_DIR, file_name).resolve()

        logger.info(f"writing opml to {out_path}")
        opml.dump(fp=out_path)

        return out_path, file_name

    async def opml_to_feeds(self, file: SpooledTemporaryFile):
        opml = OpmlDocument.load(fp=file)

        feeds = []

        for entry in opml.outlines:
            entry: OpmlOutline

            feed = Feed(
                name=entry.text, url=entry.xml_url, category=entry.categories[0] or None
            )

            feeds.append(feed)

        for feed in feeds:
            self.db.upsert_feed(feed=feed)

        settings: GlobalSettings = self.db.get_settings()
        if not settings.finished_onboarding:
            settings.finished_onboarding = True
            self.db.upsert_settings(settings=settings)

    async def backup(self):
        feeds = self.db.get_feeds()
        settings: GlobalSettings = self.db.get_settings()
        handlers = self.db.get_handlers()

        backup = {
            "settings": settings.model_dump(exclude={"db"}),
            "handlers": {k: v.model_dump() for k, v in handlers.items() if v},
            "feeds": [i.model_dump() for i in feeds],
            "feed_entries": {},
            "entry_content": {},
            "poll_state": {},
        }

        for feed in feeds:
            feed: Feed
            backup["poll_state"][feed.id] = self.db.get_poll_state(feed)
            entries = [i["entry"] for i in self.db.get_entries(feed)]
            entry_content = {i.id: await self.db.get_entry_content(i) for i in entries}
            backup["feed_entries"][feed.id] = [i.model_dump() for i in entries]
            backup["entry_content"][feed.id] = {
                k: v.model_dump() for k, v in entry_content.items()
            }

        str_now = datetime.now().strftime("%Y%m%d%H%M%S")
        file_name = f"entrofeed_backup_{str_now}.json"
        out_path = Path(DATA_DIR, file_name).resolve()

        logger.info(f"writing backup to {out_path}")

        with open(out_path, "w+") as fp:
            dump(backup, fp)

        return out_path, file_name

    async def restore(self, file: SpooledTemporaryFile):
        bk = load(file)

        settings = GlobalSettings(db=self.db, **bk.get("settings", {}))
        settings.finished_onboarding = True

        handlers = [
            self.db.reconfigure_handler(id=k, config=v)
            for k, v in bk.get("handlers", {}).items()
        ]
        feeds = [Feed(**i) for i in bk.get("feeds", [])]

        for handler in handlers:
            self.db.upsert_handler(handler=handler)

        self.db.upsert_settings(settings)

        for feed in feeds:
            self.db.upsert_feed(feed)

        feed_entries: dict = bk.get("feed_entries", {})
        for feed, entries in feed_entries.items():
            feed_obj = self.db.get_feed(id=feed)
            for entry in entries:
                entry_obj = FeedEntry(**entry)
                self.db.upsert_feed_entry(feed=feed_obj, entry=entry_obj)

        content: dict = bk.get("entry_content", {})
        for contents in content.values():
            for i in contents.values():
                content_obj = EntryContent(**i)
                await self.db.upsert_entry_content(content=content_obj)

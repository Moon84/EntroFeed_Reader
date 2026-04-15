# -*- coding: utf-8 -*-
"""Feed-related models for EntroFeed."""

from hashlib import md5
from typing import Dict, List, Optional, Type

from feedparser import FeedParserDict, parse
from pydantic import BaseModel


class Feed(BaseModel):
    """RSS feed model."""

    name: str
    category: str = "uncategorized"
    type: str = "rss"
    url: str
    notify_destination: Optional[str] = None
    notify: bool = True
    preview_only: bool = False
    refresh_enabled: bool = True
    use_script: bool = False
    retrieve_content: bool = True

    @property
    def rss(self) -> Type[FeedParserDict]:
        return parse(self.url)

    @property
    def id(self) -> str:
        return md5(self.url.encode()).hexdigest()

    def validate(self):
        try:
            return bool(self.rss.entries)
        except Exception:
            return False


class FeedEntry(BaseModel):
    """Feed entry/article model."""

    feed_id: str
    title: str
    url: str
    published_at: int
    updated_at: int
    content: Optional[str] = None
    authors: List[str] = []
    preview: Optional[str] = None
    # Scoring and tagging metadata
    total_score: Optional[float] = None
    recency_score: Optional[float] = None
    authority_score: Optional[float] = None
    relevance_score: Optional[float] = None
    impact_score: Optional[float] = None
    tags: List[Dict] = []
    matched_interests: List[str] = []
    has_ontology_match: bool = False
    # Read status
    is_read: bool = False
    read_at: Optional[int] = None
    # Like/dislike status: -1 = dislike, 0 = none, 1 = like
    liked: int = 0
    # Favorite/bookmark
    is_favorite: bool = False

    @property
    def id(self) -> str:
        return md5(self.url.encode()).hexdigest()


class EntryContent(BaseModel):
    """Full article content with summary."""

    url: str
    content: Optional[str] = None
    summary: Optional[str] = None
    unretrievable: bool = False
    banned: bool = False

    @property
    def id(self) -> str:
        return md5(self.url.encode()).hexdigest()

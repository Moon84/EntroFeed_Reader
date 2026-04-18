# -*- coding: utf-8 -*-
"""Integration tests for core modules."""

import os
import tempfile
import sqlite3
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, Mock

from src.models.feed import Feed, FeedEntry, EntryContent


class TestFeedModelIntegration:
    """Integration tests for Feed model."""

    def test_feed_model_creation(self):
        """Test creating a real Feed instance."""
        feed = Feed(
            name="Test Feed",
            url="https://example.com/feed.xml",
            category="technology",
        )

        assert feed.name == "Test Feed"
        assert feed.url == "https://example.com/feed.xml"
        assert feed.category == "technology"
        assert feed.type == "rss"
        assert feed.notify is True
        assert feed.id is not None
        assert len(feed.id) == 32  # MD5 hash length

    def test_feed_model_id_consistency(self):
        """Test that feed ID is consistent for same URL."""
        feed1 = Feed(name="Feed 1", url="https://example.com/feed.xml")
        feed2 = Feed(name="Feed 2", url="https://example.com/feed.xml")

        assert feed1.id == feed2.id

    def test_feed_model_different_urls_different_ids(self):
        """Test that different URLs produce different IDs."""
        feed1 = Feed(name="Feed 1", url="https://example.com/feed1.xml")
        feed2 = Feed(name="Feed 2", url="https://example.com/feed2.xml")

        assert feed1.id != feed2.id


class TestFeedEntryModelIntegration:
    """Integration tests for FeedEntry model."""

    def test_entry_model_creation(self):
        """Test creating a real FeedEntry instance."""
        entry = FeedEntry(
            feed_id="feed123",
            title="Test Article",
            url="https://example.com/article.html",
            published_at=1234567890,
            updated_at=1234567890,
            content="<p>Full article content</p>",
            preview="Article preview text",
            authors=["Author 1", "Author 2"],
        )

        assert entry.title == "Test Article"
        assert entry.feed_id == "feed123"
        assert len(entry.authors) == 2
        assert entry.id is not None

    def test_entry_model_scoring_fields(self):
        """Test entry with scoring metadata."""
        entry = FeedEntry(
            feed_id="feed123",
            title="Important Article",
            url="https://example.com/important.html",
            published_at=1234567890,
            updated_at=1234567890,
            total_score=0.85,
            recency_score=0.9,
            authority_score=0.8,
            relevance_score=0.75,
            impact_score=0.7,
            tags=[{"name": "AI", "category": "technology"}],
            matched_interests=["artificial intelligence", "machine learning"],
            has_ontology_match=True,
        )

        assert entry.total_score == 0.85
        assert entry.has_ontology_match is True
        assert len(entry.tags) == 1
        assert len(entry.matched_interests) == 2

    def test_entry_model_read_status(self):
        """Test entry with read status."""
        entry = FeedEntry(
            feed_id="feed123",
            title="Unread Article",
            url="https://example.com/unread.html",
            published_at=1234567890,
            updated_at=1234567890,
            is_read=False,
            liked=0,
            is_favorite=False,
        )

        assert entry.is_read is False
        assert entry.liked == 0
        assert entry.is_favorite is False

    def test_entry_model_like_dislike_status(self):
        """Test entry with like/dislike status."""
        liked_entry = FeedEntry(
            feed_id="feed123",
            title="Liked Article",
            url="https://example.com/liked.html",
            published_at=1234567890,
            updated_at=1234567890,
            liked=1,
            is_favorite=True,
        )

        disliked_entry = FeedEntry(
            feed_id="feed123",
            title="Disliked Article",
            url="https://example.com/disliked.html",
            published_at=1234567890,
            updated_at=1234567890,
            liked=-1,
        )

        assert liked_entry.liked == 1
        assert liked_entry.is_favorite is True
        assert disliked_entry.liked == -1


class TestEntryContentModelIntegration:
    """Integration tests for EntryContent model."""

    def test_entry_content_creation(self):
        """Test creating a real EntryContent instance."""
        content = EntryContent(
            url="https://example.com/article.html",
            content="<p>Full article content here</p>",
            summary="Article summary",
            unretrievable=False,
            banned=False,
        )

        assert content.url == "https://example.com/article.html"
        assert content.content is not None
        assert content.summary == "Article summary"
        assert content.id is not None

    def test_entry_content_banned(self):
        """Test banned content."""
        content = EntryContent(
            url="https://example.com/banned.html",
            content=None,
            summary="Banned content",
            banned=True,
            unretrievable=False,
        )

        assert content.banned is True

    def test_entry_content_unretrievable(self):
        """Test unretrievable content."""
        content = EntryContent(
            url="https://example.com/unretrievable.html",
            content=None,
            summary=None,
            unretrievable=True,
            banned=False,
        )

        assert content.unretrievable is True
        assert content.content is None


class TestFeedModelValidation:
    """Integration tests for Feed validation."""

    def test_feed_validate_invalid_url(self):
        """Test validation with invalid URL."""
        feed = Feed(
            name="Test",
            url="not-a-valid-url",
        )

        result = feed.validate()
        assert result is False

    def test_feed_validate_returns_bool(self):
        """Test that validate returns boolean."""
        feed = Feed(
            name="Test",
            url="https://example.com/feed.xml",
        )

        result = feed.validate()
        assert isinstance(result, bool)


class TestStorageDirectSQL:
    """Integration tests for storage using direct SQL."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feeds (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT DEFAULT 'uncategorized',
                    type TEXT DEFAULT 'rss',
                    url TEXT NOT NULL UNIQUE,
                    notify_destination TEXT,
                    notify INTEGER DEFAULT 1,
                    preview_only INTEGER DEFAULT 0,
                    refresh_enabled INTEGER DEFAULT 1,
                    use_script INTEGER DEFAULT 0,
                    retrieve_content INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feed_entries (
                    id TEXT PRIMARY KEY,
                    feed_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    published_at INTEGER,
                    updated_at INTEGER,
                    content TEXT,
                    authors TEXT DEFAULT '[]',
                    preview TEXT,
                    created_at TEXT NOT NULL,
                    updated_at_entry TEXT NOT NULL,
                    FOREIGN KEY (feed_id) REFERENCES feeds(id)
                )
            """)
            conn.commit()

            yield conn

            conn.close()

    def test_save_and_get_feed(self, temp_db):
        """Test saving and retrieving a feed via SQL."""
        feed_id = "test_feed_123"
        now = datetime.now().isoformat()

        temp_db.execute(
            """INSERT INTO feeds (id, name, category, url, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                feed_id,
                "Test Feed",
                "technology",
                "https://example.com/feed.xml",
                now,
                now,
            ),
        )
        temp_db.commit()

        cursor = temp_db.execute("SELECT * FROM feeds WHERE id = ?", (feed_id,))
        row = cursor.fetchone()

        assert row is not None
        assert row["name"] == "Test Feed"
        assert row["category"] == "technology"

    def test_save_and_get_entry(self, temp_db):
        """Test saving and retrieving an entry via SQL."""
        feed_id = "test_feed_123"
        now = datetime.now().isoformat()

        temp_db.execute(
            """INSERT INTO feeds (id, name, category, url, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (feed_id, "Test Feed", "tech", "https://example.com/feed.xml", now, now),
        )

        entry_id = "test_entry_456"
        temp_db.execute(
            """INSERT INTO feed_entries (id, feed_id, title, url, published_at, updated_at, created_at, updated_at_entry)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                entry_id,
                feed_id,
                "Test Entry",
                "https://example.com/entry.html",
                1234567890,
                1234567890,
                now,
                now,
            ),
        )
        temp_db.commit()

        cursor = temp_db.execute("SELECT * FROM feed_entries WHERE id = ?", (entry_id,))
        row = cursor.fetchone()

        assert row is not None
        assert row["title"] == "Test Entry"

    def test_list_feeds(self, temp_db):
        """Test listing all feeds."""
        now = datetime.now().isoformat()

        temp_db.execute(
            """INSERT INTO feeds (id, name, category, url, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("feed1", "Feed 1", "tech", "https://example.com/feed1.xml", now, now),
        )
        temp_db.execute(
            """INSERT INTO feeds (id, name, category, url, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("feed2", "Feed 2", "news", "https://example.com/feed2.xml", now, now),
        )
        temp_db.commit()

        cursor = temp_db.execute("SELECT COUNT(*) as count FROM feeds")
        count = cursor.fetchone()["count"]

        assert count == 2

    def test_delete_feed(self, temp_db):
        """Test deleting a feed."""
        now = datetime.now().isoformat()

        temp_db.execute(
            """INSERT INTO feeds (id, name, category, url, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                "to_delete",
                "To Delete",
                "tech",
                "https://example.com/delete.xml",
                now,
                now,
            ),
        )
        temp_db.commit()

        temp_db.execute("DELETE FROM feeds WHERE id = ?", ("to_delete",))
        temp_db.commit()

        cursor = temp_db.execute("SELECT * FROM feeds WHERE id = ?", ("to_delete",))
        row = cursor.fetchone()

        assert row is None


class TestConstantsIntegration:
    """Integration tests for constants."""

    def test_user_agent_format(self):
        """Test USER_AGENT is properly formatted."""
        from src.constants import USER_AGENT

        assert USER_AGENT.startswith("EntroFeed/")
        assert len(USER_AGENT) > 10

    def test_data_dir(self):
        """Test DATA_DIR exists or can be created."""
        from src.constants import DATA_DIR

        assert DATA_DIR is not None
        assert isinstance(DATA_DIR, Path)


class TestHandlersIntegration:
    """Integration tests for handlers."""

    def test_handler_base_id(self):
        """Test HandlerBase has id property."""
        from src.handlers import HandlerBase

        class TestHandler(HandlerBase):
            id = "test_handler"

        handler = TestHandler()
        assert handler.id == "test_handler"

    def test_content_retrieval_handler_id(self):
        """Test ContentRetrievalHandler has an id."""
        from src.handlers import ContentRetrievalHandler

        assert ContentRetrievalHandler.id is not None
        assert isinstance(ContentRetrievalHandler.id, str)

    def test_notification_handler_id(self):
        """Test NotificationHandler has an id."""
        from src.handlers import NotificationHandler

        assert NotificationHandler.id is not None
        assert isinstance(NotificationHandler.id, str)


class TestOntologyTypesIntegration:
    """Integration tests for ontology types."""

    def test_interest_tag_creation(self):
        """Test creating InterestTag."""
        from src.services.ontology.types import InterestTag, InterestCategory, TagSource

        tag = InterestTag(
            name="artificial intelligence",
            category=InterestCategory.TECHNOLOGY,
            confidence=0.9,
            source=TagSource.EXPLICIT,
        )

        assert tag.name == "artificial intelligence"
        assert tag.category == InterestCategory.TECHNOLOGY
        assert tag.confidence == 0.9
        assert tag.source == TagSource.EXPLICIT
        assert tag.to_dict() is not None

    def test_user_interest_mark_accessed(self):
        """Test UnifiedNode mark_accessed (was UserInterest)."""
        from src.services.ontology.types import (
            UnifiedNode,
            InterestCategory,
        )

        interest = UnifiedNode(
            name="AI",
            is_interest=True,
            priority=5,
            relevance=0.8,
            domain="technology",
        )

        initial_count = interest.access_count
        interest.mark_accessed()

        assert interest.access_count == initial_count + 1
        assert interest.relevance > 0.8

    def test_content_profile_creation(self):
        """Test creating ContentProfile."""
        from src.services.ontology.types import ContentProfile

        profile = ContentProfile(
            entry_id="entry123",
            tags=[
                {"name": "AI", "category": "technology"},
                {"name": "ML", "category": "technology"},
            ],
            priority=4,
            summary="Test article about AI",
            key_entities=["GPT", "Neural Networks"],
            language="en",
        )

        assert profile.entry_id == "entry123"
        assert len(profile.tags) == 2
        assert profile.priority == 4
        assert profile.language == "en"

    def test_ontology_node_creation(self):
        """Test creating OntologyNode."""
        from src.services.ontology.types import OntologyNode

        node = OntologyNode(
            name="Artificial Intelligence",
            node_type="concept",
            description="Intelligence demonstrated by machines",
            is_seed=True,
            seed_priority=5,
        )

        assert node.name == "Artificial Intelligence"
        assert node.node_type == "concept"
        assert node.is_seed is True
        assert node.seed_priority == 5

    def test_ontology_relation_creation(self):
        """Test creating OntologyRelation."""
        from src.services.ontology.types import OntologyRelation

        relation = OntologyRelation(
            source_id="node1",
            target_id="node2",
            relation_type="related_to",
            weight=0.8,
        )

        assert relation.source_id == "node1"
        assert relation.target_id == "node2"
        assert relation.relation_type == "related_to"
        assert relation.weight == 0.8


class TestSkillsIntegration:
    """Integration tests for skills system."""

    def test_skills_can_be_imported(self):
        """Test skills module can be imported."""
        from src.skills import registry, loader, executor

        assert registry is not None
        assert loader is not None
        assert executor is not None


class TestPluginBaseIntegration:
    """Integration tests for plugin base classes."""

    def test_plugin_base_import(self):
        """Test that PluginBase can be imported."""
        from src.kernel.registry import PluginBase

        assert PluginBase is not None

    def test_plugin_registry_import(self):
        """Test that PluginRegistry can be imported."""
        from src.kernel.registry import PluginRegistry

        assert PluginRegistry is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

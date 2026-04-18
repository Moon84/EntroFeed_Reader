# -*- coding: utf-8 -*-
"""Tests for Feed service module."""

from datetime import datetime, timezone
from calendar import timegm
from io import BytesIO
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import pytest

from src.services.feed.service import (
    _get_entry_time,
    _score_and_tag_entry,
    EntroFeedRSS,
)
from src.models.feed import Feed


class TestGetEntryTime:
    """Test _get_entry_time helper function."""

    def test_published_parsed_exists(self):
        """Test when published_parsed is available."""
        entry = Mock()
        entry.published_parsed = (2024, 1, 15, 10, 30, 0, 0, 0, 0)
        entry.updated_parsed = None

        result = _get_entry_time(entry)
        expected = timegm((2024, 1, 15, 10, 30, 0, 0, 0, 0))
        assert result == expected

    def test_updated_parsed_fallback(self):
        """Test fallback to updated_parsed."""
        entry = Mock()
        entry.published_parsed = None
        entry.updated_parsed = (2024, 3, 20, 14, 45, 0, 0, 0, 0)

        result = _get_entry_time(entry)
        expected = timegm((2024, 3, 20, 14, 45, 0, 0, 0, 0))
        assert result == expected

    def test_no_time_data(self):
        """Test when no time data is available."""
        entry = Mock()
        entry.published_parsed = None
        entry.updated_parsed = None

        result = _get_entry_time(entry)
        # Should be current time (within a few seconds)
        now = int(datetime.now(tz=timezone.utc).timestamp())
        assert abs(result - now) < 5


class TestScoreAndTagEntry:
    """Test _score_and_tag_entry function."""

    def test_returns_entry_data_on_exception(self):
        """Test that entry_data is returned on exception."""
        entry_data = {
            "title": "Test Entry",
            "summary": "Test summary",
            "url": "http://test.com",
        }

        # Mock to force exception path - patch at the import location
        with patch(
            "src.services.ontology.priority_scorer.get_priority_scorer",
            side_effect=Exception("Test error"),
        ):
            result = _score_and_tag_entry(entry_data)

        # Should return original entry_data with default scores
        assert result["title"] == "Test Entry"
        assert result.get("total_score", 0) == 0


class TestEntroFeedRSS:
    """Test EntroFeedRSS class."""

    def test_init(self):
        """Test initialization."""
        mock_db = Mock()
        rss = EntroFeedRSS(mock_db)
        assert rss.db is mock_db


class TestOPMLExport:
    """Test OPML export functionality."""

    @pytest.mark.asyncio
    async def test_opml_to_feeds(self):
        """Test OPML import creates feeds."""
        mock_db = Mock()
        mock_db.get_settings.return_value = Mock(finished_onboarding=False)

        rss = EntroFeedRSS(mock_db)

        # Create minimal OPML content
        opml_content = """<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <head>
    <title>Test OPML</title>
  </head>
  <body>
    <outline text="Test Feed" xmlUrl="http://test.com/feed.xml" category="tech"/>
  </body>
</opml>
"""
        file_obj = BytesIO(opml_content.encode())

        await rss.opml_to_feeds(file_obj)

        # Should have called upsert_feed
        assert mock_db.upsert_feed.called

        # Should have marked onboarding as complete
        assert mock_db.upsert_settings.called


class TestFeedOperations:
    """Test feed operations."""

    @pytest.mark.asyncio
    async def test_check_feed_by_id(self):
        """Test checking a specific feed by ID."""
        mock_db = Mock()
        mock_feed = Mock()
        mock_feed.id = "test-feed-id"
        mock_feed.name = "Test Feed"
        mock_feed.refresh_enabled = True
        mock_feed.rss = Mock()
        mock_feed.rss.entries = []

        mock_db.get_feed.return_value = mock_feed
        mock_db.get_poll_state.return_value = True
        mock_db.get_feed_start_ts.return_value = 0

        rss = EntroFeedRSS(mock_db)
        result = await rss.check_feed_by_id("test-feed-id")

        # Should have called get_feed
        assert mock_db.get_feed.called
        # Method returns None, so result should be None
        assert result is None

    @pytest.mark.asyncio
    async def test_add_feed_entry(self):
        """Test adding a feed entry."""
        mock_db = Mock()
        mock_settings = Mock()
        mock_settings.send_notification = False
        mock_db.get_settings.return_value = mock_settings
        mock_db.get_entry_content = AsyncMock()

        mock_feed = Mock()
        mock_feed.notify = False
        mock_feed.preview_only = False

        mock_entry = Mock()
        mock_entry.id = "entry-1"
        mock_entry.title = "Test Entry"

        rss = EntroFeedRSS(mock_db)
        await rss.add_feed_entry(feed=mock_feed, entry=mock_entry)

        # Should upsert the entry
        assert mock_db.upsert_feed_entry.called

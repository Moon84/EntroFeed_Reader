# -*- coding: utf-8 -*-
"""Tests for recommendation modules."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.services.recommendation import (
    SimilarRecommender,
    InterestBasedRecommender,
    TrendingRecommender,
    get_similar_recommendations,
    get_interest_recommendations,
    get_trending_recommendations,
)
from src.services.ontology.types import (
    InterestTag,
    UnifiedNode,
    ContentProfile,
    InterestCategory,
    TagSource,
)


class TestSimilarRecommender:
    """Test SimilarRecommender."""

    @pytest.fixture
    def mock_memory(self):
        """Create mock OntologyMemory."""
        mock = MagicMock()
        return mock

    @pytest.fixture
    def recommender(self, mock_memory):
        """Create SimilarRecommender with mock memory."""
        return SimilarRecommender(memory=mock_memory)

    def test_recommend_with_profile(self, recommender, mock_memory):
        """Test recommend when content profile exists."""
        mock_memory.get_content_profile.return_value = ContentProfile(
            entry_id="entry1",
            summary="AI breakthrough in medical diagnosis",
            tags=[
                InterestTag(
                    name="artificial intelligence", category=InterestCategory.TECHNOLOGY
                ),
                InterestTag(
                    name="medical diagnosis", category=InterestCategory.MEDICAL
                ),
            ],
            priority=4,
        )
        mock_memory.search_similar_content.return_value = {
            "ids": [["entry2", "entry3"]],
            "documents": [["doc1", "doc2"]],
            "metadatas": [[{"url": "http://ex.com/2"}, {"url": "http://ex.com/3"}]],
        }

        with patch.object(recommender, "_is_read", return_value=False):
            results = recommender.recommend("entry1", limit=2)

        assert len(results) <= 2
        assert all(r["source"] == "similar" for r in results)

    def test_recommend_with_no_profile(self, recommender, mock_memory):
        """Test recommend when no content profile exists."""
        mock_memory.get_content_profile.side_effect = Exception("Not found")

        mock_entry = Mock()
        mock_entry.title = "Test Article"
        mock_entry.preview = "Test preview"

        mock_storage = MagicMock()
        mock_storage.get_feed_entry.return_value = mock_entry

        with patch.object(recommender, "_is_read", return_value=False):
            with patch(
                "src.storage.singleton.get_storage",
                return_value=mock_storage,
            ):
                results = recommender.recommend("entry1", limit=2)

        assert isinstance(results, list)

    def test_recommend_excludes_read(self, recommender, mock_memory):
        """Test that read content is excluded."""
        mock_memory.get_content_profile.return_value = ContentProfile(
            entry_id="entry1",
            summary="Test content",
            priority=3,
        )
        mock_memory.search_similar_content.return_value = {
            "ids": [["entry2", "entry3"]],
            "documents": [["doc1", "doc2"]],
            "metadatas": [[{"url": "http://ex.com/2"}, {"url": "http://ex.com/3"}]],
        }

        with patch.object(recommender, "_is_read", side_effect=[False, True]):
            results = recommender.recommend("entry1", limit=5, exclude_read=True)

        assert len(results) <= 1

    def test_recommend_fallback_on_search_error(self, recommender, mock_memory):
        """Test fallback when vector search fails."""
        mock_memory.get_content_profile.return_value = ContentProfile(
            entry_id="entry1",
            summary="Test content",
            priority=3,
        )
        mock_memory.search_similar_content.side_effect = Exception("Search failed")

        results = recommender.recommend("entry1", limit=5)

        assert results == []

    def test_is_read(self, recommender, mock_memory):
        """Test _is_read method."""
        mock_memory.get_content_profile.return_value = ContentProfile(
            entry_id="entry1",
            summary="Test",
            priority=3,
        )

        assert recommender._is_read("entry1") is True

        mock_memory.get_content_profile.side_effect = Exception("Not found")
        assert recommender._is_read("entry2") is False

    def test_get_entry_title(self, recommender):
        """Test _get_entry_title method."""
        mock_entry = Mock()
        mock_entry.title = "Test Title"

        mock_storage = MagicMock()
        mock_storage.get_feed_entry.return_value = mock_entry

        with patch("src.storage.singleton.get_storage", return_value=mock_storage):
            title = recommender._get_entry_title("entry1")

        assert title == "Test Title"

    def test_get_entry_title_on_error(self, recommender):
        """Test _get_entry_title on error."""
        mock_storage = MagicMock()
        mock_storage.get_feed_entry.side_effect = Exception("Not found")

        with patch("src.storage.singleton.get_storage", return_value=mock_storage):
            title = recommender._get_entry_title("entry1")

        assert title == ""


class TestSimilarRecommenderConvenienceFunction:
    """Test convenience functions for similar recommendations."""

    def test_get_similar_recommendations(self):
        """Test get_similar_recommendations convenience function."""
        mock_recommender = Mock()
        mock_recommender.recommend.return_value = [
            {"entry_id": "entry2", "source": "similar", "similarity_score": 0.9}
        ]

        with patch(
            "src.services.recommendation.similar.SimilarRecommender",
            return_value=mock_recommender,
        ):
            results = get_similar_recommendations("entry1", limit=5)

        mock_recommender.recommend.assert_called_once_with("entry1", 5, True)
        assert len(results) == 1


class TestTrendingRecommender:
    """Test TrendingRecommender."""

    @pytest.fixture
    def mock_registry(self):
        """Create mock OntologyRegistry."""
        mock = MagicMock()
        return mock

    @pytest.fixture
    def recommender(self, mock_registry):
        """Create TrendingRecommender with mock registry."""
        return TrendingRecommender(registry=mock_registry)

    def test_recommend_with_profiles(self, recommender, mock_registry):
        """Test recommend when ContentProfiles exist."""
        profiles = [
            ContentProfile(
                entry_id="entry1",
                tags=[InterestTag(name="AI", category=InterestCategory.TECHNOLOGY)],
                priority=5,
                key_entities=["GPT"],
            ),
            ContentProfile(
                entry_id="entry2",
                tags=[InterestTag(name="AI", category=InterestCategory.TECHNOLOGY)],
                priority=4,
                key_entities=["machine learning"],
            ),
        ]
        mock_registry.get_recent_profiles.return_value = profiles

        mock_entry_info = {
            "title": "Test Article",
            "url": "http://ex.com/test",
            "feed_name": "Test Feed",
        }

        with patch.object(recommender, "_get_entry_info", return_value=mock_entry_info):
            results = recommender.recommend(limit=10, recent_hours=24)

        assert len(results) <= 10
        assert all(r["source"] == "trending" for r in results)

    def test_recommend_fallback_to_entries(self, recommender, mock_registry):
        """Test fallback when no profiles exist."""
        mock_registry.get_recent_profiles.return_value = []

        mock_storage = MagicMock()
        mock_entry = Mock()
        mock_entry.id = "entry1"
        mock_entry.title = "Test"
        mock_entry.preview = "Preview"
        mock_entry.feed_id = "feed1"
        mock_entry.tags = []
        mock_entry.total_score = 5
        mock_entry.feed_name = "Feed"

        mock_storage.get_entries.return_value = [{"id": "entry1", "entry": mock_entry}]

        mock_entry_info = {
            "title": "Test Article",
            "url": "http://ex.com/test",
            "feed_name": "Test Feed",
        }

        with patch.object(recommender, "_get_entry_info", return_value=mock_entry_info):
            with patch(
                "src.storage.singleton.get_storage",
                return_value=mock_storage,
            ):
                results = recommender.recommend(limit=10, recent_hours=24)

        assert len(results) <= 10

    def test_calculate_trending_score(self, recommender):
        """Test _calculate_trending_score method."""
        profile = ContentProfile(
            entry_id="entry1",
            tags=[
                InterestTag(name="AI", category=InterestCategory.TECHNOLOGY),
                InterestTag(name="ML", category=InterestCategory.TECHNOLOGY),
            ],
            priority=5,
            key_entities=["GPT", "neural network"],
        )

        profiles = [profile]

        score = recommender._calculate_trending_score(profile, profiles)

        assert 0.0 <= score <= 1.0

    def test_count_entity_overlap(self, recommender):
        """Test _count_entity_overlap method."""
        profile1 = ContentProfile(
            entry_id="entry1",
            tags=[],
            key_entities=["AI", "ML"],
            priority=3,
        )
        profile2 = ContentProfile(
            entry_id="entry2",
            tags=[],
            key_entities=["AI", "deep learning"],
            priority=3,
        )
        profile3 = ContentProfile(
            entry_id="entry3",
            tags=[],
            key_entities=["blockchain"],
            priority=3,
        )

        profiles = [profile1, profile2, profile3]

        overlap = recommender._count_entity_overlap(profile1, profiles)

        assert overlap == 1  # Only profile2 shares entities with profile1

    def test_count_tag_overlap(self, recommender):
        """Test _count_tag_overlap method."""
        tag1 = InterestTag(name="AI", category=InterestCategory.TECHNOLOGY)
        tag2 = InterestTag(name="ML", category=InterestCategory.TECHNOLOGY)
        tag3 = InterestTag(name="blockchain", category=InterestCategory.FINANCE)

        profile1 = ContentProfile(
            entry_id="entry1",
            tags=[tag1, tag2],
            priority=3,
        )
        profile2 = ContentProfile(
            entry_id="entry2",
            tags=[tag1, tag2],
            priority=3,
        )
        profile3 = ContentProfile(
            entry_id="entry3",
            tags=[tag3],
            priority=3,
        )

        profiles = [profile1, profile2, profile3]

        overlap = recommender._count_tag_overlap(profile1, profiles)

        assert overlap == 1  # Only profile2 has 2+ shared tags with profile1

    def test_source_authority_bonus(self, recommender):
        """Test authority bonus calculation."""
        fda_entry = Mock()
        fda_entry.feed_name = "FDA News"

        nature_entry = Mock()
        nature_entry.feed_name = "Nature News"

        regular_entry = Mock()
        regular_entry.feed_name = "My Blog"

        assert recommender._get_source_authority_bonus_from_entry(fda_entry) == 1.0
        assert recommender._get_source_authority_bonus_from_entry(nature_entry) == 0.8
        assert recommender._get_source_authority_bonus_from_entry(regular_entry) == 0.4

    def test_get_entry_info(self, recommender):
        """Test _get_entry_info method."""
        mock_entry = Mock()
        mock_entry.title = "Test"
        mock_entry.url = "http://test.com"
        mock_entry.feed_id = "feed1"
        mock_entry.published_at = 1234567890

        mock_feed = Mock()
        mock_feed.name = "Test Feed"

        mock_storage = MagicMock()
        mock_storage.get_feed_entry.return_value = mock_entry
        mock_storage.get_feed.return_value = mock_feed

        mock_backend = Mock()
        mock_backend._format_time.return_value = "2024-01-01"

        with patch(
            "src.storage.singleton.get_storage",
            return_value=mock_storage,
        ):
            with patch(
                "src.backend.EntroFeedBackend",
                return_value=mock_backend,
            ):
                info = recommender._get_entry_info("entry1")

        assert info["title"] == "Test"
        assert info["url"] == "http://test.com"


class TestTrendingRecommenderConvenienceFunction:
    """Test convenience functions for trending recommendations."""

    def test_get_trending_recommendations(self):
        """Test get_trending_recommendations convenience function."""
        mock_recommender = Mock()
        mock_recommender.recommend.return_value = [
            {"entry_id": "entry1", "source": "trending", "trending_score": 0.8}
        ]

        with patch(
            "src.services.recommendation.trending.TrendingRecommender",
            return_value=mock_recommender,
        ):
            results = get_trending_recommendations(limit=10, recent_hours=24)

        mock_recommender.recommend.assert_called_once_with(10, 24)
        assert len(results) == 1


class TestInterestBasedRecommender:
    """Test InterestBasedRecommender."""

    @pytest.fixture
    def mock_registry(self):
        """Create mock OntologyRegistry."""
        mock = MagicMock()
        return mock

    @pytest.fixture
    def recommender(self, mock_registry):
        """Create InterestBasedRecommender with mock registry."""
        return InterestBasedRecommender(registry=mock_registry)

    def test_recommend_with_interests(self, recommender, mock_registry):
        """Test recommend when user interests exist."""
        user_interests = [
            UnifiedNode(
                name="artificial intelligence",
                is_interest=True,
                interest_priority=5,
                interest_level=0.9,
                category=InterestCategory.TECHNOLOGY,
            ),
        ]
        mock_registry.get_user_interests.return_value = user_interests

        profile = ContentProfile(
            entry_id="entry1",
            tags=[
                InterestTag(
                    name="artificial intelligence",
                    category=InterestCategory.TECHNOLOGY,
                )
            ],
            priority=4,
            summary="AI breakthrough",
        )
        mock_registry.get_content_profile.return_value = profile

        mock_entry = Mock()
        mock_entry.id = "entry1"
        mock_entry.title = "AI News"
        mock_entry.preview = "Latest AI developments"
        mock_entry.feed_id = "feed1"

        mock_storage = MagicMock()
        mock_storage.get_entries.return_value = [{"id": "entry1", "entry": mock_entry}]

        mock_entry_info = {
            "title": "AI News",
            "url": "http://ex.com/ai",
            "feed_name": "Tech News",
            "published_at": "2024-01-01",
        }

        with patch.object(recommender, "_get_entry_info", return_value=mock_entry_info):
            with patch(
                "src.storage.singleton.get_storage",
                return_value=mock_storage,
            ):
                results = recommender.recommend(limit=10, recent_hours=72)

        assert len(results) <= 10
        assert all(r["source"] == "interest" for r in results)

    def test_recommend_no_interests(self, recommender, mock_registry):
        """Test recommend when no user interests exist."""
        mock_registry.get_user_interests.return_value = []

        results = recommender.recommend(limit=10, recent_hours=72)

        assert results == []

    def test_convert_entry_tags(self, recommender):
        """Test _convert_entry_tags method."""
        entry = Mock()
        entry.tags = [
            {
                "name": "AI",
                "category": "technology",
                "confidence": 0.9,
                "is_entity": False,
            },
            {
                "name": "ML",
                "category": "technology",
                "confidence": 0.8,
                "is_entity": True,
            },
        ]

        tags = recommender._convert_entry_tags(entry)

        assert len(tags) == 2
        assert all(isinstance(t, InterestTag) for t in tags)

    def test_calculate_interest_score(self, recommender):
        """Test _calculate_interest_score method."""
        tag = InterestTag(
            name="AI", category=InterestCategory.TECHNOLOGY, confidence=0.9
        )
        profile = ContentProfile(
            entry_id="entry1",
            tags=[tag],
            priority=4,
            summary="Artificial intelligence breakthrough",
        )

        user_interests = [
            UnifiedNode(
                name="artificial intelligence",
                is_interest=True,
                interest_priority=5,
                interest_level=0.9,
                category=InterestCategory.TECHNOLOGY,
            ),
        ]

        score = recommender._calculate_interest_score(
            profile, user_interests, "AI breakthrough"
        )

        assert 0.0 <= score <= 1.0

    def test_get_matched_interest(self, recommender):
        """Test _get_matched_interest method."""
        tag1 = InterestTag(
            name="artificial intelligence", category=InterestCategory.TECHNOLOGY
        )
        tag2 = InterestTag(
            name="machine learning", category=InterestCategory.TECHNOLOGY
        )

        profile = ContentProfile(
            entry_id="entry1",
            tags=[tag1, tag2],
            priority=4,
        )

        user_interests = [
            UnifiedNode(
                name="artificial intelligence",
                is_interest=True,
                interest_priority=5,
                interest_level=0.9,
                category=InterestCategory.TECHNOLOGY,
            ),
            UnifiedNode(
                name="deep learning",
                is_interest=True,
                interest_priority=3,
                interest_level=0.7,
                category=InterestCategory.TECHNOLOGY,
            ),
        ]

        matched = recommender._get_matched_interest(profile, user_interests)

        assert matched == "artificial intelligence"

    def test_get_entry_info(self, recommender):
        """Test _get_entry_info method."""
        mock_entry = Mock()
        mock_entry.title = "Test"
        mock_entry.url = "http://test.com"
        mock_entry.feed_id = "feed1"
        mock_entry.published_at = 1234567890

        mock_feed = Mock()
        mock_feed.name = "Test Feed"

        mock_storage = MagicMock()
        mock_storage.get_feed_entry.return_value = mock_entry
        mock_storage.get_feed.return_value = mock_feed

        mock_backend = Mock()
        mock_backend._format_time.return_value = "2024-01-01"

        with patch(
            "src.storage.singleton.get_storage",
            return_value=mock_storage,
        ):
            with patch(
                "src.backend.EntroFeedBackend",
                return_value=mock_backend,
            ):
                info = recommender._get_entry_info("entry1")

        assert info["title"] == "Test"
        assert info["url"] == "http://test.com"


class TestInterestBasedRecommenderConvenienceFunction:
    """Test convenience functions for interest-based recommendations."""

    def test_get_interest_recommendations(self):
        """Test get_interest_recommendations convenience function."""
        mock_recommender = Mock()
        mock_recommender.recommend.return_value = [
            {"entry_id": "entry1", "source": "interest", "match_score": 0.85}
        ]

        with patch(
            "src.services.recommendation.interest_based.InterestBasedRecommender",
            return_value=mock_recommender,
        ):
            results = get_interest_recommendations(limit=10, recent_hours=72)

        mock_recommender.recommend.assert_called_once_with(10, 72)
        assert len(results) == 1


class TestCrossDomainDetection:
    """Test cross-domain detection in InterestBasedRecommender."""

    @pytest.fixture
    def recommender(self):
        """Create InterestBasedRecommender without registry."""
        return InterestBasedRecommender(registry=None)

    def test_cross_domain_match(self, recommender):
        """Test _cross_domain_match method."""
        detected_domains = [
            {"domain": "MedicalAI", "score": 0.9, "level": 2},
            {"domain": "Technology", "score": 0.8, "level": 1},
        ]

        score = recommender._cross_domain_match(
            interest_name="machine learning",
            interest_category="technology",
            detected_domains=detected_domains,
        )

        assert 0.0 <= score <= 1.0

    def test_get_cross_domain_tags(self, recommender):
        """Test _get_cross_domain_tags method."""
        text = "AI-powered medical diagnosis system using deep learning"

        tags = recommender._get_cross_domain_tags(text)

        assert isinstance(tags, list)
        assert len(tags) <= 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# -*- coding: utf-8 -*-
"""
Trending Recommender - Recommend popular/trending content.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import Counter

from src.services.ontology.types import ContentProfile


class TrendingRecommender:
    """
    Recommend trending content based on:

    - ContentProfile priority (from ontology processing)
    - Entity/tag overlap with other recent content
    - Source authority
    - Falls back to raw entry processing when no ContentProfile exists

    Uses OntologyRegistry as the primary interface.
    """

    def __init__(self, registry=None):
        """
        Initialize trending recommender.

        Args:
            registry: OntologyRegistry instance (uses global if not provided)
        """
        self._registry_instance = registry

    @property
    def _registry(self):
        """Get OntologyRegistry facade."""
        if self._registry_instance is None:
            from src.services.ontology import get_ontology_registry
            self._registry_instance = get_ontology_registry()
        return self._registry_instance

    def recommend(
        self,
        limit: int = 10,
        recent_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get trending content recommendations.

        Args:
            limit: Maximum number of recommendations
            recent_hours: Consider content from last N hours

        Returns:
            List of trending entries with scores
        """
        # Try to get trending from ContentProfiles first (preferred)
        profile_recommendations = self._get_trending_from_profiles(limit, recent_hours)
        if profile_recommendations:
            return profile_recommendations

        # Fallback: use raw entry processing
        return self._get_trending_from_entries(limit, recent_hours)

    def _get_trending_from_profiles(
        self,
        limit: int,
        recent_hours: int
    ) -> List[Dict[str, Any]]:
        """Get trending content from ContentProfiles (preferred method)."""
        try:
            # Get recent profiles from registry
            profiles = self._registry.get_recent_profiles(limit=100, recent_hours=recent_hours)
            if not profiles:
                return []
        except Exception:
            return []

        # Build a map of entry_id -> profile and collect all profiles for overlap calculation
        entry_profiles: Dict[str, ContentProfile] = {p.entry_id: p for p in profiles}

        # Score each profile
        scored: List[tuple] = []
        for profile in profiles:
            entry_id = profile.entry_id
            score = self._calculate_trending_score(profile, profiles)

            entry_info = self._get_entry_info(entry_id)
            if entry_info.get("title"):
                scored.append((entry_id, profile, score, entry_info))

        # Sort by score descending
        scored.sort(key=lambda x: x[2], reverse=True)

        # Build recommendations
        recommendations = []
        for entry_id, profile, score, info in scored[:limit]:
            recommendations.append({
                "entry_id": entry_id,
                "trending_score": score,
                "title": info.get("title", ""),
                "url": info.get("url", ""),
                "feed_name": info.get("feed_name", ""),
                "source": "trending",
                "priority": profile.priority,  # include ontology priority for debugging
            })

        return recommendations

    def _get_trending_from_entries(
        self,
        limit: int,
        recent_hours: int
    ) -> List[Dict[str, Any]]:
        """Fallback: get trending content from raw entries."""
        try:
            from src.storage.singleton import get_storage
            storage = get_storage()

            cutoff_time = int(datetime.now().timestamp()) - (recent_hours * 3600)
            recent_entries_data = storage.get_entries(after=cutoff_time)
        except Exception:
            return []

        scored_entries: Dict[str, tuple] = {}

        for entry_data in recent_entries_data:
            entry = entry_data.get("entry")
            if not entry:
                continue

            entry_id = entry_data.get("id") or entry.id

            if entry_id in scored_entries:
                continue

            score = self._calculate_trending_score_from_entry(entry, recent_entries_data)
            entry_info = self._get_entry_info(entry_id)
            scored_entries[entry_id] = (entry, score, entry_info)

        sorted_entries = sorted(
            scored_entries.values(),
            key=lambda x: x[1],
            reverse=True
        )

        recommendations = []
        for entry, score, info in sorted_entries[:limit]:
            recommendations.append({
                "entry_id": entry.id if hasattr(entry, 'id') else entry_data.get("id"),
                "trending_score": score,
                "title": info.get("title", ""),
                "url": info.get("url", ""),
                "feed_name": info.get("feed_name", ""),
                "source": "trending",
            })

        return recommendations

    def _calculate_trending_score(
        self,
        profile: ContentProfile,
        all_profiles: List[ContentProfile]
    ) -> float:
        """
        Calculate trending score based on ContentProfile data.

        Uses pre-computed priority from ontology processing.
        """
        score = 0.0

        # Priority contribution (0-5 scale normalized)
        score += (profile.priority / 5.0) * 0.4

        # Entity overlap (content about same entities is trending)
        if profile.key_entities:
            entity_overlap = self._count_entity_overlap(profile, all_profiles)
            score += min(0.3, entity_overlap * 0.05)

        # Tag concentration (multiple sources about same topics)
        if profile.tags:
            tag_overlap = self._count_tag_overlap(profile, all_profiles)
            score += min(0.2, tag_overlap * 0.02)

        return min(1.0, score)

    def _count_entity_overlap(
        self,
        profile: ContentProfile,
        all_profiles: List[ContentProfile]
    ) -> int:
        """Count how many other profiles share key entities."""
        if not profile.key_entities:
            return 0

        overlap_count = 0
        profile_entities = set(e.lower() for e in profile.key_entities)

        for other in all_profiles:
            if other.entry_id == profile.entry_id:
                continue
            other_entities = set(e.lower() for e in other.key_entities)
            overlap = len(profile_entities & other_entities)
            if overlap > 0:
                overlap_count += 1

        return overlap_count

    def _count_tag_overlap(
        self,
        profile: ContentProfile,
        all_profiles: List[ContentProfile]
    ) -> int:
        """Count how many other profiles share tags (at least 2 shared)."""
        if not profile.tags:
            return 0

        overlap_count = 0
        profile_tags = set(t.name.lower() for t in profile.tags)

        for other in all_profiles:
            if other.entry_id == profile.entry_id:
                continue
            other_tags = set(t.name.lower() for t in other.tags)
            overlap = len(profile_tags & other_tags)
            if overlap >= 2:
                overlap_count += 1

        return overlap_count

    def _calculate_trending_score_from_entry(
        self,
        entry,
        all_entries_data: List
    ) -> float:
        """Fallback: calculate trending score from raw entry data."""
        score = 0.0

        # Total score contribution
        total_score = getattr(entry, 'total_score', 0) or 0
        score += (total_score / 10.0) * 0.3

        # Entity overlap
        entry_tags = getattr(entry, 'tags', []) or []
        entry_entities = [t.get("name", "") for t in entry_tags if t.get("is_entity")]
        if entry_entities:
            entity_overlap = self._count_entity_overlap_from_entry(entry, entry_entities, all_entries_data)
            score += min(0.3, entity_overlap * 0.05)

        # Tag overlap
        if entry_tags:
            tag_overlap = self._count_tag_overlap_from_entry(entry, entry_tags, all_entries_data)
            score += min(0.2, tag_overlap * 0.02)

        # Source authority bonus
        source_bonus = self._get_source_authority_bonus_from_entry(entry)
        score += source_bonus * 0.2

        return min(1.0, score)

    def _count_entity_overlap_from_entry(
        self,
        entry,
        entry_entities: List[str],
        all_entries_data: List
    ) -> int:
        """Count how many other entries share key entities."""
        if not entry_entities:
            return 0

        overlap_count = 0
        entry_id = getattr(entry, 'id', None)
        entry_entities_set = set(e.lower() for e in entry_entities)

        for other_data in all_entries_data:
            other = other_data.get("entry")
            if not other or getattr(other, 'id', None) == entry_id:
                continue
            other_tags = getattr(other, 'tags', []) or []
            other_entities = set(t.get("name", "").lower() for t in other_tags if t.get("is_entity"))
            overlap = len(entry_entities_set & other_entities)
            if overlap > 0:
                overlap_count += 1

        return overlap_count

    def _count_tag_overlap_from_entry(
        self,
        entry,
        entry_tags: List,
        all_entries_data: List
    ) -> int:
        """Count how many other entries share tags (at least 2 shared)."""
        if not entry_tags:
            return 0

        overlap_count = 0
        entry_id = getattr(entry, 'id', None)
        entry_tags_set = set(t.get("name", "").lower() for t in entry_tags)

        for other_data in all_entries_data:
            other = other_data.get("entry")
            if not other or getattr(other, 'id', None) == entry_id:
                continue
            other_tags = getattr(other, 'tags', []) or []
            other_tags_set = set(t.get("name", "").lower() for t in other_tags)
            overlap = len(entry_tags_set & other_tags_set)
            if overlap >= 2:
                overlap_count += 1

        return overlap_count

    def _get_source_authority_bonus_from_entry(self, entry) -> float:
        """Get authority bonus based on entry's feed name."""
        feed_name = getattr(entry, 'feed_name', None)
        if not feed_name:
            feed_id = getattr(entry, 'feed_id', None)
            if feed_id:
                try:
                    from src.storage.singleton import get_storage
                    storage = get_storage()
                    feed = storage.get_feed(feed_id)
                    feed_name = feed.name if feed else ""
                except Exception:
                    feed_name = ""

        feed_name_lower = feed_name.lower() if feed_name else ""

        if any(x in feed_name_lower for x in ["fda", "ema", "nih", "regulatory"]):
            return 1.0
        if any(x in feed_name_lower for x in ["nature", "science", "arxiv", "medrxiv"]):
            return 0.8
        if any(x in feed_name_lower for x in ["stat", "fierce", "endpoints", "biotech"]):
            return 0.6
        return 0.4

    def _get_entry_info(self, entry_id: str) -> Dict[str, Any]:
        """Get basic entry info."""
        try:
            from src.storage.singleton import get_storage
            storage = get_storage()
            entry = storage.get_feed_entry(entry_id)
            feed = storage.get_feed(entry.feed_id)

            from src.backend import EntroFeedBackend
            backend = EntroFeedBackend(db=storage)

            return {
                "title": entry.title,
                "url": entry.url,
                "feed_name": feed.name,
                "published_at": backend._format_time(entry.published_at),
            }
        except Exception:
            return {}


def get_trending_recommendations(
    limit: int = 10,
    recent_hours: int = 24
) -> List[Dict[str, Any]]:
    """
    Convenience function for getting trending recommendations.

    Args:
        limit: Maximum number of recommendations
        recent_hours: Consider content from last N hours

    Returns:
        List of trending entries
    """
    recommender = TrendingRecommender()
    return recommender.recommend(limit, recent_hours)


__all__ = ["TrendingRecommender", "get_trending_recommendations"]

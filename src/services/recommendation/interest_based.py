# -*- coding: utf-8 -*-
"""
Interest-Based Recommender - Recommend content based on user interests.
"""
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime, timedelta

from src.ontology.types import UserInterest, ContentProfile
from src.ontology.domain_hierarchy import (
    detect_domains_in_text,
    get_cross_domain_parents,
    calculate_cross_domain_score,
)

if TYPE_CHECKING:
    from src.ontology.memory import OntologyMemory


class InterestBasedRecommender:
    """
    Recommend content based on user's tracked interests.

    Scores content by how well it matches:
    - User's high-priority interests
    - Recent reading patterns
    - Explicitly added interests (highest weight)
    - Cross-domain concepts (e.g., AI+Medical = MedicalAI)
    """

    def __init__(self, memory=None):
        """
        Initialize interest-based recommender.

        Args:
            memory: OntologyMemory instance (uses global if not provided)
        """
        self.memory = memory

    @property
    def _memory(self):
        if self.memory is None:
            from src.ontology import get_ontology_registry
            self.memory = get_ontology_registry().memory
        return self.memory

    def recommend(
        self,
        limit: int = 10,
        recent_hours: int = 72
    ) -> List[Dict[str, Any]]:
        """
        Get recommendations based on user interests.

        Args:
            limit: Maximum number of recommendations
            recent_hours: Only consider content from last N hours

        Returns:
            List of recommended entries with match scores
        """
        # Get user interests
        try:
            user_interests = self._memory.get_all_user_interests()
        except Exception:
            user_interests = []

        if not user_interests:
            return []

        # Sort by priority (highest first)
        sorted_interests = sorted(
            user_interests,
            key=lambda x: (x.priority, x.relevance_score),
            reverse=True
        )

        # Get recent entries directly from storage (not from content_profiles which may be empty)
        try:
            from src.storage.singleton import get_storage
            storage = get_storage()

            # Calculate cutoff time
            cutoff_time = int(datetime.now().timestamp()) - (recent_hours * 3600)

            # Get recent entries from storage
            recent_entries_data = storage.get_entries(after=cutoff_time)
        except Exception:
            recent_entries_data = []

        # Score each entry
        scored_entries: List[tuple] = []
        for entry_data in recent_entries_data:
            entry = entry_data.get("entry")
            if not entry:
                continue

            entry_id = entry_data.get("id") or entry.id
            content_text = f"{entry.title} {entry.preview or ''} {entry.content or ''}"

            # Convert entry tags to InterestTag-like format for scoring
            entry_tags = []
            if entry.tags:
                for t in entry.tags:
                    if isinstance(t, dict):
                        from src.ontology.types import InterestTag, InterestCategory, TagSource
                        try:
                            cat = InterestCategory(t.get("category", "other"))
                        except ValueError:
                            cat = InterestCategory.OTHER
                        entry_tags.append(InterestTag(
                            name=t.get("name", "").lower(),
                            category=cat,
                            confidence=t.get("confidence", 0.5),
                            source=TagSource.INFERENCE
                        ))

            score = self._calculate_interest_score_from_entry(entry, entry_tags, sorted_interests, content_text)
            if score > 0:
                scored_entries.append((entry_id, entry, score))

        # Sort by score descending
        scored_entries.sort(key=lambda x: x[2], reverse=True)

        # Build recommendations
        recommendations = []
        seen_entries = set()

        for entry_id, entry, score in scored_entries:
            if entry_id in seen_entries:
                continue

            seen_entries.add(entry_id)
            entry_info = self._get_entry_info(entry_id)

            recommendations.append({
                "entry_id": entry_id,
                "match_score": score,
                "title": entry_info.get("title", ""),
                "url": entry_info.get("url", ""),
                "feed_name": entry_info.get("feed_name", ""),
                "published_at": entry_info.get("published_at", ""),
                "matched_interest": self._get_matched_interest_from_entry(entry, sorted_interests),
                "cross_domain_tags": self._get_cross_domain_tags(content_text),
                "source": "interest",
            })

            if len(recommendations) >= limit:
                break

        return recommendations

    def _calculate_interest_score(
        self,
        profile: ContentProfile,
        user_interests: List[UserInterest],
        content_text: str = ""
    ) -> float:
        """
        Calculate how well content matches user interests.

        Score = sum(tag_match * interest_priority * interest_relevance)
        With cross-domain bonus for multi-domain content (e.g., AI+Medical).
        """
        if not profile.tags and not content_text:
            return 0.0

        total_score = 0.0
        profile_tag_names = {t.name.lower() for t in profile.tags}
        profile_categories = {t.category for t in profile.tags}

        # Detect cross-domain concepts in content
        detected_domains = []
        if content_text:
            detected_domains = detect_domains_in_text(content_text)

        for interest in user_interests:
            tag = interest.tag
            tag_score = 0.0
            match_type = "exact"

            # Exact tag name match (highest weight)
            if tag.name.lower() in profile_tag_names:
                tag_score = 1.0
            # Category match (medium weight)
            elif tag.category in profile_categories:
                tag_score = 0.5
            # Cross-domain match
            elif detected_domains:
                cross_score = self._cross_domain_match(
                    tag.name.lower(),
                    tag.category.value if hasattr(tag.category, 'value') else str(tag.category),
                    detected_domains
                )
                if cross_score > 0:
                    tag_score = cross_score
                    match_type = "cross_domain"
            # Fuzzy match (lower weight)
            else:
                for pt in profile.tags:
                    if tag.name.lower() in pt.name.lower() or pt.name.lower() in tag.name.lower():
                        tag_score = 0.3
                        match_type = "fuzzy"
                        break

            if tag_score > 0:
                # Weight by priority (0-5) and relevance (0-1)
                weight = (interest.priority / 5.0) * interest.relevance_score
                total_score += tag_score * weight

        return min(1.0, total_score)

    def _cross_domain_match(
        self,
        interest_name: str,
        interest_category: str,
        detected_domains: List[Dict]
    ) -> float:
        """
        Calculate cross-domain match score.

        E.g., User interest: "machine learning" (technology)
              Content has "AI医疗" → detects MedicalAI domain
              → Cross-domain match between Technology and Medical
        """
        for domain_info in detected_domains:
            domain = domain_info["domain"]
            score = domain_info.get("score", 0.0)

            # Direct interest name in domain
            if interest_name in domain.lower():
                return 0.6 * score

            # Interest category is a cross-domain parent of detected domain
            cross_parents = get_cross_domain_parents(domain)
            if interest_category.lower() in [cp.lower() for cp in cross_parents]:
                return 0.5 * score

            # Wu-Palmer similarity for cross-domain
            for cross_parent in cross_parents:
                sim = calculate_cross_domain_score(interest_name, cross_parent.lower())
                if sim > 0.3:
                    return sim * 0.4 * score

        return 0.0

    def _get_cross_domain_tags(self, content_text: str) -> List[str]:
        """Get cross-domain tags detected in content."""
        if not content_text:
            return []

        detected = detect_domains_in_text(content_text)
        cross_domain_tags = []

        for domain_info in detected:
            # Only include level 2+ domains (cross-domain specific)
            if domain_info.get("level", 0) >= 2:
                cross_domain_tags.append(domain_info["domain"])

        return cross_domain_tags[:5]  # Limit to top 5

    def _get_matched_interest(
        self,
        profile: ContentProfile,
        user_interests: List[UserInterest]
    ) -> str:
        """Get the highest-matching user interest for a profile."""
        best_match = ""
        best_score = 0.0

        profile_tag_names = {t.name.lower() for t in profile.tags}

        for interest in user_interests:
            if interest.tag.name.lower() in profile_tag_names:
                score = interest.priority * interest.relevance_score
                if score > best_score:
                    best_score = score
                    best_match = interest.tag.name

        return best_match

    def _calculate_interest_score_from_entry(
        self,
        entry,
        entry_tags: List,
        user_interests: List[UserInterest],
        content_text: str = ""
    ) -> float:
        """
        Calculate how well an entry matches user interests.
        Works with FeedEntry tags (dict format) instead of ContentProfile tags.
        """
        if not entry_tags and not content_text:
            return 0.0

        total_score = 0.0
        entry_tag_names = {t.name.lower() for t in entry_tags}
        entry_categories = {t.category for t in entry_tags}

        # Detect cross-domain concepts in content
        detected_domains = []
        if content_text:
            detected_domains = detect_domains_in_text(content_text)

        for interest in user_interests:
            tag = interest.tag
            tag_score = 0.0
            match_type = "exact"

            # Exact tag name match (highest weight)
            if tag.name.lower() in entry_tag_names:
                tag_score = 1.0
            # Category match (medium weight)
            elif tag.category in entry_categories:
                tag_score = 0.5
            # Cross-domain match
            elif detected_domains:
                cross_score = self._cross_domain_match(
                    tag.name.lower(),
                    tag.category.value if hasattr(tag.category, 'value') else str(tag.category),
                    detected_domains
                )
                if cross_score > 0:
                    tag_score = cross_score
                    match_type = "cross_domain"
            # Fuzzy match (lower weight)
            else:
                for pt in entry_tags:
                    if tag.name.lower() in pt.name.lower() or pt.name.lower() in tag.name.lower():
                        tag_score = 0.3
                        match_type = "fuzzy"
                        break

            if tag_score > 0:
                # Weight by priority (0-5) and relevance (0-1)
                weight = (interest.priority / 5.0) * interest.relevance_score
                total_score += tag_score * weight

        return min(1.0, total_score)

    def _get_matched_interest_from_entry(
        self,
        entry,
        user_interests: List[UserInterest]
    ) -> str:
        """Get the highest-matching user interest for an entry."""
        best_match = ""
        best_score = 0.0

        # entry.tags is a list of dicts with 'name' key
        entry_tag_names = {t.get("name", "").lower() for t in entry.tags} if entry.tags else set()

        for interest in user_interests:
            if interest.tag.name.lower() in entry_tag_names:
                score = interest.priority * interest.relevance_score
                if score > best_score:
                    best_score = score
                    best_match = interest.tag.name

        return best_match

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


def get_interest_recommendations(
    limit: int = 10,
    recent_hours: int = 72
) -> List[Dict[str, Any]]:
    """
    Convenience function for getting interest-based recommendations.

    Args:
        limit: Maximum number of recommendations
        recent_hours: Only consider content from last N hours

    Returns:
        List of recommended entries
    """
    recommender = InterestBasedRecommender()
    return recommender.recommend(limit, recent_hours)


__all__ = ["InterestBasedRecommender", "get_interest_recommendations"]

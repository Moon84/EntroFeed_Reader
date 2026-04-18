# -*- coding: utf-8 -*-
"""
Interest-Based Recommender - Recommend content based on user interests.
"""
from typing import List, Dict, Any
from datetime import datetime

from src.services.ontology.types import UnifiedNode, ContentProfile, InterestTag, InterestCategory, TagSource
from src.services.ontology.domain_hierarchy import (
    detect_domains_in_text,
    get_cross_domain_parents,
    calculate_cross_domain_score,
)


class InterestBasedRecommender:
    """
    Recommend content based on user's tracked interests.

    Uses OntologyRegistry as the primary interface to access:
    - ContentProfile (pre-computed tags and priority)
    - UnifiedNode (user's tracked interests with is_interest=True)

    Falls back to raw entry processing only when no ContentProfile exists.
    """

    def __init__(self, registry=None):
        """
        Initialize interest-based recommender.

        Args:
            registry: OntologyRegistry instance (uses global if not provided)
        """
        self._registry_instance = registry

    @property
    def _registry(self):
        """Get OntologyRegistry facade (avoids direct memory access)."""
        if self._registry_instance is None:
            from src.services.ontology import get_ontology_registry
            self._registry_instance = get_ontology_registry()
        return self._registry_instance

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
        # Get user interests through registry
        try:
            user_interests = self._registry.get_user_interests()
        except Exception:
            user_interests = []

        if not user_interests:
            return []

        # Sort by priority (highest first)
        sorted_interests = sorted(
            user_interests,
            key=lambda x: (x.interest_priority, x.interest_level),
            reverse=True
        )

        # Get recent profiles from ontology (preferred) and entries (fallback)
        try:
            from src.storage.singleton import get_storage
            storage = get_storage()

            cutoff_time = int(datetime.now().timestamp()) - (recent_hours * 3600)
            recent_entries_data = storage.get_entries(after=cutoff_time)
        except Exception:
            recent_entries_data = []

        # Build a map of entry_id -> ContentProfile from registry
        entry_profiles: Dict[str, ContentProfile] = {}
        for entry_data in recent_entries_data:
            entry = entry_data.get("entry")
            if not entry:
                continue
            entry_id = entry_data.get("id") or entry.id
            profile = self._registry.get_content_profile(entry_id)
            if profile:
                entry_profiles[entry_id] = profile

        # Score entries - prefer ContentProfile when available
        scored_entries: List[tuple] = []
        for entry_data in recent_entries_data:
            entry = entry_data.get("entry")
            if not entry:
                continue

            entry_id = entry_data.get("id") or entry.id
            profile = entry_profiles.get(entry_id)
            content_text = f"{entry.title} {entry.preview or ''} {entry.content or ''}"

            if profile:
                # Use pre-computed ContentProfile
                score = self._calculate_interest_score(profile, sorted_interests, content_text)
                if score > 0:
                    scored_entries.append((entry_id, entry, score, profile))
            else:
                # Fallback: convert raw entry tags to InterestTag format
                entry_tags = self._convert_entry_tags(entry)
                if entry_tags or content_text:
                    score = self._calculate_interest_score_from_entry(entry, entry_tags, sorted_interests, content_text)
                    if score > 0:
                        scored_entries.append((entry_id, entry, score, None))

        # Sort by score descending
        scored_entries.sort(key=lambda x: x[2], reverse=True)

        # Build recommendations
        recommendations = []
        seen_entries = set()

        for entry_id, entry, score, profile in scored_entries:
            if entry_id in seen_entries:
                continue

            seen_entries.add(entry_id)
            entry_info = self._get_entry_info(entry_id)

            # Use profile tags if available, otherwise entry tags
            if profile:
                matched_interest = self._get_matched_interest(profile, sorted_interests)
                cross_domain_tags = self._get_cross_domain_tags_from_profile(profile, content_text)
            else:
                matched_interest = self._get_matched_interest_from_entry(entry, sorted_interests)
                cross_domain_tags = self._get_cross_domain_tags(content_text)

            recommendations.append({
                "entry_id": entry_id,
                "match_score": score,
                "title": entry_info.get("title", ""),
                "url": entry_info.get("url", ""),
                "feed_name": entry_info.get("feed_name", ""),
                "published_at": entry_info.get("published_at", ""),
                "matched_interest": matched_interest,
                "cross_domain_tags": cross_domain_tags,
                "source": "interest",
            })

            if len(recommendations) >= limit:
                break

        return recommendations

    def _convert_entry_tags(self, entry) -> List[InterestTag]:
        """Convert raw entry tags to InterestTag list."""
        entry_tags = []
        if entry.tags:
            for t in entry.tags:
                if isinstance(t, dict):
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
        return entry_tags

    def _calculate_interest_score(
        self,
        profile: ContentProfile,
        user_interests: List[UnifiedNode],
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
            tag_name = interest.name
            tag_category = interest.category
            tag_score = 0.0
            match_type = "exact"

            # Exact tag name match (highest weight)
            if tag_name.lower() in profile_tag_names:
                tag_score = 1.0
            # Category match (medium weight)
            elif tag_category in profile_categories:
                tag_score = 0.5
            # Cross-domain match
            elif detected_domains:
                cross_score = self._cross_domain_match(
                    tag_name.lower(),
                    tag_category.value if hasattr(tag_category, 'value') else str(tag_category),
                    detected_domains
                )
                if cross_score > 0:
                    tag_score = cross_score
                    match_type = "cross_domain"
            # Fuzzy match (lower weight)
            else:
                for pt in profile.tags:
                    if tag_name.lower() in pt.name.lower() or pt.name.lower() in tag_name.lower():
                        tag_score = 0.3
                        match_type = "fuzzy"
                        break

            if tag_score > 0:
                # Weight by priority (0-5) and relevance (0-1)
                weight = (interest.interest_priority / 5.0) * interest.interest_level
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
        user_interests: List[UnifiedNode]
    ) -> str:
        """Get the highest-matching user interest for a profile."""
        best_match = ""
        best_score = 0.0

        profile_tag_names = {t.name.lower() for t in profile.tags}

        for interest in user_interests:
            if interest.name.lower() in profile_tag_names:
                score = interest.interest_priority * interest.interest_level
                if score > best_score:
                    best_score = score
                    best_match = interest.name

        return best_match

    def _get_cross_domain_tags_from_profile(
        self,
        profile: ContentProfile,
        content_text: str
    ) -> List[str]:
        """Get cross-domain tags from profile and content text."""
        if not content_text:
            return []
        return self._get_cross_domain_tags(content_text)

    def _calculate_interest_score_from_entry(
        self,
        entry,
        entry_tags: List,
        user_interests: List[UnifiedNode],
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
            tag_name = interest.name
            tag_category = interest.category
            tag_score = 0.0
            match_type = "exact"

            # Exact tag name match (highest weight)
            if tag_name.lower() in entry_tag_names:
                tag_score = 1.0
            # Category match (medium weight)
            elif tag_category in entry_categories:
                tag_score = 0.5
            # Cross-domain match
            elif detected_domains:
                cross_score = self._cross_domain_match(
                    tag_name.lower(),
                    tag_category.value if hasattr(tag_category, 'value') else str(tag_category),
                    detected_domains
                )
                if cross_score > 0:
                    tag_score = cross_score
                    match_type = "cross_domain"
            # Fuzzy match (lower weight)
            else:
                for pt in entry_tags:
                    if tag_name.lower() in pt.name.lower() or pt.name.lower() in tag_name.lower():
                        tag_score = 0.3
                        match_type = "fuzzy"
                        break

            if tag_score > 0:
                # Weight by priority (0-5) and relevance (0-1)
                weight = (interest.interest_priority / 5.0) * interest.interest_level
                total_score += tag_score * weight

        return min(1.0, total_score)

    def _get_matched_interest_from_entry(
        self,
        entry,
        user_interests: List[UnifiedNode]
    ) -> str:
        """Get the highest-matching user interest for an entry."""
        best_match = ""
        best_score = 0.0

        # entry.tags is a list of dicts with 'name' key
        entry_tag_names = {t.get("name", "").lower() for t in entry.tags} if entry.tags else set()

        for interest in user_interests:
            if interest.name.lower() in entry_tag_names:
                score = interest.interest_priority * interest.interest_level
                if score > best_score:
                    best_score = score
                    best_match = interest.name

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

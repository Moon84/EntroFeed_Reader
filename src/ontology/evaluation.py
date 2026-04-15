# -*- coding: utf-8 -*-
"""
Ontology Evaluation - Priority and relevance evaluation engine.

This module provides:
- Priority calculation for content
- Relevance scoring for user interests
- Interest decay and boosting
"""
from datetime import datetime
from typing import Dict, List, Optional, Any

from src.ontology.types import (
    InterestTag,
    UserInterest,
    ContentProfile,
    TagSource,
    InterestCategory,
)
from src.ontology.tagging import TagMatcher


class PriorityEvaluator:
    """Evaluate content priority based on user interests."""

    def __init__(self, tag_matcher: TagMatcher = None):
        """Initialize priority evaluator.

        Args:
            tag_matcher: Tag matcher for calculating relevance.
        """
        self.tag_matcher = tag_matcher or TagMatcher()

    def evaluate_content_priority(
        self,
        profile: ContentProfile,
        user_interests: List[UserInterest]
    ) -> int:
        """Evaluate content priority (0-5).

        Args:
            profile: Content profile with tags
            user_interests: User's tracked interests

        Returns:
            Priority score 0-5
        """
        if not profile.tags:
            return 0

        return self.tag_matcher.calculate_priority(
            profile.tags,
            user_interests
        )

    def evaluate_batch_priority(
        self,
        profiles: List[ContentProfile],
        user_interests: List[UserInterest]
    ) -> List[int]:
        """Evaluate priority for multiple content profiles.

        Returns:
            List of priority scores aligned with input profiles
        """
        return [
            self.evaluate_content_priority(p, user_interests)
            for p in profiles
        ]


class InterestUpdater:
    """Update user interests based on reading behavior."""

    # Decay rates
    DAILY_DECAY_RATE = 0.01  # 1% per day
    READING_BOOST = 0.05     # 5% boost when accessed
    HIGH_PRIORITY_BOOST = 0.1  # 10% boost for high priority content

    def __init__(self):
        pass

    def update_interests_on_read(
        self,
        content_tags: List[InterestTag],
        content_priority: int,
        user_interests: List[UserInterest]
    ) -> List[UserInterest]:
        """Update user interests after reading content.

        Args:
            content_tags: Tags from the content read
            content_priority: Calculated priority of the content
            user_interests: Current user interests

        Returns:
            Updated user interests
        """
        updated = {i.id: i for i in user_interests}
        now = datetime.now().isoformat()

        for tag in content_tags:
            existing = self._find_existing_interest(tag, list(updated.values()))

            if existing:
                # Update existing interest
                existing.mark_accessed()
                if content_priority >= 4:
                    existing.relevance_score = min(
                        1.0,
                        existing.relevance_score + self.HIGH_PRIORITY_BOOST
                    )
                existing.priority = max(
                    existing.priority,
                    content_priority // 2
                )
            else:
                # Create new interest
                new_interest = UserInterest(
                    tag=tag,
                    priority=content_priority // 2,
                    access_count=1,
                    last_accessed=now,
                    relevance_score=0.3 + (content_priority * 0.05)
                )
                updated[new_interest.id] = new_interest

        return list(updated.values())

    def decay_interests(
        self,
        user_interests: List[UserInterest],
        days_since_last_update: int
    ) -> List[UserInterest]:
        """Apply time-based decay to user interests.

        Args:
            user_interests: Current user interests
            days_since_last_update: Number of days since last decay

        Returns:
            Decayed user interests
        """
        decay_amount = days_since_last_update * self.DAILY_DECAY_RATE

        for interest in user_interests:
            # Only decay if not recently accessed
            if interest.last_accessed:
                last_access = datetime.fromisoformat(interest.last_accessed)
                days_ago = (datetime.now() - last_access).days
                if days_ago > 7:  # Don't decay if accessed within a week
                    interest.relevance_score = max(
                        0.1,
                        interest.relevance_score - decay_amount
                    )

        return user_interests

    def boost_interest(
        self,
        interest_id: str,
        user_interests: List[UserInterest],
        boost_amount: float = 0.1
    ) -> Optional[UserInterest]:
        """Boost a specific interest.

        Args:
            interest_id: ID of interest to boost
            user_interests: Current user interests
            boost_amount: Amount to boost (0.0-1.0)

        Returns:
            Updated interest or None if not found
        """
        for interest in user_interests:
            if interest.id == interest_id:
                interest.relevance_score = min(
                    1.0,
                    interest.relevance_score + boost_amount
                )
                return interest
        return None

    def _find_existing_interest(
        self,
        tag: InterestTag,
        user_interests: List[UserInterest]
    ) -> Optional[UserInterest]:
        """Find existing interest matching the tag."""
        for interest in user_interests:
            if (interest.tag.name.lower() == tag.name.lower() or
                interest.tag.category == tag.category):
                return interest
        return None


class InterestInferrer:
    """Infer new user interests from behavior patterns."""

    COMMON_INTERESTS = {
        # Technology
        "ai": InterestCategory.TECHNOLOGY,
        "machine learning": InterestCategory.TECHNOLOGY,
        "python": InterestCategory.TECHNOLOGY,
        "startup": InterestCategory.BUSINESS,
        "software": InterestCategory.TECHNOLOGY,
        # Medical
        "health": InterestCategory.MEDICAL,
        "medical": InterestCategory.MEDICAL,
        "doctor": InterestCategory.MEDICAL,
        # Finance
        "stock": InterestCategory.FINANCE,
        "market": InterestCategory.FINANCE,
        "investment": InterestCategory.FINANCE,
        # Science
        "research": InterestCategory.SCIENCE,
        "study": InterestCategory.SCIENCE,
        "space": InterestCategory.SCIENCE,
    }

    def infer_from_reading_history(
        self,
        profiles: List[ContentProfile],
        existing_interests: List[UserInterest],
        min_confidence: float = 0.3
    ) -> List[InterestTag]:
        """Infer new interests from reading history.

        Args:
            profiles: Content profiles from reading history
            existing_interests: Current user interests
            min_confidence: Minimum confidence threshold

        Returns:
            List of inferred interest tags
        """
        existing_tag_names = {i.tag.name.lower() for i in existing_interests}
        existing_categories = {i.tag.category for i in existing_interests}

        tag_counts: Dict[str, int] = {}

        # Count tag occurrences
        for profile in profiles:
            for tag in profile.tags:
                if tag.name.lower() not in existing_tag_names:
                    if tag.confidence >= min_confidence:
                        tag_counts[tag.name.lower()] = \
                            tag_counts.get(tag.name.lower(), 0) + 1

        # Infer new tags based on frequency
        inferred = []
        for tag_name, count in tag_counts.items():
            if count >= 2:  # At least 2 occurrences
                category = self.COMMON_INTERESTS.get(
                    tag_name,
                    InterestCategory.OTHER
                )

                # Don't infer if we already have this category strongly
                existing_same_cat = [
                    i for i in existing_interests
                    if i.tag.category == category
                ]
                if existing_same_cat and max(i.relevance_score for i in existing_same_cat) > 0.7:
                    continue

                confidence = min(0.9, 0.2 + (count * 0.1))
                inferred.append(InterestTag(
                    name=tag_name,
                    category=category,
                    confidence=confidence,
                    source=TagSource.INFERENCE
                ))

        return inferred


__all__ = [
    "PriorityEvaluator",
    "InterestUpdater",
    "InterestInferrer",
]

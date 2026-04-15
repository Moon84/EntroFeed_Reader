# -*- coding: utf-8 -*-
"""
Ontology Registry - Main registry for ontology operations.

This module provides a unified interface for:
- Managing user interests
- Processing content profiles
- Tagging and evaluation
"""
from typing import Dict, List, Optional, Any, Callable

from src.ontology.memory import OntologyMemory
from src.ontology.types import (
    InterestTag,
    UserInterest,
    ContentProfile,
    InterestCategory,
    TagSource,
)
from src.ontology.tagging import TagGenerator, TagMatcher
from src.ontology.evaluation import (
    PriorityEvaluator,
    InterestUpdater,
    InterestInferrer,
)
from src.models import Feed, FeedEntry


class OntologyRegistry:
    """Main registry for ontology operations."""

    def __init__(
        self,
        data_dir: str = None,
        llm_summarizer: Callable[[Feed, FeedEntry, str], str] = None
    ):
        """Initialize ontology registry.

        Args:
            data_dir: Data directory for storage
            llm_summarizer: Optional LLM function for content analysis
        """
        self.memory = OntologyMemory(data_dir=data_dir)
        self.tag_generator = TagGenerator(llm_summarizer=llm_summarizer)
        self.tag_matcher = TagMatcher()
        self.priority_evaluator = PriorityEvaluator(tag_matcher=self.tag_matcher)
        self.interest_updater = InterestUpdater()
        self.interest_inferrer = InterestInferrer()

    # ============ Content Processing ============

    def process_content(
        self,
        entry: FeedEntry,
        feed: Feed,
        content: str = None,
        save: bool = True
    ) -> ContentProfile:
        """Process content and extract tags/entities.

        Args:
            entry: Feed entry to process
            feed: Parent feed
            content: Optional full content
            save: Whether to save to storage

        Returns:
            ContentProfile with extracted data
        """
        # Extract tags and create profile
        profile = self.tag_generator.extract_tags(entry, feed, content)

        # Calculate priority based on user interests
        user_interests = self.memory.get_all_user_interests()
        priority = self.priority_evaluator.evaluate_content_priority(
            profile,
            user_interests
        )
        profile.priority = priority

        if save:
            self.memory.save_content_profile(profile)

        return profile

    def process_batch(
        self,
        entries: List[FeedEntry],
        feeds: Dict[str, Feed]
    ) -> List[ContentProfile]:
        """Process multiple entries.

        Args:
            entries: List of entries to process
            feeds: Dict mapping feed_id to Feed

        Returns:
            List of ContentProfiles
        """
        profiles = []
        for entry in entries:
            feed = feeds.get(entry.feed_id)
            if feed:
                profile = self.process_content(entry, feed, save=True)
                profiles.append(profile)
        return profiles

    # ============ User Interest Management ============

    def get_user_interests(
        self,
        category: InterestCategory = None
    ) -> List[UserInterest]:
        """Get user interests.

        Args:
            category: Optional category filter

        Returns:
            List of UserInterest
        """
        if category:
            return self.memory.get_user_interests_by_category(category)
        return self.memory.get_all_user_interests()

    def add_interest(
        self,
        tag: InterestTag,
        priority: int = 3
    ) -> UserInterest:
        """Add explicit user interest.

        Args:
            tag: Interest tag
            priority: Initial priority (0-5)

        Returns:
            Created UserInterest
        """
        tag.source = TagSource.EXPLICIT
        interest = UserInterest(
            tag=tag,
            priority=priority,
            relevance_score=0.8 if tag.source == TagSource.EXPLICIT else 0.3
        )
        self.memory.save_user_interest(interest)
        return interest

    def remove_interest(self, interest_id: str) -> bool:
        """Remove user interest.

        Args:
            interest_id: ID of interest to remove

        Returns:
            True if removed
        """
        return self.memory.delete_user_interest(interest_id)

    def update_interest_priority(
        self,
        interest_id: str,
        priority: int
    ) -> Optional[UserInterest]:
        """Update interest priority.

        Args:
            interest_id: ID of interest
            priority: New priority (0-5)

        Returns:
            Updated interest or None
        """
        interest = self.memory.get_user_interest(interest_id)
        if interest:
            interest.priority = max(0, min(5, priority))
            self.memory.save_user_interest(interest)
        return interest

    # ============ Reading Behavior ============

    def on_content_read(
        self,
        entry_id: str,
        content_priority: int = 0
    ) -> None:
        """Handle content read event.

        Updates user interests based on what was read.

        Args:
            entry_id: ID of entry that was read
            content_priority: Calculated priority
        """
        profile = self.memory.get_content_profile(entry_id)
        if not profile:
            return

        user_interests = self.memory.get_all_user_interests()

        # Update interests
        updated = self.interest_updater.update_interests_on_read(
            profile.tags,
            content_priority or profile.priority,
            user_interests
        )

        # Save updated interests
        for interest in updated:
            self.memory.save_user_interest(interest)

    def apply_decay(self, days: int = 7) -> None:
        """Apply interest decay.

        Args:
            days: Number of days to simulate decay for
        """
        interests = self.memory.get_all_user_interests()
        decayed = self.interest_updater.decay_interests(interests, days)

        for interest in decayed:
            self.memory.save_user_interest(interest)

    # ============ Interest Inference ============

    def infer_new_interests(
        self,
        max_new: int = 5,
        min_confidence: float = 0.3
    ) -> List[InterestTag]:
        """Infer new interests from reading history.

        Args:
            max_new: Maximum number of new interests to return
            min_confidence: Minimum confidence threshold

        Returns:
            List of inferred InterestTags
        """
        # Get recent profiles
        recent = self.memory.get_recent_profiles(limit=50)
        existing = self.memory.get_all_user_interests()

        # Infer
        inferred = self.interest_inferrer.infer_from_reading_history(
            recent,
            existing,
            min_confidence
        )

        return inferred[:max_new]

    def accept_inferred_interest(
        self,
        tag: InterestTag,
        priority: int = 2
    ) -> UserInterest:
        """Accept an inferred interest as explicit.

        Args:
            tag: Inferred tag to accept
            priority: Initial priority

        Returns:
            Created UserInterest
        """
        tag.source = TagSource.EXPLICIT
        return self.add_interest(tag, priority)

    # ============ Content Search ============

    def search_similar(
        self,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for similar content using vectors.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of similar content results
        """
        return self.memory.search_similar_content(query, limit)

    def get_content_by_priority(
        self,
        min_priority: int = 3,
        limit: int = 20
    ) -> List[ContentProfile]:
        """Get high-priority content.

        Args:
            min_priority: Minimum priority threshold
            limit: Maximum results

        Returns:
            List of ContentProfiles
        """
        profiles = self.memory.get_recent_profiles(limit=100)
        return [p for p in profiles if p.priority >= min_priority][:limit]

    # ============ Cleanup ============

    def close(self):
        """Close storage connections."""
        self.memory.close()


# Singleton instance
_registry: Optional[OntologyRegistry] = None


def get_ontology_registry() -> OntologyRegistry:
    """Get or create singleton ontology registry."""
    global _registry
    if _registry is None:
        _registry = OntologyRegistry()
    return _registry


__all__ = [
    "OntologyRegistry",
    "get_ontology_registry",
]

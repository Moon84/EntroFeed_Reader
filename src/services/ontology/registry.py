# -*- coding: utf-8 -*-
"""
Ontology Registry - Main registry for ontology operations.

This module provides a unified interface for:
- Managing user interests
- Processing content profiles
- Tagging and evaluation
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

from .memory import OntologyMemory
from .types import (
    InterestTag,
    UserInterest,
    ContentProfile,
    InterestCategory,
    TagSource,
)
from .tagging import TagGenerator, TagMatcher
from .evaluation import (
    PriorityEvaluator,
    InterestUpdater,
    InterestInferrer,
)
from src.models.feed import Feed, FeedEntry


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

        # Initialize Wikidata resolver
        from .wikidata import WikidataResolver
        self.wikidata_resolver = WikidataResolver(
            cache_db_path=self.memory.data_dir / "wikidata_cache.db"
        )

        # Initialize domain graph
        from .domain_graph import DomainGraph
        self.domain_graph = DomainGraph(
            memory=self.memory,
            wikidata=self.wikidata_resolver,
            llm_handler=llm_summarizer
        )

        # Initialize tag generator with Wikidata support
        self.tag_generator = TagGenerator(
            llm_summarizer=llm_summarizer,
            wikidata_resolver=self.wikidata_resolver
        )

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

        # Use the calculated priority
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

    def on_entry_liked(
        self,
        entry_id: str,
        is_favorited: bool = False
    ) -> None:
        """Handle entry liked/favorited event.

        Boosts relevance for tags in liked content.

        Args:
            entry_id: ID of entry that was liked
            is_favorited: True if this was a favorite
        """
        profile = self.memory.get_content_profile(entry_id)
        if not profile or not profile.tags:
            return

        user_interests = self.memory.get_all_user_interests()

        # Update interests with like boost
        updated = self.interest_updater.update_interests_on_like(
            profile.tags,
            user_interests,
            is_favorited=is_favorited
        )

        # Save updated interests
        for interest in updated:
            self.memory.save_user_interest(interest)

    def on_entry_disliked(self, entry_id: str) -> None:
        """Handle entry disliked event.

        Decays relevance for tags in disliked content.

        Args:
            entry_id: ID of entry that was disliked
        """
        profile = self.memory.get_content_profile(entry_id)
        if not profile or not profile.tags:
            return

        user_interests = self.memory.get_all_user_interests()

        # Update interests with dislike decay
        updated = self.interest_updater.update_interests_on_dislike(
            profile.tags,
            user_interests
        )

        # Save updated interests
        for interest in updated:
            self.memory.save_user_interest(interest)

    def run_daily_batch_update(self) -> Dict[str, Any]:
        """Daily batch: process liked/disliked entries, extract entities with LLM.

        Returns:
            Dict with processing stats
        """
        from src.storage.singleton import get_storage
        import logging

        logger = logging.getLogger("uvicorn.error")
        stats = {
            "processed": 0,
            "entities_found": 0,
            "liked_entries": 0,
            "disliked_entries": 0,
        }

        try:
            storage = get_storage()

            # Get all liked entries
            cursor = storage.conn.cursor()
            cursor.execute("""
                SELECT id FROM feed_entries
                WHERE liked = 1 OR is_favorite = 1
                ORDER BY updated_at_entry DESC
                LIMIT 50
            """)
            liked_entry_ids = [row[0] for row in cursor.fetchall()]
            stats["liked_entries"] = len(liked_entry_ids)

            # Get all disliked entries
            cursor.execute("""
                SELECT id FROM feed_entries
                WHERE liked = -1
                ORDER BY updated_at_entry DESC
                LIMIT 50
            """)
            disliked_entry_ids = [row[0] for row in cursor.fetchall()]
            stats["disliked_entries"] = len(disliked_entry_ids)

            # Process liked entries
            for entry_id in liked_entry_ids:
                self._process_entry_for_ontology(entry_id, sentiment="positive")
                stats["processed"] += 1

            # Process disliked entries
            for entry_id in disliked_entry_ids:
                self._process_entry_for_ontology(entry_id, sentiment="negative")
                stats["processed"] += 1

            logger.info(f"Daily ontology batch complete: {stats}")

        except Exception as e:
            logger.error(f"Daily ontology batch failed: {e}")
            stats["error"] = str(e)

        return stats

    def _process_entry_for_ontology(
        self,
        entry_id: str,
        sentiment: str
    ) -> None:
        """Process a single entry for ontology update via LLM.

        Args:
            entry_id: Entry ID to process
            sentiment: 'positive' for liked, 'negative' for disliked
        """
        from src.storage.singleton import get_storage
        import json

        storage = get_storage()
        cursor = storage.conn.cursor()

        # Get entry content
        cursor.execute("SELECT title, preview, content FROM feed_entries WHERE id = ?", (entry_id,))
        row = cursor.fetchone()
        if not row:
            return

        title, preview, content = row
        content = content or preview or ""
        if len(content) > 5000:
            content = content[:5000]

        # Get existing profile to check if we need to re-extract
        profile = self.memory.get_content_profile(entry_id)

        # If profile exists and is fresh, skip LLM extraction
        if profile and profile.tags and len(profile.tags) >= 3:
            # Just update existing tags based on sentiment
            user_interests = self.memory.get_all_user_interests()
            if sentiment == "positive":
                updated = self.interest_updater.update_interests_on_like(
                    profile.tags, user_interests
                )
            else:
                updated = self.interest_updater.update_interests_on_dislike(
                    profile.tags, user_interests
                )
            for interest in updated:
                self.memory.save_user_interest(interest)
            return

        # Need LLM extraction - use the configured LLM handler
        from src.plugins.llm import create_llm_handler, get_default_provider

        try:
            llm = create_llm_handler(get_default_provider())
        except Exception:
            # Fallback: just update based on existing profile
            if profile and profile.tags:
                user_interests = self.memory.get_all_user_interests()
                if sentiment == "positive":
                    updated = self.interest_updater.update_interests_on_like(
                        profile.tags, user_interests
                    )
                else:
                    updated = self.interest_updater.update_interests_on_dislike(
                        profile.tags, user_interests
                    )
                for interest in updated:
                    self.memory.save_user_interest(interest)
            return

        prompt = f"""Extract entities and topics from this article.

For liked/favorited articles: focus on what the user found valuable - these are positive signals.
For disliked articles: focus on what topics to deprioritize - these are negative signals.

Article title: {title}
Article content: {content[:2000]}

Return ONLY valid JSON array, no markdown:
[
    {{
        "name": "entity name in lowercase",
        "category": "technology|medical|finance|science|business|education|entertainment|sports|politics|society|other",
        "sentiment_alignment": "positive|negative"
    }}
]

If no clear entities found, return []."""

        try:
            response = llm.chat([
                {"role": "system", "content": "You are a precise entity extraction assistant. Output only valid JSON array."},
                {"role": "user", "content": prompt}
            ])

            if not response:
                return

            response = response.strip()
            if response.startswith("```"):
                response = json.loads(re.sub(r'^```(?:json)?\n?', '', response))
                response = re.sub(r'\n?```$', '', response)

            entities = json.loads(response)
            if not isinstance(entities, list):
                return

            # Convert to InterestTags
            from src.services.ontology.types import InterestTag, TagSource, InterestCategory

            category_map = {
                "technology": InterestCategory.TECHNOLOGY,
                "medical": InterestCategory.MEDICAL,
                "finance": InterestCategory.FINANCE,
                "science": InterestCategory.SCIENCE,
                "business": InterestCategory.BUSINESS,
                "education": InterestCategory.EDUCATION,
                "entertainment": InterestCategory.ENTERTAINMENT,
                "sports": InterestCategory.SPORTS,
                "politics": InterestCategory.POLITICS,
                "society": InterestCategory.SOCIETY,
                "other": InterestCategory.OTHER,
            }

            tags = []
            for e in entities:
                name = e.get("name", "").lower().strip()
                if not name or len(name) < 2:
                    continue
                cat_str = e.get("category", "other").lower()
                tag = InterestTag(
                    name=name,
                    category=category_map.get(cat_str, InterestCategory.OTHER),
                    confidence=0.7,
                    source=TagSource.BEHAVIOR,
                )
                tags.append(tag)

            # Update user interests based on sentiment
            user_interests = self.memory.get_all_user_interests()

            if sentiment == "positive":
                updated = self.interest_updater.update_interests_on_like(tags, user_interests)
            else:
                updated = self.interest_updater.update_interests_on_dislike(tags, user_interests)

            for interest in updated:
                self.memory.save_user_interest(interest)

        except Exception as e:
            import logging
            logging.getLogger("uvicorn.error").warning(f"LLM entity extraction failed: {e}")

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

    def get_content_profile(self, entry_id: str) -> Optional[ContentProfile]:
        """Get content profile by entry ID.

        Args:
            entry_id: Entry ID to look up

        Returns:
            ContentProfile or None if not found
        """
        return self.memory.get_content_profile(entry_id)

    def get_recent_profiles(
        self,
        limit: int = 50,
        recent_hours: int = None
    ) -> List[ContentProfile]:
        """Get recent content profiles.

        Args:
            limit: Maximum number of profiles
            recent_hours: If set, only return profiles from last N hours

        Returns:
            List of ContentProfiles
        """
        profiles = self.memory.get_recent_profiles(limit=limit * 2 if recent_hours else limit)
        if recent_hours:
            from datetime import datetime, timedelta
            cutoff = datetime.now() - timedelta(hours=recent_hours)
            cutoff_str = cutoff.isoformat()
            profiles = [p for p in profiles if p.created_at >= cutoff_str]
        return profiles[:limit]

    # ============ User Profile Initialization ============

    def init_user_interests_from_file(
        self,
        file_path: str = None,
        use_llm: bool = True
    ) -> List[UserInterest]:
        """Initialize user interests from a user.md file.

        This method reads the user's profile description from a markdown file
        and extracts interests using LLM with the McKinsey MECE framework.

        Args:
            file_path: Path to user.md file. If None, uses {DATA_DIR}/user.md
            use_llm: Whether to use LLM for extraction (required)

        Returns:
            List of created UserInterest objects
        """
        import re
        import json
        from pathlib import Path
        from src.constants import DATA_DIR

        if file_path is None:
            # Default to {DATA_DIR}/user.md (user data directory)
            user_md_path = DATA_DIR / "user.md"
        else:
            user_md_path = Path(file_path)

        if not user_md_path.exists():
            return []

        try:
            content = user_md_path.read_text(encoding="utf-8")
        except Exception:
            return []

        # Check if already initialized (file hasn't changed)
        existing_interests = self.memory.get_all_user_interests()
        explicit_interests = [i for i in existing_interests if i.tag.source == TagSource.EXPLICIT]
        if explicit_interests:
            # Already has explicit interests, skip initialization
            return explicit_interests

        # Extract interests using LLM or rules
        if use_llm:
            extracted = self._extract_interests_with_llm(content)
        else:
            extracted = self._extract_interests_rule_based(content)

        # Create and save UserInterest objects
        created = []
        for item in extracted:
            tag = InterestTag(
                name=item["name"].lower().strip(),
                category=self._map_to_interest_category(item.get("category", "other")),
                confidence=item.get("confidence", 0.7),
                source=TagSource.EXPLICIT,
                wikidata_qid=item.get("wikidata_qid"),
                wikidata_label=item.get("wikidata_label"),
                wikidata_description=item.get("wikidata_description"),
                synonyms=item.get("synonyms", [])
            )
            interest = self.add_interest(tag, priority=item.get("priority", 3))
            created.append(interest)

        return created

    def seed_ontology_nodes(self) -> None:
        """Seed ontology graph with user interests.

        This adds user interests as nodes in the domain graph and resolves
        them via Wikidata if not already present.
        """
        user_interests = self.memory.get_all_user_interests()

        for interest in user_interests:
            tag_name = interest.tag.name
            qid = interest.tag.wikidata_qid

            # If already has QID, check if in graph
            if qid:
                node = self.domain_graph.get_node_by_qid(qid)
                if node:
                    continue  # Already in graph

            # Resolve and add to graph
            try:
                resolved_qid = self.domain_graph.resolve_and_add(
                    entity_name=tag_name,
                    context=[],
                    language="en"
                )

                # Update interest tag with resolved QID if it changed
                if resolved_qid and resolved_qid != qid:
                    interest.tag.wikidata_qid = resolved_qid
                    self.memory.save_user_interest(interest)

            except Exception as e:
                import logging
                logging.getLogger("uvicorn.error").warning(
                    f"Failed to seed interest '{tag_name}': {e}"
                )

    def _extract_interests_with_llm(self, text: str) -> List[Dict[str, Any]]:
        """Extract interests from text using LLM with McKinsey MECE framework.

        Args:
            text: User profile text from user.md

        Returns:
            List of extracted interests with name, category, priority
        """
        prompt = f"""You are an expert analyst using the McKinsey MECE framework to extract user interests.

## Your Task
Analyze the user's profile text and extract their research interests and topics they want to track.

## MECE Categories (use one of these):
- technology: AI/ML, software, hardware, infrastructure, cloud, data science
- medical: healthcare, clinical, pharmaceutical, biotech, gene editing, medical devices
- finance: investment, banking, stock market, venture capital, cryptocurrency
- science: research, academic, physics, chemistry, biology, space, publication
- business: startup, entrepreneurship, funding, acquisition, market strategy
- education: learning, training, academic
- entertainment: arts, movies, music, gaming
- sports: athletics, sports news
- politics: government, policy, regulation
- society: social issues, culture, community
- other: topics that don't fit above

## Output Format (JSON array only):
[
    {{
        "name": "specific interest tag in English lowercase",
        "category": "one of the MECE categories above",
        "priority": 5 for core interests, 4 for important, 3 for general, 2 for occasional,
        "confidence": 0.0 to 1.0 based on how explicitly mentioned
    }}
]

## Priority Guidelines:
- 5 = Core interest, directly related to profession/decision making, checked daily
- 4 = Important, checked weekly, influences strategy
- 3 = General interest, checked regularly, good to know
- 2 = Occasional interest, low priority

## User Profile Text:
{text}

Return ONLY valid JSON array, no markdown formatting, no other text. If no clear interests found, return []."""
        try:
            from src.storage.singleton import get_storage
            from src.plugins.llm import create_llm_handler, get_default_provider

            storage = get_storage()
            settings = storage.get_settings()
            llm_handler = settings.llm_handler

            # Fallback to default provider if null_llm is configured
            if not llm_handler or not hasattr(llm_handler, 'chat') or type(llm_handler).__name__ == 'NullLLMHandler':
                import logging
                logging.getLogger("uvicorn.error").info("Using default LLM provider for interest extraction")
                llm_handler = create_llm_handler(get_default_provider())

            response = llm_handler.chat([
                {"role": "system", "content": "You are a precise data extraction assistant. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ])

            # Handle None response (e.g., from NullLLMHandler)
            if response is None:
                import logging
                logging.getLogger("uvicorn.error").warning("LLM returned None for interest extraction")
                return []

            # Parse JSON response
            response = response.strip()
            if response.startswith("```"):
                response = re.sub(r'^```(?:json)?\n?', '', response)
                response = re.sub(r'\n?```$', '', response)

            extracted = json.loads(response)
            if not isinstance(extracted, list):
                return []

            # Validate and clean each item
            valid_extracted = []
            for item in extracted:
                if not isinstance(item, dict):
                    continue
                name = item.get("name", "")
                if not name or len(name) < 2:
                    continue

                # Resolve via Wikidata
                resolved = self.wikidata_resolver.resolve(name, language="en")

                if resolved:
                    valid_extracted.append({
                        "name": name.lower().strip(),
                        "category": item.get("category", "other"),
                        "priority": max(0, min(5, item.get("priority", 3))),
                        "confidence": max(0.0, min(1.0, item.get("confidence", 0.5))),
                        "wikidata_qid": resolved["qid"],
                        "wikidata_label": resolved["label"],
                        "wikidata_description": resolved.get("description", ""),
                        "synonyms": resolved.get("aliases", [])
                    })
                else:
                    # No Wikidata match, create custom entity
                    import uuid
                    custom_qid = f"entrofeed:{uuid.uuid4().hex[:8]}"
                    valid_extracted.append({
                        "name": name.lower().strip(),
                        "category": item.get("category", "other"),
                        "priority": max(0, min(5, item.get("priority", 3))),
                        "confidence": max(0.0, min(1.0, item.get("confidence", 0.5))),
                        "wikidata_qid": custom_qid,
                        "wikidata_label": name,
                        "wikidata_description": f"Custom entity: {name}",
                        "synonyms": []
                    })

            return valid_extracted

        except Exception as e:
            import logging
            logging.getLogger("uvicorn.error").warning(f"LLM interest extraction failed: {e}")
            return []

    def _map_to_interest_category(self, category_str: str) -> InterestCategory:
        """Map string category to InterestCategory enum."""
        category_lower = category_str.lower().strip()
        mapping = {
            "technology": InterestCategory.TECHNOLOGY,
            "tech": InterestCategory.TECHNOLOGY,
            "medical": InterestCategory.MEDICAL,
            "health": InterestCategory.MEDICAL,
            "healthcare": InterestCategory.MEDICAL,
            "finance": InterestCategory.FINANCE,
            "financial": InterestCategory.FINANCE,
            "science": InterestCategory.SCIENCE,
            "scientific": InterestCategory.SCIENCE,
            "business": InterestCategory.BUSINESS,
            "education": InterestCategory.EDUCATION,
            "entertainment": InterestCategory.ENTERTAINMENT,
            "sports": InterestCategory.SPORTS,
            "politics": InterestCategory.POLITICS,
            "society": InterestCategory.SOCIETY,
            "other": InterestCategory.OTHER,
        }
        return mapping.get(category_lower, InterestCategory.OTHER)

    # ============ User Profile File Operations ============

    def get_user_profile_path(self) -> Path:
        """Get the path to user.md file.

        Returns:
            Path to user.md in DATA_DIR
        """
        from src.constants import DATA_DIR
        return DATA_DIR / "user.md"

    def read_user_profile(self) -> str:
        """Read user profile content from user.md.

        Returns:
            Content of user.md or empty string if not exists
        """
        user_md_path = self.get_user_profile_path()
        if user_md_path.exists():
            try:
                return user_md_path.read_text(encoding="utf-8")
            except Exception:
                return ""
        return ""

    def write_user_profile(self, content: str) -> bool:
        """Write user profile content to user.md.

        Args:
            content: Markdown content to write

        Returns:
            True if successful, False otherwise
        """
        from src.constants import DATA_DIR
        user_md_path = self.get_user_profile_path()
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            user_md_path.write_text(content, encoding="utf-8")
            return True
        except Exception:
            return False

    def get_user_profile_status(self) -> Dict[str, Any]:
        """Get user profile status (exists, empty, content length).

        Returns:
            Dict with status info
        """
        content = self.read_user_profile()
        user_md_path = self.get_user_profile_path()

        return {
            "exists": user_md_path.exists(),
            "is_empty": not content.strip(),
            "content_length": len(content),
            "path": str(user_md_path),
        }

    def reinitialize_interests_from_profile(self) -> List[UserInterest]:
        """Re-read user.md and re-initialize user interests.

        This clears existing EXPLICIT interests and re-extracts from user.md.

        Returns:
            List of newly created UserInterest objects
        """
        # Clear existing explicit interests
        existing = self.memory.get_all_user_interests()
        for interest in existing:
            if interest.tag.source == TagSource.EXPLICIT:
                self.memory.delete_user_interest(interest.id)

        # Re-read profile and extract
        content = self.read_user_profile()
        if not content.strip():
            return []

        extracted = self._extract_interests_with_llm(content)
        if not extracted:
            return []

        created = []
        for item in extracted:
            tag = InterestTag(
                name=item["name"].lower().strip(),
                category=self._map_to_interest_category(item.get("category", "other")),
                confidence=item.get("confidence", 0.7),
                source=TagSource.EXPLICIT,
                wikidata_qid=item.get("wikidata_qid"),
                wikidata_label=item.get("wikidata_label"),
                wikidata_description=item.get("wikidata_description"),
                synonyms=item.get("synonyms", [])
            )
            interest = self.add_interest(tag, priority=item.get("priority", 3))
            created.append(interest)

        return created

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

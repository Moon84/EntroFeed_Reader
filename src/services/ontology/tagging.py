# -*- coding: utf-8 -*-
"""
Ontology Tagging - Tag generation and matching for content.

This module provides:
- Tag extraction from content using LLM
- Tag matching against user interests (UnifiedNode)
- Automatic tag inference
- Cross-domain detection
"""

import json
import re
from typing import Dict, List, Any, Callable, Optional

from .types import (
    UnifiedNode,
    InterestCategory,
    TagSource,
    ContentProfile,
)
from .wikidata import WikidataResolver
from .domain_hierarchy import (
    detect_domains_in_text,
    get_domain_by_name,
    get_cross_domain_parents,
    calculate_cross_domain_score,
)
from src.models.feed import Feed, FeedEntry


class TagGenerator:
    """Generate tags from content using LLM."""

    DEFAULT_TAG_CATEGORIES = [
        "technology",
        "medical",
        "finance",
        "science",
        "business",
        "education",
        "entertainment",
        "sports",
        "politics",
        "society",
        "other",
    ]

    TAG_EXTRACTION_PROMPT = """
Extract tags from the following content. Return a JSON list with objects containing:
- "name": tag name (lowercase, single word or hyphenated)
- "category": one of [{categories}]
- "confidence": score from 0.0 to 1.0 indicating how confident you are in this tag

Also extract:
- key_entities: list of important named entities (people, organizations, products)
- key_concepts: list of main topics or themes

Content Title: {title}
Content Preview: {preview}
Content Body: {body[:2000]}

Return ONLY valid JSON, no markdown formatting.
"""

    def __init__(
        self,
        llm_summarizer: Optional[Callable[[Feed, FeedEntry, str], str]] = None,
        wikidata_resolver: Optional["WikidataResolver"] = None,
    ):
        """Initialize tag generator.

        Args:
            llm_summarizer: Optional LLM function for content analysis.
                           If not provided, uses rule-based extraction.
            wikidata_resolver: Optional WikidataResolver for entity standardization.
        """
        self.llm_summarizer = llm_summarizer
        self.wikidata_resolver = wikidata_resolver

    def extract_tags(
        self, entry: FeedEntry, feed: Feed, content: Optional[str] = None
    ) -> ContentProfile:
        """Extract tags and create content profile.

        Args:
            entry: Feed entry to analyze
            feed: Parent feed
            content: Full content (if available)

        Returns:
            ContentProfile with extracted tags and entities
        """
        preview = entry.preview or entry.content[:500] if entry.content else ""
        body = content or entry.content or preview

        if self.llm_summarizer:
            return self._extract_with_llm(entry, feed, body, preview)
        else:
            return self._extract_rule_based(entry, feed, body, preview)

    def _extract_with_llm(
        self, entry: FeedEntry, feed: Feed, body: str, preview: str
    ) -> ContentProfile:
        """Extract tags using LLM."""
        prompt = self.TAG_EXTRACTION_PROMPT.format(
            categories=", ".join(self.DEFAULT_TAG_CATEGORIES),
            title=entry.title,
            preview=preview[:500],
            body=body,
        )

        try:
            # Use existing summarizer if available
            assert self.llm_summarizer is not None
            result = self.llm_summarizer(feed, entry, prompt)
            parsed = json.loads(result)

            tags = []
            for tag_data in parsed.get("tags", []):
                try:
                    category = InterestCategory(tag_data.get("category", "other"))
                except ValueError:
                    category = InterestCategory.OTHER

                tag_name = tag_data.get("name", "").lower()
                confidence = tag_data.get("confidence", 0.5)

                # Resolve via Wikidata if available
                tag = self._resolve_tag_with_wikidata(tag_name, category, confidence)
                tags.append(tag)

            return ContentProfile(
                entry_id=entry.id,
                tags=tags,
                summary=entry.content[:200] if entry.content else "",
                key_entities=parsed.get("key_entities", []),
                key_concepts=parsed.get("key_concepts", []),
                language=self._detect_language(body),
            )
        except (json.JSONDecodeError, Exception):
            # Fallback to rule-based
            return self._extract_rule_based(entry, feed, body, preview)

    def _extract_rule_based(
        self, entry: FeedEntry, feed: Feed, body: str, preview: str
    ) -> ContentProfile:
        """Extract tags using rule-based approach."""
        text = f"{entry.title} {preview} {body}".lower()

        # Common tech keywords
        tech_keywords = [
            "ai",
            "machine learning",
            "python",
            "software",
            "tech",
            "startup",
            "api",
            "cloud",
            "data",
            "algorithm",
            "python",
            "javascript",
        ]
        medical_keywords = [
            "medical",
            "health",
            "doctor",
            "patient",
            "hospital",
            "treatment",
            "disease",
            "drug",
            "clinical",
            "patient",
        ]
        finance_keywords = [
            "stock",
            "market",
            "investment",
            "bank",
            "finance",
            "economy",
            "revenue",
            "billion",
            " IPO",
            "cryptocurrency",
            "fintech",
        ]
        science_keywords = [
            "research",
            "study",
            "scientist",
            "experiment",
            "discovery",
            "physics",
            "chemistry",
            "biology",
            "space",
            "nasa",
        ]
        business_keywords = [
            "company",
            "ceo",
            "startup",
            "funding",
            "acquisition",
            "partnership",
            "launch",
            "product",
            "strategy",
        ]

        detected_tags = []

        for kw in tech_keywords:
            if kw in text:
                tag = self._resolve_tag_with_wikidata(
                    kw, InterestCategory.TECHNOLOGY, 0.6
                )
                detected_tags.append(tag)

        for kw in medical_keywords:
            if kw in text:
                tag = self._resolve_tag_with_wikidata(kw, InterestCategory.MEDICAL, 0.6)
                detected_tags.append(tag)

        for kw in finance_keywords:
            if kw in text:
                tag = self._resolve_tag_with_wikidata(kw, InterestCategory.FINANCE, 0.6)
                detected_tags.append(tag)

        for kw in science_keywords:
            if kw in text:
                tag = self._resolve_tag_with_wikidata(kw, InterestCategory.SCIENCE, 0.6)
                detected_tags.append(tag)

        for kw in business_keywords:
            if kw in text:
                tag = self._resolve_tag_with_wikidata(
                    kw, InterestCategory.BUSINESS, 0.6
                )
                detected_tags.append(tag)

        # Extract entities (simple capitalized phrase detection)
        entities = re.findall(
            r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", f"{entry.title} {preview}"
        )
        entities = [e for e in entities if len(e) > 2][:10]

        return ContentProfile(
            entry_id=entry.id,
            tags=detected_tags,
            summary=preview[:200] if preview else "",
            key_entities=entities,
            key_concepts=list(set([t.name for t in detected_tags])),
            language=self._detect_language(body),
        )

    def _detect_language(self, text: str) -> str:
        """Simple language detection."""
        if not text:
            return "en"

        # Check for Chinese characters
        if re.search(r"[\u4e00-\u9fff]", text):
            return "zh"
        # Check for Japanese
        if re.search(r"[\u3040-\u309f\u30a0-\u30ff]", text):
            return "ja"
        return "en"

    def _resolve_tag_with_wikidata(
        self, tag_name: str, category: InterestCategory, confidence: float
    ) -> UnifiedNode:
        """Resolve tag name to Wikidata QID if possible.

        Args:
            tag_name: Tag name to resolve
            category: Tag category
            confidence: Confidence score

        Returns:
            UnifiedNode with Wikidata fields populated if found
        """
        if not self.wikidata_resolver or not tag_name:
            return UnifiedNode(
                name=tag_name,
                category=category,
                confidence=confidence,
                source=TagSource.INFERENCE,
                is_interest=False,
            )

        # Try to resolve via Wikidata
        result = self.wikidata_resolver.resolve(tag_name, language="en")

        if result:
            return UnifiedNode(
                name=tag_name,
                category=category,
                confidence=confidence,
                source=TagSource.INFERENCE,
                wikidata_qid=result["qid"],
                wikidata_label=result["label"],
                wikidata_description=result.get("description", ""),
                synonyms=result.get("aliases", []),
                is_interest=False,
            )
        else:
            # No Wikidata match, create custom entity ID
            import uuid

            custom_qid = f"entrofeed:{uuid.uuid4().hex[:8]}"
            return UnifiedNode(
                name=tag_name,
                category=category,
                confidence=confidence,
                source=TagSource.INFERENCE,
                wikidata_qid=custom_qid,
                wikidata_label=tag_name,
                wikidata_description=f"Custom entity: {tag_name}",
                is_interest=False,
            )


class TagMatcher:
    """Match content tags against user interests (UnifiedNode) with cross-domain detection."""

    def __init__(self):
        pass

    def calculate_priority(
        self,
        content_tags: List[UnifiedNode],
        user_interests: List[UnifiedNode],
        content_text: str = "",
        decay_factor: float = 0.9,
    ) -> int:
        """Calculate priority based on tag matching with cross-domain detection.

        Args:
            content_tags: Tags extracted from content (as UnifiedNodes)
            user_interests: User's tracked interests (UnifiedNodes)
            content_text: Full content text for domain detection
            decay_factor: Decay factor for non-exact matches

        Returns:
            Priority score 0-5
        """
        if not content_tags and not content_text:
            return 0

        content_tag_names = {t.name.lower() for t in content_tags}
        content_categories = {t.category for t in content_tags}

        max_match_score = 0.0

        # Detect domains from content text (for cross-domain matching)
        detected_domains = []
        if content_text:
            detected_domains = detect_domains_in_text(content_text)

        for interest in user_interests:
            score = 0.0

            # Exact tag name match
            if interest.name.lower() in content_tag_names:
                score = interest.interest_level * interest.interest_priority / 5.0
            # Category match
            elif interest.category in content_categories:
                score = interest.interest_level * interest.interest_priority / 10.0
            # Cross-domain match
            elif detected_domains:
                score = self._cross_domain_match(
                    interest, detected_domains, decay_factor
                )
            # Fuzzy match (substring)
            else:
                for content_tag in content_tags:
                    if (
                        content_tag.name in interest.name
                        or interest.name in content_tag.name
                    ):
                        score = (
                            interest.interest_level
                            * decay_factor
                            * interest.interest_priority
                            / 10.0
                        )
                        break

            max_match_score = max(max_match_score, score)

        # Scale to 0-5
        return min(5, int(max_match_score * 5))

    def _cross_domain_match(
        self, interest: UnifiedNode, detected_domains: List[Dict], decay_factor: float
    ) -> float:
        """Calculate cross-domain match score.

        Args:
            interest: User interest (UnifiedNode) to match
            detected_domains: Domains detected in content
            decay_factor: Decay factor

        Returns:
            Match score from 0.0 to 1.0
        """
        interest_name_lower = interest.name.lower()
        cat = interest.category
        interest_category_lower = cat.value if hasattr(cat, "value") else str(cat)

        # Check if any detected domain matches the interest's category
        for domain_info in detected_domains:
            domain = domain_info["domain"]

            # Direct domain name match
            if interest_name_lower in domain.lower():
                return interest.interest_level * interest.interest_priority / 5.0

            # Check cross-domain parents
            cross_parents = get_cross_domain_parents(domain)

            # If interest's category is a cross-domain parent
            if interest_category_lower in cross_parents:
                return (
                    interest.interest_level
                    * interest.interest_priority
                    / 6.0
                    * domain_info["score"]
                )

            # Check cross-domain relationship via Wu-Palmer similarity
            for cross_parent in cross_parents:
                cross_score = calculate_cross_domain_score(
                    interest_name_lower, cross_parent.lower()
                )
                if cross_score > 0.3:
                    return (
                        interest.interest_level
                        * cross_score
                        * interest.interest_priority
                        / 5.0
                        * domain_info["score"]
                    )

        return 0.0

    def detect_cross_domain_tags(
        self, content_text: str, base_categories: List[str]
    ) -> List[Dict]:
        """Detect cross-domain concepts in content.

        Args:
            content_text: Full content text
            base_categories: Base categories detected in content

        Returns:
            List of cross-domain tags with detection info
        """
        if not content_text:
            return []

        detected = detect_domains_in_text(content_text)
        cross_domain_tags = []

        for domain_info in detected:
            domain = domain_info["domain"]
            info = get_domain_by_name(domain)

            if not info:
                continue

            # Only include cross-domain domains (level >= 2)
            if info.get("level", 0) >= 2:
                cross_domain_tags.append(
                    {
                        "domain": domain,
                        "level": info.get("level", 0),
                        "description": info.get("description", ""),
                        "matches": domain_info.get("matches", []),
                        "score": domain_info.get("score", 0.0),
                        "cross_domains": info.get("cross_domains", []),
                    }
                )

        return cross_domain_tags

    def find_matching_interests(
        self,
        content_tags: List[UnifiedNode],
        user_interests: List[UnifiedNode],
        content_text: str = "",
    ) -> List[Dict[str, Any]]:
        """Find matching user interests for content tags with cross-domain support.

        Args:
            content_tags: Tags extracted from content
            user_interests: User's tracked interests (UnifiedNodes)
            content_text: Full content text for domain detection

        Returns:
            List of matches with interest and match score
        """
        matches = []

        # Detect cross-domain in content
        cross_domain_tags = []
        if content_text:
            cross_domain_tags = self.detect_cross_domain_tags(content_text, [])

        for content_tag in content_tags:
            for interest in user_interests:
                match_score = 0.0
                match_type = "exact"

                # Exact match
                if content_tag.name.lower() == interest.name.lower():
                    match_score = 1.0
                # Category match
                elif content_tag.category == interest.category:
                    match_score = 0.5
                # Cross-domain match
                elif cross_domain_tags:
                    cross_score = self._cross_domain_match(
                        interest, cross_domain_tags, 0.9
                    )
                    if cross_score > 0:
                        match_score = cross_score
                        match_type = "cross_domain"
                # Related match
                elif self._are_related(content_tag.name, interest.name):
                    match_score = 0.3
                    match_type = "related"

                if match_score > 0:
                    matches.append(
                        {
                            "content_tag": content_tag,
                            "user_interest": interest,
                            "match_score": match_score * interest.interest_level,
                            "match_type": match_type,
                        }
                    )

        return sorted(matches, key=lambda x: x["match_score"], reverse=True)

    def _are_related(self, tag1: str, tag2: str) -> bool:
        """Check if two tags are related (simple substring check)."""
        t1, t2 = tag1.lower(), tag2.lower()
        return t1 in t2 or t2 in t1


__all__ = [
    "TagGenerator",
    "TagMatcher",
]

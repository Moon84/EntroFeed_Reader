# -*- coding: utf-8 -*-
"""
McKinsey-Style Analysis Plugin - Integration of McKinsey analysis framework with ontology.

This plugin provides:
- McKinsey-style content analysis for technology tracks
- MECE-based tag categorization
- Evidence-based priority scoring
- Competitive landscape analysis
"""
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum

from .types import (
    InterestTag,
    InterestCategory,
    TagSource,
    ContentProfile,
    UserInterest,
)
from src.models.feed import Feed, FeedEntry


class AnalysisPhase(str, Enum):
    """McKinsey analysis phases"""
    INTAKE = "intake"           #需求澄清与框架设定
    PLAN = "plan"               # 计划与并行执行
    COLLECT = "collect"         # 信息收集与综合
    DELIVERY = "delivery"       # 交付与架构集成


class FactorCategory(str, Enum):
    """Impact factor categories (aligned with McKinsey framework)"""
    TECHNOLOGY = "technology"      # 技术因子
    MARKET = "market"              # 市场因子
    REGULATORY = "regulatory"       # 监管因子
    COMPETITIVE = "competitive"     # 竞争因子
    COMMERCIAL = "commercial"       # 商业化因子
    GENERAL = "general"             # 通用因子


class MECEClassifier:
    """
    MECE (Mutually Exclusive, Collectively Exhaustive) Classifier.

    Ensures tags are properly categorized without overlap and cover all aspects.
    """

    # MECE categories for tech/health content
    MECE_CATEGORIES = {
        "technology": [
            "algorithm", "model", "architecture", "infrastructure",
            "computing", "hardware", "software", "data", "pipeline"
        ],
        "market": [
            "market", "industry", "sector", "segment", "adoption",
            "penetration", "growth", "forecast", "trend"
        ],
        "regulatory": [
            "policy", "regulation", "approval", "compliance", "standard",
            "certification", "guideline", "law", "fda", "nmpa"
        ],
        "competitive": [
            "competitor", "landscape", "player", "leader", "challenger",
            "monopoly", "oligopoly", "differentiation", "advantage"
        ],
        "commercial": [
            "revenue", "pricing", "cost", "roi", "business model",
            "monetization", "partnership", "acquisition", "funding"
        ],
        "scientific": [
            "research", "study", "trial", "experiment", "discovery",
            "publication", "peer-review", "hypothesis", "result"
        ],
        "clinical": [
            "patient", "treatment", "diagnosis", "therapy", "drug",
            "device", "efficacy", "safety", "outcome", "hospital"
        ]
    }

    # Sub-categories for deeper classification
    SUB_CATEGORIES = {
        "algorithm": ["neural network", "deep learning", "ml model", "llm", "transformer"],
        "data": ["dataset", "training data", "real-world data", "benchmark", "annotation"],
        "computing": ["cloud", "edge", "gpu", "tpu", "serverless"],
        "regulation": ["privacy", "security", "gdpr", "hipaa", "data protection"],
    }

    def __init__(self):
        pass

    def classify(self, tag_name: str, context: str = "") -> Dict[str, Any]:
        """
        Classify a tag using MECE principles.

        Args:
            tag_name: Tag to classify
            tag_lower = tag_name.lower()
            context: Additional context for disambiguation

        Returns:
            Dict with category, sub_category, and confidence
        """
        tag_lower = tag_name.lower()
        combined_text = f"{tag_lower} {context.lower()}"

        result = {
            "category": InterestCategory.OTHER,
            "sub_category": None,
            "confidence": 0.5,
            "mece_valid": True,
            "alternatives": []
        }

        # Check each MECE category
        for cat_keyword, keywords in self.MECE_CATEGORIES.items():
            for keyword in keywords:
                if keyword in tag_lower or keyword in combined_text:
                    try:
                        result["category"] = InterestCategory(cat_keyword)
                    except ValueError:
                        result["category"] = InterestCategory.OTHER
                    result["confidence"] = 0.7
                    result["sub_category"] = keyword
                    return result

        # Check sub-categories
        for sub_key, sub_keywords in self.SUB_CATEGORIES.items():
            for keyword in sub_keywords:
                if keyword in tag_lower:
                    result["sub_category"] = sub_key
                    result["confidence"] = 0.6
                    break

        # Infer category from common patterns
        if any(w in tag_lower for w in ["ai", "ml", "model", "network"]):
            result["category"] = InterestCategory.TECHNOLOGY
            result["confidence"] = 0.6
        elif any(w in tag_lower for w in ["medical", "health", "clinical", "patient"]):
            result["category"] = InterestCategory.MEDICAL
            result["confidence"] = 0.6
        elif any(w in tag_lower for w in ["stock", "market", "investment", "fund"]):
            result["category"] = InterestCategory.FINANCE
            result["confidence"] = 0.6

        return result

    def ensure_mece(self, tags: List[InterestTag]) -> List[InterestTag]:
        """
        Ensure tags follow MECE principles.

        Args:
            tags: List of tags to validate

        Returns:
            Deduplicated, MECE-compliant tags
        """
        seen = set()
        mece_tags = []

        for tag in tags:
            key = (tag.name.lower(), tag.category.value)
            if key not in seen:
                seen.add(key)
                mece_tags.append(tag)

        return mece_tags


class EvidenceScorer:
    """
    Evidence-based scoring following McKinsey principles.

    Scores content based on:
    - Source credibility (regulatory > academic > media)
    - Evidence strength (peer-reviewed > case study > opinion)
    - Recency (current data preferred)
    """

    SOURCE_WEIGHTS = {
        "regulatory": 1.0,      # FDA, NMPA, EMA documents
        "academic": 0.9,        # Peer-reviewed papers, conferences
        "industry": 0.7,        # Company reports, whitepapers
        "media": 0.5,           # News, blogs
        "social": 0.3,          # Social media, forums
    }

    EVIDENCE_TYPES = {
        "clinical_trial": 1.0,
        "meta_analysis": 0.95,
        "randomized_trial": 0.9,
        "case_study": 0.7,
        "expert_opinion": 0.5,
        "anecdotal": 0.3,
    }

    def __init__(self):
        pass

    def score_source(self, feed_category: str, url: str = "") -> float:
        """
        Score based on source credibility.

        Args:
            feed_category: Category of the feed
            url: URL of the source

        Returns:
            Source credibility score (0.0-1.0)
        """
        url_lower = url.lower()
        category_lower = feed_category.lower()

        # Regulatory sources
        if any(d in url_lower for d in ["fda.gov", "nmpa.gov", "ema.europa.eu", "nih.gov"]):
            return self.SOURCE_WEIGHTS["regulatory"]

        # Academic sources
        if any(d in url_lower for d in ["arxiv.org", "nature.com", "science.org",
                                         "nejm.org", "lancet.com", "pubmed.gov"]):
            return self.SOURCE_WEIGHTS["academic"]

        # Industry reports
        if any(d in url_lower for d in ["mckinsey.com", "bcg.com", "bain.com",
                                        "gartner.com", "forrester.com"]):
            return self.SOURCE_WEIGHTS["industry"]

        # Tier 1 journals
        if "tier1" in category_lower and "journal" in category_lower:
            return self.SOURCE_WEIGHTS["academic"]

        return self.SOURCE_WEIGHTS["media"]

    def score_evidence_type(self, content: str, title: str = "") -> float:
        """
        Score based on evidence type in content.

        Args:
            content: Content body
            title: Content title

        Returns:
            Evidence strength score (0.0-1.0)
        """
        text = f"{title} {content}".lower()

        # Clinical trial indicators
        if any(w in text for w in ["clinical trial", "randomized controlled", "rct",
                                    "phase i", "phase ii", "phase iii"]):
            if "randomized" in text:
                return self.EVIDENCE_TYPES["randomized_trial"]
            return self.EVIDENCE_TYPES["clinical_trial"]

        # Meta-analysis
        if "meta-analysis" in text or "meta analysis" in text:
            return self.EVIDENCE_TYPES["meta_analysis"]

        # Case study
        if "case study" in text or "case report" in text:
            return self.EVIDENCE_TYPES["case_study"]

        # Research indicators
        if any(w in text for w in ["study shows", "research found", "experiment",
                                   "demonstrated", "published in"]):
            return 0.6

        return self.EVIDENCE_TYPES["expert_opinion"]

    def calculate_priority_score(
        self,
        source_score: float,
        evidence_score: float,
        tag_match_score: float,
        recency_days: int = 0
    ) -> int:
        """
        Calculate final priority score (0-5).

        Following McKinsey 80/20 principle - focus on high-impact factors.

        Args:
            source_score: Source credibility (0-1)
            evidence_score: Evidence strength (0-1)
            tag_match_score: Match with user interests (0-1)
            recency_days: Days since publication

        Returns:
            Priority score 0-5
        """
        # Weighted combination (source and evidence are primary)
        raw_score = (
            source_score * 0.35 +
            evidence_score * 0.35 +
            tag_match_score * 0.30
        )

        # Recency bonus (recent content gets slight boost)
        if recency_days <= 7:
            raw_score *= 1.1
        elif recency_days > 90:
            raw_score *= 0.9

        # Scale to 0-5
        final = min(5.0, raw_score * 5)
        return int(final)


class McKinseyTagger:
    """
    McKinsey-style content tagger.

    Integrates MECE classification with evidence-based scoring.
    """

    def __init__(self, llm_summarizer: Callable = None):
        """
        Initialize McKinsey tagger.

        Args:
            llm_summarizer: Optional LLM function for advanced analysis.
        """
        self.mece = MECEClassifier()
        self.scorer = EvidenceScorer()
        self.llm_summarizer = llm_summarizer

    def analyze(
        self,
        entry: FeedEntry,
        feed: Feed,
        content: str = None,
        user_interests: List[UserInterest] = None
    ) -> ContentProfile:
        """
        Analyze content McKinsey-style.

        Args:
            entry: Feed entry to analyze
            feed: Parent feed
            content: Full content (if available)
            user_interests: User's interests for priority scoring

        Returns:
            ContentProfile with McKinsey-style analysis
        """
        user_interests = user_interests or []

        # Extract base content
        preview = entry.preview or ""
        body = content or entry.content or preview
        text = f"{entry.title} {preview} {body}"

        # Extract tags using rule-based + context
        tags = self._extract_tags_mckinsey(entry, feed, body)

        # Ensure MECE compliance
        tags = self.mece.ensure_mece(tags)

        # Calculate source and evidence scores
        source_score = self.scorer.score_source(feed.category, feed.url)
        evidence_score = self.scorer.score_evidence_type(body, entry.title)

        # Calculate tag match score
        tag_match_score = self._calculate_tag_match(tags, user_interests)

        # Calculate recency
        recency_days = 0
        if entry.published_at:
            publish_time = datetime.fromtimestamp(entry.published_at)
            recency_days = (datetime.now() - publish_time).days

        # Final priority
        priority = self.scorer.calculate_priority_score(
            source_score, evidence_score, tag_match_score, recency_days
        )

        # Extract entities (companies, products, etc.)
        entities = self._extract_entities(entry, preview)

        # Build content profile
        profile = ContentProfile(
            entry_id=entry.id,
            tags=tags,
            priority=priority,
            summary=self._generate_summary(entry, feed, body),
            key_entities=entities,
            key_concepts=[t.name for t in tags if t.confidence > 0.6],
            metadata={
                "source_score": source_score,
                "evidence_score": evidence_score,
                "tag_match_score": tag_match_score,
                "recency_days": recency_days,
                "analysis_phase": AnalysisPhase.DELIVERY.value,
                "mece_valid": True,
            }
        )

        return profile

    def _extract_tags_mckinsey(
        self,
        entry: FeedEntry,
        feed: Feed,
        body: str
    ) -> List[InterestTag]:
        """Extract tags using McKinsey-style classification."""
        text = f"{entry.title} {body[:1000]}".lower()
        tags = []
        seen = set()

        # Technology keywords (aligned with feed categories)
        tech_terms = {
            "ai": "technology", "artificial intelligence": "technology",
            "machine learning": "technology", "deep learning": "technology",
            "neural network": "technology", "llm": "technology",
            "gpt": "technology", "transformer": "technology",
            "algorithm": "technology", "model": "technology",
        }

        # Medical keywords
        medical_terms = {
            "medical": "medical", "health": "medical", "healthcare": "medical",
            "patient": "clinical", "treatment": "clinical", "therapy": "clinical",
            "drug": "clinical", "pharmaceutical": "clinical", "biotech": "technology",
            "gene": "scientific", "genomic": "scientific", "cancer": "clinical",
            "diagnosis": "clinical", "clinical trial": "clinical",
        }

        # Business keywords
        business_terms = {
            "startup": "commercial", "funding": "commercial", "investment": "commercial",
            "acquisition": "commercial", "merger": "commercial", "ipo": "commercial",
            "revenue": "commercial", "billion": "commercial", "valuation": "commercial",
            "partnership": "commercial", "launch": "commercial", "product": "commercial",
        }

        # Science keywords
        science_terms = {
            "research": "scientific", "study": "scientific", "discovery": "scientific",
            "experiment": "scientific", "published": "scientific", "peer-reviewed": "scientific",
            "nature": "scientific", "cell": "scientific", "protein": "scientific",
        }

        # Regulatory keywords
        regulatory_terms = {
            "fda": "regulatory", "approval": "regulatory", "nmpa": "regulatory",
            "regulation": "regulatory", "policy": "regulatory", "compliance": "regulatory",
            "standard": "regulatory", "certification": "regulatory", "guideline": "regulatory",
        }

        all_terms = {**tech_terms, **medical_terms, **business_terms,
                     **science_terms, **regulatory_terms}

        for term, category in all_terms.items():
            if term in text and term not in seen:
                seen.add(term)
                try:
                    cat = InterestCategory(category)
                except ValueError:
                    cat = InterestCategory.OTHER

                tags.append(InterestTag(
                    name=term,
                    category=cat,
                    confidence=0.7,
                    source=TagSource.INFERENCE,
                    properties={"analysis_method": "mcKinsey_keyword"}
                ))

        # Use MECE classifier for additional context
        for tag in tags:
            mece_result = self.mece.classify(tag.name, text)
            if mece_result["sub_category"]:
                tag.properties["sub_category"] = mece_result["sub_category"]

        return tags

    def _calculate_tag_match(
        self,
        tags: List[InterestTag],
        user_interests: List[UserInterest]
    ) -> float:
        """Calculate how well tags match user interests."""
        if not user_interests:
            return 0.5  # Neutral if no interests

        interest_names = {i.tag.name.lower() for i in user_interests}
        interest_cats = {i.tag.category for i in user_interests}

        matches = 0
        for tag in tags:
            if tag.name.lower() in interest_names:
                matches += 1
            elif tag.category in interest_cats:
                matches += 0.5

        return min(1.0, matches / max(1, len(tags)))

    def _extract_entities(self, entry: FeedEntry, preview: str) -> List[str]:
        """Extract named entities (companies, products, etc.)."""
        import re
        text = f"{entry.title} {preview}"
        entities = []

        # Capitalized words pattern
        caps = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        entities = [e for e in caps if len(e) > 2 and e not in [
            "AI", "ML", "LLM", "FDA", "NIH", "Nature", "Cell"
        ]][:10]

        return entities

    def _generate_summary(
        self,
        entry: FeedEntry,
        feed: Feed,
        body: str
    ) -> str:
        """Generate summary using LLM or fallback to preview."""
        if self.llm_summarizer:
            try:
                return self.llm_summarizer(feed, entry, body[:2000])
            except Exception:
                pass

        # Fallback
        preview = entry.preview or ""
        return preview[:200] if preview else body[:200]


class ImpactAnalyzer:
    """
    Impact analysis for content (inspired by Publication_research ImpactFactor).

    Analyzes content impact based on:
    - Factor categories (technology, market, regulatory, etc.)
    - Source reliability
    - Evidence strength
    """

    def __init__(self):
        self.factor_weights = {
            FactorCategory.TECHNOLOGY: 0.25,
            FactorCategory.MARKET: 0.20,
            FactorCategory.REGULATORY: 0.20,
            FactorCategory.COMPETITIVE: 0.15,
            FactorCategory.COMMERCIAL: 0.10,
            FactorCategory.SCIENTIFIC: 0.10,
        }

    def analyze_impact(
        self,
        profile: ContentProfile,
        feed: Feed
    ) -> Dict[str, Any]:
        """
        Analyze content impact.

        Args:
            profile: Content profile with tags
            feed: Source feed

        Returns:
            Impact analysis result
        """
        category_scores = {}
        total_weighted = 0.0

        for tag in profile.tags:
            try:
                cat = FactorCategory(tag.category.value)
            except ValueError:
                cat = FactorCategory.GENERAL

            weight = self.factor_weights.get(cat, 0.05)
            category_scores[cat.value] = tag.confidence * weight
            total_weighted += tag.confidence * weight

        # Normalize
        max_possible = sum(self.factor_weights.values())
        normalized_score = total_weighted / max_possible if max_possible > 0 else 0

        # Determine dominant category
        dominant_cat = max(category_scores, key=category_scores.get) if category_scores else "general"

        return {
            "impact_score": min(1.0, normalized_score * 2),  # Scale up
            "category_breakdown": category_scores,
            "dominant_category": dominant_cat,
            "priority": profile.priority,
            "confidence": sum(t.confidence for t in profile.tags) / max(1, len(profile.tags)),
        }


def create_mckinsey_tagger(llm_summarizer: Callable = None) -> McKinseyTagger:
    """Factory function to create McKinsey tagger."""
    return McKinseyTagger(llm_summarizer=llm_summarizer)


__all__ = [
    "AnalysisPhase",
    "FactorCategory",
    "MECEClassifier",
    "EvidenceScorer",
    "McKinseyTagger",
    "ImpactAnalyzer",
    "create_mckinsey_tagger",
]

# -*- coding: utf-8 -*-
"""Ontology module for user interest evaluation and tagging."""

from src.ontology.types import (
    TagSource,
    InterestCategory,
    InterestTag,
    UserInterest,
    ContentProfile,
    OntologyNode,
    OntologyRelation,
)
from src.ontology.registry import OntologyRegistry, get_ontology_registry
from src.ontology.tagging import TagGenerator, TagMatcher
from src.ontology.evaluation import (
    PriorityEvaluator,
    InterestUpdater,
    InterestInferrer,
)
from src.ontology.priority_scorer import (
    PriorityScorer,
    ArticleTagger,
    get_priority_scorer,
    get_article_tagger,
    score_and_tag_articles,
    get_recency_score,
    get_authority_score,
)

__all__ = [
    # Types
    "TagSource",
    "InterestCategory",
    "InterestTag",
    "UserInterest",
    "ContentProfile",
    "OntologyNode",
    "OntologyRelation",
    # Registry
    "OntologyRegistry",
    "get_ontology_registry",
    # Tagging
    "TagGenerator",
    "TagMatcher",
    # Evaluation
    "PriorityEvaluator",
    "InterestUpdater",
    "InterestInferrer",
    # Priority Scoring
    "PriorityScorer",
    "ArticleTagger",
    "get_priority_scorer",
    "get_article_tagger",
    "score_and_tag_articles",
    "get_recency_score",
    "get_authority_score",
]

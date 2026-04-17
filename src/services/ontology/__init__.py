# -*- coding: utf-8 -*-
"""Ontology module for user interest evaluation and tagging."""

from .types import (
    TagSource,
    InterestCategory,
    InterestTag,
    UserInterest,
    ContentProfile,
    OntologyNode,
    OntologyRelation,
)
from .registry import OntologyRegistry, get_ontology_registry
from .tagging import TagGenerator, TagMatcher
from .evaluation import (
    PriorityEvaluator,
    InterestUpdater,
    InterestInferrer,
)
from .priority_scorer import (
    PriorityScorer,
    ArticleTagger,
    GraphPropagationScorer,
    get_priority_scorer,
    get_article_tagger,
    get_graph_propagation_scorer,
    score_and_tag_articles,
    get_recency_score,
    get_authority_score,
    reset_article_tagger,
)
from .wikidata import WikidataResolver
from .domain_graph import DomainGraph

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
    "GraphPropagationScorer",
    "get_priority_scorer",
    "get_article_tagger",
    "get_graph_propagation_scorer",
    "score_and_tag_articles",
    "get_recency_score",
    "get_authority_score",
    "reset_article_tagger",
    # Wikidata & Graph
    "WikidataResolver",
    "DomainGraph",
]

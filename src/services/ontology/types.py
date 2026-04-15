# -*- coding: utf-8 -*-
"""
Ontology Types - Core type definitions for user interest evaluation.

This module defines the core types for the ontology system:
- InterestTag: Tags for categorizing content
- UserInterest: User's interest profile
- ContentProfile: Profile for feed entries
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional

from pydantic import BaseModel, Field


class TagSource(str, Enum):
    """Tag extraction source"""
    EXPLICIT = "explicit"      # User explicitly added
    INFERENCE = "inference"    # Inferred from content
    BEHAVIOR = "behavior"      # Inferred from reading behavior


class InterestCategory(str, Enum):
    """Interest categories"""
    TECHNOLOGY = "technology"
    MEDICAL = "medical"
    FINANCE = "finance"
    SCIENCE = "science"
    BUSINESS = "business"
    EDUCATION = "education"
    ENTERTAINMENT = "entertainment"
    SPORTS = "sports"
    POLITICS = "politics"
    SOCIETY = "society"
    OTHER = "other"


class InterestTag(BaseModel):
    """Tag for categorizing content and user interests"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    category: InterestCategory = InterestCategory.OTHER
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    source: TagSource = TagSource.INFERENCE
    synonyms: List[str] = Field(default_factory=list)
    properties: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class UserInterest(BaseModel):
    """User's interest profile with priority and relevance"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tag: InterestTag
    priority: int = Field(default=0, ge=0, le=5)
    access_count: int = 0
    last_accessed: Optional[str] = None
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    def mark_accessed(self):
        """Mark interest as accessed and update score"""
        self.access_count += 1
        self.last_accessed = datetime.now().isoformat()
        self.relevance_score = min(1.0, self.relevance_score + 0.01)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class ContentProfile(BaseModel):
    """Profile for feed entry content analysis"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    entry_id: str
    tags: List[InterestTag] = Field(default_factory=list)
    priority: int = Field(default=0, ge=0, le=5)
    summary: str = ""
    key_entities: List[str] = Field(default_factory=list)
    key_concepts: List[str] = Field(default_factory=list)
    sentiment: Optional[str] = None
    language: str = "en"
    reading_time_seconds: Optional[int] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class OntologyNode(BaseModel):
    """Node in the ontology graph"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    node_type: str  # "concept", "entity", "topic"
    category: str = ""
    description: str = ""
    properties: Dict[str, Any] = Field(default_factory=dict)
    relations: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class OntologyRelation(BaseModel):
    """Relation between ontology nodes"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str
    target_id: str
    relation_type: str  # "related_to", "is_a", "part_of", "causes"
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    properties: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


__all__ = [
    "TagSource",
    "InterestCategory",
    "InterestTag",
    "UserInterest",
    "ContentProfile",
    "OntologyNode",
    "OntologyRelation",
]

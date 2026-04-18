# -*- coding: utf-8 -*-
"""
Ontology Types - Unified type definitions for EntroFeed.

This module defines the core types for the ontology system:
- UnifiedNode: Unified node combining InterestTag, UserInterest, and OntologyNode
- OntologyRelation: Relations between nodes with rich relation types
- ContentProfile: Profile for feed entries

Updates:
- Added RelationType for rich relation modeling
- Added hierarchy_path for complete domain hierarchy
- Added NodeLevel, NodeSource, InterestStatus enums
- Enhanced UnifiedNode with relation management methods
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional

from pydantic import BaseModel, Field, model_validator


# =============================================================================
# 关系类型 (丰富自 Publication_research)
# =============================================================================


class RelationType(str, Enum):
    """关系类型枚举"""

    # 层级关系
    IS_A = "is_a"  # A is a B (概念继承)
    PART_OF = "part_of"  # A is part of B
    SUBTYPE_OF = "subtype_of"  # A is subtype of B

    # 语义关系
    RELATED_TO = "related_to"  # A related to B (通用关联)
    SIMILAR_TO = "similar_to"  # A similar to B (相似)
    OPPOSITE_OF = "opposite_of"  # A opposite to B (对立)
    SAME_AS = "same_as"  # A same as B (等价)

    # 因果关系
    CAUSES = "causes"  # A causes B
    TRIGGERS = "triggers"  # A triggers B
    ENABLES = "enables"  # A enables B
    REQUIRES = "requires"  # A requires B
    PREVENTS = "prevents"  # A prevents B
    INHIBITS = "inhibits"  # A inhibits B
    ACTIVATES = "activates"  # A activates B

    # 医学领域 (扩展)
    TREATS = "treats"  # Drug treats Disease
    DIAGNOSES = "diagnoses"  # Test diagnoses Disease
    INTERACTS_WITH = "interacts_with"  # Drug interacts with Drug
    ASSOCIATED_WITH = "associated_with"  # Symptom associated with Disease
    CAUSES_SYMPTOM = "causes_symptom"  # Disease causes symptom
    INDICATES = "indicates"  # Marker indicates condition

    # 动作关系
    FOLLOWS = "follows"  # A follows B (时序)
    PRECEDES = "precedes"  # A precedes B (时序)
    CONTAINS = "contains"  # A contains B (组成)
    CONTAINED_IN = "contained_in"  # A contained in B

    # 组织关系
    BELONGS_TO = "belongs_to"  # Entity belongs to Category
    OWNED_BY = "owned_by"  # Entity owned by Organization
    PART_OF_ORGANIZATION = "part_of_organization"  # Part of organization

    # 应用关系
    APPLIES_TO = "applies_to"  # Rule applies to Entity
    GOVERNS = "governs"  # Policy governs Entity
    USES = "uses"  # A uses B
    USED_BY = "used_by"  # A used by B

    # 推荐关系
    RECOMMENDED_FOR = "recommended_for"  # Content recommended for interest
    MATCHES_INTEREST = "matches_interest"  # Content matches user interest

    # 自定义
    CUSTOM = "custom"  # 自定义关系


# =============================================================================
# 节点层级 (丰富层级路径)
# =============================================================================


class NodeLevel(int, Enum):
    """节点层级"""

    WIKIDATA = 2  # Wikidata 标准实体
    KNOWLEDGE = 3  # 领域知识 (LLM 提取)
    DERIVED = 4  # 派生节点 (规则推理)
    USER = 5  # 用户定义


class NodeSource(str, Enum):
    """节点来源"""

    EXPLICIT = "explicit"  # 用户明确添加
    WIKIDATA = "wikidata"  # Wikidata 导入
    EXTRACTED = "extracted"  # LLM 提取
    INFERRED = "inferred"  # 行为推断
    DERIVED = "derived"  # 规则派生


class InterestStatus(str, Enum):
    """兴趣状态"""

    ACTIVE = "active"  # 活跃兴趣
    DORMANT = "dormant"  # 休眠兴趣
    ARCHIVED = "archived"  # 已归档


# =============================================================================
# 统一节点类型 (更新)
# =============================================================================


class UnifiedNode(BaseModel):
    """
    统一节点 - 整合 InterestTag, UserInterest, OntologyNode

    特性:
    1. 丰富层级: 支持完整 hierarchy_path
    2. 丰富关系: 支持多种 RelationType
    3. 领域灵活: domain 为字符串，非枚举
    """

    # ---------- 核心标识 ----------
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    wikidata_qid: Optional[str] = None  # Wikidata ID

    # ---------- 分类 (简化) ----------
    node_type: str = "concept"  # "concept", "entity", "topic", "domain", "event"

    # ---------- 层级与来源 ----------
    level: int = NodeLevel.KNOWLEDGE.value
    source: NodeSource = NodeSource.EXTRACTED

    # ---------- 领域 (字符串，灵活) ----------
    domain: str = "other"  # "technology", "medical", "finance", "ai", "drug", ...
    subdomains: List[str] = Field(default_factory=list)

    # ---------- 兼容性别名 ----------
    @property
    def category(self):
        """兼容: category alias for domain (getter)."""
        from src.services.ontology.types import InterestCategory

        try:
            return InterestCategory(self.domain)
        except ValueError:
            return InterestCategory.OTHER

    @category.setter
    def category(self, value: "InterestCategory"):
        """兼容: category alias for domain (setter)."""
        self.domain = value.value if hasattr(value, "value") else str(value)

    @property
    def layer(self) -> int:
        """兼容: layer alias for level (NodeLayer)."""
        return self.level  # 子领域

    # ---------- 层级路径 (新增) ----------
    hierarchy_path: List[str] = Field(default_factory=list)
    parent_id: Optional[str] = None  # 直接父节点
    parent_ids: List[str] = Field(default_factory=list)  # 所有祖先

    # ---------- 关系建模 (新增) ----------
    outgoing_relations: List[Dict[str, Any]] = Field(default_factory=list)
    incoming_relations: List[Dict[str, Any]] = Field(default_factory=list)

    # ---------- 兴趣追踪 (整合) ----------
    is_interest: bool = False
    priority: int = Field(default=0, ge=0, le=5)  # 0-5
    relevance: float = Field(default=0.0, ge=0.0, le=1.0)  # 0.0-1.0
    status: InterestStatus = InterestStatus.ACTIVE
    access_count: int = 0
    last_accessed: Optional[str] = None

    # ---------- Wikidata 对齐 ----------
    wikidata_label: Optional[str] = None
    wikidata_description: Optional[str] = None
    wikidata_aliases: List[str] = Field(default_factory=list)

    # ---------- 扩展属性 ----------
    synonyms: List[str] = Field(default_factory=list)
    description: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    is_seed: bool = False
    properties: Dict[str, Any] = Field(default_factory=dict)

    # ---------- 质量指标 (新增) ----------
    extraction_count: int = 1
    verification_count: int = 0
    last_verified: Optional[str] = None

    # ---------- 系统字段 ----------
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    last_used: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _handle_legacy_fields(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Handle backward compatibility for legacy field names."""
        if not isinstance(values, dict):
            return values
        if "interest_priority" in values:
            values["priority"] = values.pop("interest_priority")
        if "interest_level" in values:
            values["relevance"] = values.pop("interest_level")
        if "category" in values:
            cat = values.pop("category")
            if hasattr(cat, "value"):
                values["domain"] = cat.value
            elif isinstance(cat, str):
                values["domain"] = cat
        return values

    # ========================================================================
    # 层级路径方法
    # ========================================================================

    def get_root_domain(self) -> Optional[str]:
        """获取根领域 (hierarchy_path 第一个)"""
        return self.hierarchy_path[0] if self.hierarchy_path else None

    def get_parent_domain(self) -> Optional[str]:
        """获取直接父领域"""
        return self.hierarchy_path[-2] if len(self.hierarchy_path) > 1 else None

    def get_ancestors(self) -> List[str]:
        """获取所有祖先领域 (排除自己)"""
        return self.hierarchy_path[:-1] if len(self.hierarchy_path) > 1 else []

    def is_subdomain_of(self, domain: str) -> bool:
        """判断是否为某领域的子领域"""
        return domain in self.hierarchy_path

    def matches_domain(self, domain: str, include_descendants: bool = True) -> bool:
        """匹配领域"""
        if self.domain == domain:
            return True
        if include_descendants:
            return domain in self.hierarchy_path
        return False

    def set_hierarchy_from_domain(self, domain: str) -> None:
        """根据 domain 设置层级路径"""
        if domain and domain not in self.hierarchy_path:
            self.hierarchy_path = [domain] + self.hierarchy_path

    # ========================================================================
    # 关系方法
    # ========================================================================

    def add_relation(
        self,
        target_id: str,
        relation_type: RelationType,
        properties: Dict[str, Any] = None,
    ) -> None:
        """添加出向关系"""
        relation = {
            "target_id": target_id,
            "type": relation_type.value,
            "properties": properties or {},
        }
        self.outgoing_relations.append(relation)
        self.updated_at = datetime.now().isoformat()

    def add_incoming_relation(
        self,
        source_id: str,
        relation_type: RelationType,
        properties: Dict[str, Any] = None,
    ) -> None:
        """添加入向关系"""
        relation = {
            "source_id": source_id,
            "type": relation_type.value,
            "properties": properties or {},
        }
        self.incoming_relations.append(relation)
        self.updated_at = datetime.now().isoformat()

    def get_related_nodes(self, relation_type: RelationType = None) -> List[str]:
        """获取相关节点ID列表"""
        related = []
        for rel in self.outgoing_relations:
            if relation_type is None or rel["type"] == relation_type.value:
                related.append(rel["target_id"])
        return related

    def get_similar_nodes(self) -> List[str]:
        """获取相似节点"""
        return self.get_related_nodes(RelationType.SIMILAR_TO)

    def get_related_topics(self) -> List[str]:
        """获取相关主题"""
        return self.get_related_nodes(RelationType.RELATED_TO)

    # ========================================================================
    # 兴趣方法
    # ========================================================================

    def mark_accessed(self) -> None:
        """标记已访问"""
        self.access_count += 1
        self.last_accessed = datetime.now().isoformat()
        self.status = InterestStatus.ACTIVE
        self.update_relevance(delta=0.01)
        self.updated_at = datetime.now().isoformat()

    def update_relevance(self, delta: float = 0.01) -> None:
        """更新相关性分数"""
        self.relevance = min(1.0, max(0.0, self.relevance + delta))
        self.updated_at = datetime.now().isoformat()

    def archive(self) -> None:
        """归档兴趣"""
        self.status = InterestStatus.ARCHIVED
        self.updated_at = datetime.now().isoformat()

    def activate(self) -> None:
        """激活兴趣"""
        self.status = InterestStatus.ACTIVE
        self.updated_at = datetime.now().isoformat()

    # ========================================================================
    # 兼容性别名
    # ========================================================================

    @property
    def interest_priority(self) -> int:
        """兼容: priority alias for interest_priority."""
        return self.priority

    @property
    def interest_level(self) -> float:
        """兼容: relevance alias for interest_level."""
        return self.relevance

    @property
    def follow_up_status(self) -> "FollowUpStatus":
        """兼容: maps InterestStatus to FollowUpStatus."""
        mapping = {
            InterestStatus.ACTIVE: FollowUpStatus.FOLLOWED,
            InterestStatus.DORMANT: FollowUpStatus.PENDING,
            InterestStatus.ARCHIVED: FollowUpStatus.ARCHIVED,
        }
        return mapping.get(self.status, FollowUpStatus.NONE)

    @property
    def parent_qids(self) -> List[str]:
        """兼容: parent_ids alias for parent_qids."""
        return self.parent_ids

    @property
    def instance_of_qids(self) -> List[str]:
        """兼容: derived from incoming IS_A relations."""
        return [
            rel["source_id"]
            for rel in self.incoming_relations
            if rel.get("type") == RelationType.IS_A.value
        ]

    # ========================================================================
    # 转换方法
    # ========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump()

    def to_relation_dict(self) -> Dict[str, Any]:
        """转换为关系格式"""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.node_type,
            "domain": self.domain,
            "level": self.level,
        }

    # ========================================================================
    # 从旧类型转换 (向后兼容)
    # ========================================================================

    @classmethod
    def from_interest_tag(cls, tag: "InterestTag", **overrides) -> "UnifiedNode":
        """Create UnifiedNode from InterestTag."""
        return cls(
            id=tag.id,
            name=tag.name,
            domain=tag.category.value
            if hasattr(tag.category, "value")
            else str(tag.category),
            source=NodeSource(tag.source.value)
            if hasattr(tag.source, "value")
            else NodeSource.EXTRACTED,
            wikidata_qid=tag.wikidata_qid,
            wikidata_label=tag.wikidata_label,
            wikidata_description=tag.wikidata_description,
            synonyms=tag.synonyms,
            confidence=tag.confidence,
            properties=tag.properties,
            level=NodeLevel.KNOWLEDGE.value,
            **overrides,
        )

    @classmethod
    def from_user_interest(cls, interest: "UserInterest", **overrides) -> "UnifiedNode":
        """Create UnifiedNode from UserInterest."""
        node = cls.from_interest_tag(interest.tag)
        node.is_interest = True
        node.priority = interest.priority
        node.relevance = interest.relevance_score
        node.access_count = interest.access_count
        node.last_accessed = interest.last_accessed
        node.created_at = interest.created_at
        node.updated_at = interest.updated_at
        for k, v in overrides.items():
            setattr(node, k, v)
        return node

    @classmethod
    def from_ontology_node(cls, node: "OntologyNode", **overrides) -> "UnifiedNode":
        """Create UnifiedNode from OntologyNode."""
        return cls(
            id=node.id,
            name=node.name,
            wikidata_qid=node.wikidata_qid,
            wikidata_label=node.wikidata_label,
            wikidata_description=node.wikidata_description,
            level=node.layer,
            node_type=node.node_type,
            domain=node.category if node.category else "other",
            synonyms=node.synonyms,
            description=node.description,
            confidence=node.confidence,
            is_seed=node.is_seed,
            properties=node.properties,
            created_at=node.created_at,
            updated_at=node.updated_at,
            parent_id=node.parent_qids[0] if node.parent_qids else None,
            parent_ids=node.parent_qids,
            **overrides,
        )


# =============================================================================
# 关系模型 (新增)
# =============================================================================


class OntologyRelation(BaseModel):
    """关系模型"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str
    target_id: str
    relation_type: RelationType
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    properties: Dict[str, Any] = Field(default_factory=dict)
    source: NodeSource = NodeSource.EXTRACTED
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump()


# =============================================================================
# 内容画像 (保留)
# =============================================================================


class ContentProfile(BaseModel):
    """内容画像"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    entry_id: str
    tags: List["InterestTag"] = Field(
        default_factory=list
    )  # Keep InterestTag for compatibility
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
        """Convert to dictionary."""
        return self.model_dump()

    def get_unified_tags(self) -> List["UnifiedNode"]:
        """Get tags as UnifiedNodes."""
        return [tag.to_unified_node() for tag in self.tags]


# =============================================================================
# 向后兼容类型 (废弃警告)
# =============================================================================


class TagSource(str, Enum):
    """废弃: 使用 NodeSource"""

    EXPLICIT = "explicit"
    INFERENCE = "inference"
    BEHAVIOR = "behavior"
    WIKIDATA = "wikidata"


class InterestCategory(str, Enum):
    """废弃: 使用 domain 字符串"""

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


class FollowUpStatus(str, Enum):
    """废弃: 使用 InterestStatus"""

    NONE = "none"
    PENDING = "pending"
    FOLLOWED = "followed"
    ARCHIVED = "archived"


class NodeLayer(int, Enum):
    """废弃: 使用 NodeLevel"""

    WIKIDATA = 2
    LLM_EXPANEDED = 3
    USER_CUSTOM = 4


# ============ Deprecated Types (for backward compatibility) ============


class InterestTag(BaseModel):
    """Deprecated: Use UnifiedNode instead."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    category: InterestCategory = InterestCategory.OTHER
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    source: TagSource = TagSource.INFERENCE
    synonyms: List[str] = Field(default_factory=list)
    properties: Dict[str, Any] = Field(default_factory=dict)
    wikidata_qid: Optional[str] = None
    wikidata_label: Optional[str] = None
    wikidata_description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    def to_unified_node(self, **overrides) -> UnifiedNode:
        """Convert to UnifiedNode."""
        return UnifiedNode.from_interest_tag(self, **overrides)

    @classmethod
    def from_unified_node(cls, node: UnifiedNode) -> "InterestTag":
        """Create InterestTag from UnifiedNode."""
        return cls(
            id=node.id,
            name=node.name,
            category=InterestCategory(node.domain)
            if node.domain in [c.value for c in InterestCategory]
            else InterestCategory.OTHER,
            confidence=node.confidence,
            source=TagSource(node.source.value)
            if isinstance(node.source, NodeSource)
            else node.source,
            synonyms=node.synonyms,
            properties=node.properties,
            wikidata_qid=node.wikidata_qid,
            wikidata_label=node.wikidata_label,
            wikidata_description=node.wikidata_description,
        )


class UserInterest(BaseModel):
    """Deprecated: Use UnifiedNode with is_interest=True instead."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tag: InterestTag
    priority: int = Field(default=0, ge=0, le=5)
    access_count: int = 0
    last_accessed: Optional[str] = None
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    def mark_accessed(self):
        self.access_count += 1
        self.last_accessed = datetime.now().isoformat()
        self.relevance_score = min(1.0, self.relevance_score + 0.01)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    def to_unified_node(self, **overrides) -> UnifiedNode:
        """Convert to UnifiedNode."""
        return UnifiedNode.from_user_interest(self, **overrides)

    @classmethod
    def from_unified_node(cls, node: UnifiedNode) -> "UserInterest":
        """Create UserInterest from UnifiedNode."""
        return cls(
            id=node.id,
            tag=InterestTag.from_unified_node(node),
            priority=node.priority,
            access_count=node.access_count,
            last_accessed=node.last_accessed,
            relevance_score=node.relevance,
            created_at=node.created_at,
            updated_at=node.updated_at,
        )


class OntologyNode(BaseModel):
    """Deprecated: Use UnifiedNode instead."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    node_type: str = "concept"
    category: str = ""
    description: str = ""
    synonyms: List[str] = Field(default_factory=list)
    is_seed: bool = False
    seed_priority: int = 0
    properties: Dict[str, Any] = Field(default_factory=dict)
    relations: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    wikidata_qid: Optional[str] = None
    wikidata_label: Optional[str] = None
    wikidata_description: Optional[str] = None
    layer: int = 2
    parent_qids: List[str] = Field(default_factory=list)
    instance_of_qids: List[str] = Field(default_factory=list)
    last_used: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    def to_unified_node(self, **overrides) -> UnifiedNode:
        """Convert to UnifiedNode."""
        return UnifiedNode.from_ontology_node(self, **overrides)

    @classmethod
    def from_unified_node(cls, node: UnifiedNode) -> "OntologyNode":
        """Create OntologyNode from UnifiedNode."""
        return cls(
            id=node.id,
            name=node.name,
            node_type=node.node_type,
            category=node.domain,
            description=node.description,
            synonyms=node.synonyms,
            is_seed=node.is_seed,
            seed_priority=node.priority if node.is_seed else 0,
            properties=node.properties,
            confidence=node.confidence,
            created_at=node.created_at,
            updated_at=node.updated_at,
            wikidata_qid=node.wikidata_qid,
            wikidata_label=node.wikidata_label,
            wikidata_description=node.wikidata_description,
            layer=node.level,
            parent_qids=node.parent_ids,
            instance_of_qids=node.wikidata_aliases,
            last_used=node.last_used,
        )


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    # 枚举
    "RelationType",
    "NodeLevel",
    "NodeSource",
    "InterestStatus",
    # 核心
    "UnifiedNode",
    "OntologyRelation",
    "ContentProfile",
    # 废弃 (向后兼容)
    "TagSource",
    "InterestCategory",
    "FollowUpStatus",
    "NodeLayer",
    "InterestTag",
    "UserInterest",
    "OntologyNode",
]

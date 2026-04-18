# -*- coding: utf-8 -*-
"""
Ontology Memory - Storage layer for unified ontology nodes and content profiles.

This module provides storage for:
- UnifiedNode: Combined InterestTag, UserInterest, and OntologyNode
- ContentProfile: Feed entry content analysis
- OntologyRelation: Relations between nodes
- Vector embeddings (ChromaDB)

Migration from legacy types:
- InterestTag + UserInterest -> UnifiedNode (is_interest=True)
- OntologyNode -> UnifiedNode
"""

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from .types import (
    UnifiedNode,
    ContentProfile,
    OntologyRelation,
    InterestCategory,
    FollowUpStatus,
    NodeSource,
    InterestStatus,
)


class OntologyMemory:
    """Storage for ontology data using SQLite and ChromaDB."""

    def __init__(self, data_dir: Optional[str] = None):
        """Initialize ontology storage.

        Args:
            data_dir: Base data directory. Defaults to DATA_DIR env var or "./data".
        """
        from src.constants import DATA_DIR as DEFAULT_DATA_DIR

        _data_dir = data_dir or os.getenv("DATA_DIR")
        self.data_dir = Path(_data_dir if _data_dir else str(DEFAULT_DATA_DIR))
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.data_dir / "ontology.db"
        self.chroma_path = self.data_dir / "chroma"

        self._init_sqlite()
        self._init_chroma()

    def _init_sqlite(self):
        """Initialize SQLite database with unified schema."""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        cursor = self.conn.cursor()

        # Unified nodes table (replaces user_interests and ontology_nodes)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                wikidata_qid TEXT,
                category TEXT DEFAULT 'other',
                node_type TEXT DEFAULT 'concept',
                layer INTEGER DEFAULT 3,
                source TEXT DEFAULT 'inference',

                -- Interest tracking fields
                is_interest INTEGER DEFAULT 0,
                interest_priority INTEGER DEFAULT 0,
                interest_level REAL DEFAULT 0.0,
                follow_up_status TEXT DEFAULT 'none',
                access_count INTEGER DEFAULT 0,
                last_accessed TEXT,

                -- Wikidata alignment
                wikidata_label TEXT,
                wikidata_description TEXT,
                parent_qids_json TEXT DEFAULT '[]',
                instance_of_qids_json TEXT DEFAULT '[]',

                -- Additional metadata
                synonyms_json TEXT DEFAULT '[]',
                description TEXT DEFAULT '',
                confidence REAL DEFAULT 1.0,
                is_seed INTEGER DEFAULT 0,
                properties_json TEXT DEFAULT '{}',

                -- System fields
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_used TEXT,

                UNIQUE(wikidata_qid)
            )
        """)

        # Content profiles table (unchanged)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_profiles (
                id TEXT PRIMARY KEY,
                entry_id TEXT NOT NULL UNIQUE,
                tags_json TEXT NOT NULL,
                priority INTEGER DEFAULT 0,
                summary TEXT DEFAULT '',
                key_entities_json TEXT DEFAULT '[]',
                key_concepts_json TEXT DEFAULT '[]',
                sentiment TEXT,
                language TEXT DEFAULT 'en',
                reading_time_seconds INTEGER,
                created_at TEXT NOT NULL,
                metadata_json TEXT DEFAULT '{}'
            )
        """)

        # Ontology edges table (unchanged)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ontology_edges (
                id TEXT PRIMARY KEY,
                source_qid TEXT NOT NULL,
                target_qid TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                edge_source TEXT DEFAULT 'wikidata',
                created_at TEXT NOT NULL,
                UNIQUE(source_qid, target_qid, relation_type)
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_name ON nodes(name)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_nodes_wikidata ON nodes(wikidata_qid)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_layer ON nodes(layer)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_nodes_interest ON nodes(is_interest)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_nodes_category ON nodes(category)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_content_profiles_entry ON content_profiles(entry_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_ontology_edges_source ON ontology_edges(source_qid)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_ontology_edges_target ON ontology_edges(target_qid)"
        )

        # Migration: Check for legacy tables and mark for migration
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='user_interests'"
        )
        if cursor.fetchone():
            self._migrate_from_legacy(cursor)

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='ontology_nodes'"
        )
        if cursor.fetchone():
            self._migrate_ontology_nodes(cursor)

        self.conn.commit()

    def _migrate_from_legacy(self, cursor):
        """Migrate legacy user_interests table to unified nodes table."""
        cursor.execute("SELECT * FROM user_interests")
        for row in cursor.fetchall():
            now = datetime.now().isoformat()
            cursor.execute(
                """
                INSERT OR REPLACE INTO nodes
                (id, name, category, source, wikidata_qid, wikidata_label,
                 wikidata_description, confidence, is_interest, interest_priority,
                 interest_level, access_count, last_accessed, created_at, updated_at,
                 layer, synonyms_json, properties_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, 3, '[]', '{}')
            """,
                (
                    row["tag_id"],
                    row["tag_name"],
                    row["tag_category"],
                    row["tag_source"],
                    None,  # wikidata_qid
                    None,  # wikidata_label
                    None,  # wikidata_description
                    row["tag_confidence"],
                    row["priority"],
                    row["relevance_score"],
                    row["access_count"],
                    row["last_accessed"],
                    row["created_at"],
                    now,
                ),
            )
        # Don't delete legacy table yet, in case migration needs rollback

    def _migrate_ontology_nodes(self, cursor):
        """Migrate legacy ontology_nodes table to unified nodes table."""
        cursor.execute("SELECT * FROM ontology_nodes")
        for row in cursor.fetchall():
            now = datetime.now().isoformat()
            # Check if already migrated via user_interests
            cursor.execute("SELECT id FROM nodes WHERE id = ?", (row["id"],))
            if cursor.fetchone():
                continue

            cursor.execute(
                """
                INSERT OR REPLACE INTO nodes
                (id, name, wikidata_qid, wikidata_label, wikidata_description,
                 layer, node_type, category, synonyms_json, description,
                 confidence, is_seed, properties_json, created_at, updated_at,
                 parent_qids_json, instance_of_qids_json, last_used)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    row["id"],
                    row["name"],
                    row["wikidata_qid"],
                    row["wikidata_label"],
                    row["wikidata_description"],
                    row["layer"],
                    row["node_type"],
                    row["category"],
                    row["synonyms_json"],
                    row["wikidata_description"] or "",
                    row["confidence"],
                    1 if row.get("is_seed") else 0,
                    "{}",
                    row["created_at"],
                    now,
                    row["parent_qids_json"],
                    row["instance_of_qids_json"],
                    row["last_used"],
                ),
            )

    def _init_chroma(self):
        """Initialize ChromaDB for vector storage."""
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.chroma_path),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.vector_collection = self.chroma_client.get_or_create_collection(
            name="ontology_vectors",
            metadata={"description": "Vector embeddings for ontology"},
        )

    # ============ Unified Node Operations ============

    def save_node(self, node: UnifiedNode) -> None:
        """Save or update a unified node."""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()

        cursor.execute(
            """
            INSERT OR REPLACE INTO nodes
            (id, name, wikidata_qid, category, node_type, layer, source,
             is_interest, interest_priority, interest_level, follow_up_status,
             access_count, last_accessed, wikidata_label, wikidata_description,
             parent_qids_json, instance_of_qids_json, synonyms_json, description,
             confidence, is_seed, properties_json, created_at, updated_at, last_used)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                node.id,
                node.name,
                node.wikidata_qid,
                node.category.value
                if hasattr(node.category, "value")
                else node.category,
                node.node_type,
                node.level,
                node.source.value if hasattr(node.source, "value") else node.source,
                1 if node.is_interest else 0,
                node.interest_priority,
                node.interest_level,
                node.follow_up_status.value,
                node.access_count,
                node.last_accessed,
                node.wikidata_label,
                node.wikidata_description,
                json.dumps(node.parent_qids),
                json.dumps(node.instance_of_qids),
                json.dumps(node.synonyms),
                node.description,
                node.confidence,
                1 if node.is_seed else 0,
                json.dumps(node.properties),
                node.created_at,
                now,
                node.last_used,
            ),
        )
        self.conn.commit()

    def get_node(self, node_id: str) -> Optional[UnifiedNode]:
        """Get node by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM nodes WHERE id = ?", (node_id,))
        row = cursor.fetchone()
        return self._row_to_node(row) if row else None

    def get_node_by_qid(self, qid: str) -> Optional[UnifiedNode]:
        """Get node by Wikidata QID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM nodes WHERE wikidata_qid = ?", (qid,))
        row = cursor.fetchone()
        return self._row_to_node(row) if row else None

    def get_all_nodes(
        self,
        layer: Optional[int] = None,
        category: Optional[InterestCategory] = None,
        is_interest: Optional[bool] = None,
    ) -> List[UnifiedNode]:
        """Get all nodes with optional filters."""
        cursor = self.conn.cursor()

        conditions = []
        params = []
        if layer is not None:
            conditions.append("layer = ?")
            params.append(layer)
        if category is not None:
            conditions.append("category = ?")
            params.append(category.value)
        if is_interest is not None:
            conditions.append("is_interest = ?")
            params.append(1 if is_interest else 0)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        cursor.execute(
            f"SELECT * FROM nodes WHERE {where_clause} ORDER BY name", params
        )
        return [self._row_to_node(row) for row in cursor.fetchall()]

    def get_user_interests(self, min_priority: int = 0) -> List[UnifiedNode]:
        """Get user interests with optional priority filter."""
        cursor = self.conn.cursor()
        if min_priority > 0:
            cursor.execute(
                "SELECT * FROM nodes WHERE is_interest = 1 AND interest_priority >= ? "
                "ORDER BY interest_priority DESC, interest_level DESC",
                (min_priority,),
            )
        else:
            cursor.execute(
                "SELECT * FROM nodes WHERE is_interest = 1 "
                "ORDER BY interest_priority DESC, interest_level DESC"
            )
        return [self._row_to_node(row) for row in cursor.fetchall()]

    def get_pending_follow_ups(self) -> List[UnifiedNode]:
        """Get nodes with pending follow-up status."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM nodes WHERE is_interest = 1 AND follow_up_status = ? ORDER BY interest_priority DESC",
            (FollowUpStatus.PENDING.value,),
        )
        return [self._row_to_node(row) for row in cursor.fetchall()]

    def search_nodes(self, query: str, limit: int = 10) -> List[UnifiedNode]:
        """Search nodes by name or synonyms."""
        cursor = self.conn.cursor()
        search_pattern = f"%{query}%"
        cursor.execute(
            """
            SELECT * FROM nodes
            WHERE name LIKE ? OR synonyms_json LIKE ?
            ORDER BY
                CASE WHEN name LIKE ? THEN 0 ELSE 1 END,
                interest_level DESC
            LIMIT ?
        """,
            (search_pattern, search_pattern, search_pattern, limit),
        )
        return [self._row_to_node(row) for row in cursor.fetchall()]

    def delete_node(self, node_id: str) -> bool:
        """Delete node by ID."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def _row_to_node(self, row: sqlite3.Row) -> UnifiedNode:
        """Convert SQLite row to UnifiedNode."""
        follow_up_status = row["follow_up_status"]
        interest_status_map = {
            "none": InterestStatus.ACTIVE,
            "pending": InterestStatus.DORMANT,
            "followed": InterestStatus.ACTIVE,
            "archived": InterestStatus.ARCHIVED,
        }
        status = interest_status_map.get(follow_up_status, InterestStatus.ACTIVE)
        return UnifiedNode(
            id=row["id"],
            name=row["name"],
            wikidata_qid=row["wikidata_qid"],
            domain=row["category"],
            node_type=row["node_type"],
            level=row["layer"],
            source=NodeSource(row["source"]),
            is_interest=bool(row["is_interest"]),
            priority=row["interest_priority"],
            relevance=row["interest_level"],
            status=status,
            access_count=row["access_count"],
            last_accessed=row["last_accessed"],
            wikidata_label=row["wikidata_label"],
            wikidata_description=row["wikidata_description"],
            parent_ids=json.loads(row["parent_qids_json"]),
            synonyms=json.loads(row["synonyms_json"]),
            description=row["description"],
            confidence=row["confidence"],
            is_seed=bool(row["is_seed"]),
            properties=json.loads(row["properties_json"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_used=row["last_used"],
        )

    # ============ User Interests (Legacy Compatibility) ============

    def save_user_interest(self, interest) -> None:
        """Save user interest (converts to UnifiedNode)."""
        if isinstance(interest, UnifiedNode):
            node = interest
            node.is_interest = True
        else:
            node = UnifiedNode.from_user_interest(interest)
        self.save_node(node)

    def get_user_interest(self, interest_id: str) -> Optional[UnifiedNode]:
        """Get user interest by ID."""
        return self.get_node(interest_id)

    def get_all_user_interests(self) -> List[UnifiedNode]:
        """Get all user interests."""
        return self.get_user_interests()

    def delete_user_interest(self, interest_id: str) -> bool:
        """Delete user interest."""
        return self.delete_node(interest_id)

    # ============ Ontology Nodes (Legacy Compatibility) ============

    def save_ontology_node(self, node) -> None:
        """Save ontology node (converts to UnifiedNode)."""
        if isinstance(node, UnifiedNode):
            self.save_node(node)
        else:
            unified = UnifiedNode.from_ontology_node(node)
            self.save_node(unified)

    def get_ontology_node(self, qid: str) -> Optional[UnifiedNode]:
        """Get ontology node by QID."""
        return self.get_node_by_qid(qid)

    def get_all_ontology_nodes(self, layer: Optional[int] = None) -> List[UnifiedNode]:
        """Get all ontology nodes."""
        return self.get_all_nodes(layer=layer, is_interest=False)

    # ============ Content Profiles ============

    def save_content_profile(self, profile: ContentProfile) -> None:
        """Save or update content profile."""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()

        tags_json = json.dumps([t.model_dump() for t in profile.tags])
        entities_json = json.dumps(profile.key_entities)
        concepts_json = json.dumps(profile.key_concepts)
        metadata_json = json.dumps(profile.metadata)

        cursor.execute(
            """
            INSERT OR REPLACE INTO content_profiles
            (id, entry_id, tags_json, priority, summary, key_entities_json,
             key_concepts_json, sentiment, language, reading_time_seconds, created_at, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                profile.id,
                profile.entry_id,
                tags_json,
                profile.priority,
                profile.summary,
                entities_json,
                concepts_json,
                profile.sentiment,
                profile.language,
                profile.reading_time_seconds,
                now,
                metadata_json,
            ),
        )
        self.conn.commit()

        self._save_content_vectors(profile)

    def get_content_profile(self, entry_id: str) -> Optional[ContentProfile]:
        """Get content profile by entry ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM content_profiles WHERE entry_id = ?", (entry_id,))
        row = cursor.fetchone()
        return self._row_to_content_profile(row) if row else None

    def get_recent_profiles(self, limit: int = 50) -> List[ContentProfile]:
        """Get recent content profiles."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM content_profiles ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        return [self._row_to_content_profile(row) for row in cursor.fetchall()]

    def _row_to_content_profile(self, row: sqlite3.Row) -> ContentProfile:
        """Convert SQLite row to ContentProfile."""
        from .types import UnifiedNode

        tags = [UnifiedNode(**t) for t in json.loads(row["tags_json"])]
        return ContentProfile(
            id=row["id"],
            entry_id=row["entry_id"],
            tags=tags,
            priority=row["priority"],
            summary=row["summary"],
            key_entities=json.loads(row["key_entities_json"]),
            key_concepts=json.loads(row["key_concepts_json"]),
            sentiment=row["sentiment"],
            language=row["language"],
            reading_time_seconds=row["reading_time_seconds"],
            created_at=row["created_at"],
            metadata=json.loads(row["metadata_json"]),
        )

    def _save_content_vectors(self, profile: ContentProfile) -> None:
        """Save content profile vectors to ChromaDB."""
        if profile.summary:
            self.vector_collection.upsert(
                ids=[profile.id],
                documents=[profile.summary],
                metadatas=[
                    {
                        "entry_id": profile.entry_id,
                        "type": "summary",
                        "tags": [t.name for t in profile.tags],
                    }
                ],
            )

        for i, entity in enumerate(profile.key_entities[:10]):
            self.vector_collection.upsert(
                ids=[f"{profile.id}_entity_{i}"],
                documents=[entity],
                metadatas=[
                    {
                        "entry_id": profile.entry_id,
                        "type": "entity",
                        "profile_id": profile.id,
                    }
                ],
            )

    def search_similar_content(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Search for similar content using vector similarity."""
        results = self.vector_collection.query(query_texts=[query], n_results=limit)
        return results

    # ============ Ontology Relations ============

    def save_ontology_edge(self, edge: OntologyRelation) -> None:
        """Save or update ontology edge."""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()

        cursor.execute(
            """
            INSERT OR REPLACE INTO ontology_edges
            (id, source_qid, target_qid, relation_type, weight, edge_source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                edge.id,
                edge.source_id,
                edge.target_id,
                edge.relation_type,
                edge.weight,
                edge.properties.get("edge_source", "wikidata"),
                now,
            ),
        )
        self.conn.commit()

    def get_node_edges(
        self, qid: str, direction: str = "outgoing"
    ) -> List[OntologyRelation]:
        """Get edges for a node."""
        cursor = self.conn.cursor()

        if direction == "outgoing":
            cursor.execute("SELECT * FROM ontology_edges WHERE source_qid = ?", (qid,))
        elif direction == "incoming":
            cursor.execute("SELECT * FROM ontology_edges WHERE target_qid = ?", (qid,))
        else:
            cursor.execute(
                "SELECT * FROM ontology_edges WHERE source_qid = ? OR target_qid = ?",
                (qid, qid),
            )

        edges = []
        for row in cursor.fetchall():
            edges.append(
                OntologyRelation(
                    id=row["id"],
                    source_id=row["source_qid"],
                    target_id=row["target_qid"],
                    relation_type=row["relation_type"],
                    weight=row["weight"],
                    properties={"edge_source": row["edge_source"]},
                    created_at=row["created_at"],
                )
            )
        return edges

    def get_all_ontology_edges(self) -> List[OntologyRelation]:
        """Get all ontology edges."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM ontology_edges")

        edges = []
        for row in cursor.fetchall():
            edges.append(
                OntologyRelation(
                    id=row["id"],
                    source_id=row["source_qid"],
                    target_id=row["target_qid"],
                    relation_type=row["relation_type"],
                    weight=row["weight"],
                    properties={"edge_source": row["edge_source"]},
                    created_at=row["created_at"],
                )
            )
        return edges

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

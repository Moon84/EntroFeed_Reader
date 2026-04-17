# -*- coding: utf-8 -*-
"""
Ontology Memory - Storage layer for user interests and content profiles.

This module provides storage for:
- User interests (SQLite)
- Content profiles (SQLite)
- Vector embeddings (ChromaDB)

Note: Graph propagation is handled by GraphPropagationScorer (in-memory, hardcoded DOMAIN_HIERARCHY).
The SQLite-based graph system has been removed as redundant.
"""
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from .types import (
    InterestTag,
    UserInterest,
    ContentProfile,
    TagSource,
    InterestCategory,
)


class OntologyMemory:
    """Storage for ontology data using SQLite and ChromaDB."""

    def __init__(self, data_dir: str = None):
        """Initialize ontology storage.

        Args:
            data_dir: Base data directory. Defaults to DATA_DIR env var or "./data".
        """
        self.data_dir = Path(data_dir or os.getenv("DATA_DIR", "./data"))
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.data_dir / "ontology.db"
        self.chroma_path = self.data_dir / "chroma"

        self._init_sqlite()
        self._init_chroma()

    def _init_sqlite(self):
        """Initialize SQLite database with schema."""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        cursor = self.conn.cursor()

        # User interests table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_interests (
                id TEXT PRIMARY KEY,
                tag_id TEXT NOT NULL,
                tag_name TEXT NOT NULL,
                tag_category TEXT NOT NULL,
                tag_confidence REAL DEFAULT 0.0,
                tag_source TEXT DEFAULT 'inference',
                priority INTEGER DEFAULT 0,
                access_count INTEGER DEFAULT 0,
                last_accessed TEXT,
                relevance_score REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Content profiles table
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

        # Ontology nodes table (Wikidata + custom entities)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ontology_nodes (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                wikidata_qid TEXT UNIQUE,
                wikidata_label TEXT,
                wikidata_description TEXT,
                layer INTEGER DEFAULT 2,
                node_type TEXT DEFAULT 'concept',
                category TEXT,
                synonyms_json TEXT DEFAULT '[]',
                parent_qids_json TEXT DEFAULT '[]',
                instance_of_qids_json TEXT DEFAULT '[]',
                confidence REAL DEFAULT 1.0,
                last_used TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Ontology edges table (relations between nodes)
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
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_interests_tag ON user_interests(tag_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_profiles_entry ON content_profiles(entry_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ontology_nodes_qid ON ontology_nodes(wikidata_qid)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ontology_nodes_layer ON ontology_nodes(layer)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ontology_edges_source ON ontology_edges(source_qid)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ontology_edges_target ON ontology_edges(target_qid)")

        self.conn.commit()

    def _init_chroma(self):
        """Initialize ChromaDB for vector storage."""
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.chroma_path),
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        self.vector_collection = self.chroma_client.get_or_create_collection(
            name="ontology_vectors",
            metadata={"description": "Vector embeddings for ontology"}
        )

    # ============ User Interests ============

    def save_user_interest(self, interest: UserInterest) -> None:
        """Save or update user interest."""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()

        cursor.execute("""
            INSERT OR REPLACE INTO user_interests
            (id, tag_id, tag_name, tag_category, tag_confidence, tag_source,
             priority, access_count, last_accessed, relevance_score, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            interest.id,
            interest.tag.id,
            interest.tag.name,
            interest.tag.category.value,
            interest.tag.confidence,
            interest.tag.source.value,
            interest.priority,
            interest.access_count,
            interest.last_accessed,
            interest.relevance_score,
            interest.created_at,
            now
        ))
        self.conn.commit()

    def get_user_interest(self, interest_id: str) -> Optional[UserInterest]:
        """Get user interest by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM user_interests WHERE id = ?", (interest_id,))
        row = cursor.fetchone()
        return self._row_to_user_interest(row) if row else None

    def get_all_user_interests(self) -> List[UserInterest]:
        """Get all user interests ordered by priority."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM user_interests ORDER BY priority DESC, relevance_score DESC")
        return [self._row_to_user_interest(row) for row in cursor.fetchall()]

    def get_user_interests_by_category(self, category: InterestCategory) -> List[UserInterest]:
        """Get user interests filtered by category."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM user_interests WHERE tag_category = ? ORDER BY priority DESC",
            (category.value,)
        )
        return [self._row_to_user_interest(row) for row in cursor.fetchall()]

    def delete_user_interest(self, interest_id: str) -> bool:
        """Delete user interest by ID."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM user_interests WHERE id = ?", (interest_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def _row_to_user_interest(self, row: sqlite3.Row) -> UserInterest:
        """Convert SQLite row to UserInterest."""
        tag = InterestTag(
            id=row["tag_id"],
            name=row["tag_name"],
            category=InterestCategory(row["tag_category"]),
            confidence=row["tag_confidence"],
            source=TagSource(row["tag_source"])
        )
        return UserInterest(
            id=row["id"],
            tag=tag,
            priority=row["priority"],
            access_count=row["access_count"],
            last_accessed=row["last_accessed"],
            relevance_score=row["relevance_score"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

    # ============ Content Profiles ============

    def save_content_profile(self, profile: ContentProfile) -> None:
        """Save or update content profile."""
        import json
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()

        tags_json = json.dumps([t.model_dump() for t in profile.tags])
        entities_json = json.dumps(profile.key_entities)
        concepts_json = json.dumps(profile.key_concepts)
        metadata_json = json.dumps(profile.metadata)

        cursor.execute("""
            INSERT OR REPLACE INTO content_profiles
            (id, entry_id, tags_json, priority, summary, key_entities_json,
             key_concepts_json, sentiment, language, reading_time_seconds, created_at, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
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
            metadata_json
        ))
        self.conn.commit()

        # Also store vectors in ChromaDB
        self._save_content_vectors(profile)

    def get_content_profile(self, entry_id: str) -> Optional[ContentProfile]:
        """Get content profile by entry ID."""
        import json
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM content_profiles WHERE entry_id = ?", (entry_id,))
        row = cursor.fetchone()
        return self._row_to_content_profile(row) if row else None

    def get_recent_profiles(self, limit: int = 50) -> List[ContentProfile]:
        """Get recent content profiles."""
        import json
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM content_profiles ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        return [self._row_to_content_profile(row) for row in cursor.fetchall()]

    def _row_to_content_profile(self, row: sqlite3.Row) -> ContentProfile:
        """Convert SQLite row to ContentProfile."""
        import json
        tags = [InterestTag(**t) for t in json.loads(row["tags_json"])]
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
            metadata=json.loads(row["metadata_json"])
        )

    def _save_content_vectors(self, profile: ContentProfile) -> None:
        """Save content profile vectors to ChromaDB."""
        # Store summary as vector
        if profile.summary:
            self.vector_collection.upsert(
                ids=[profile.id],
                documents=[profile.summary],
                metadatas=[{
                    "entry_id": profile.entry_id,
                    "type": "summary",
                    "tags": [t.name for t in profile.tags]
                }]
            )

        # Store entities as separate vectors
        for i, entity in enumerate(profile.key_entities[:10]):  # Limit to 10 entities
            self.vector_collection.upsert(
                ids=[f"{profile.id}_entity_{i}"],
                documents=[entity],
                metadatas=[{
                    "entry_id": profile.entry_id,
                    "type": "entity",
                    "profile_id": profile.id
                }]
            )

    def search_similar_content(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar content using vector similarity."""
        results = self.vector_collection.query(
            query_texts=[query],
            n_results=limit
        )
        return results

    # ============ Ontology Graph Storage ============

    def save_ontology_node(self, node: 'OntologyNode') -> None:
        """Save or update ontology node."""
        import json
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()

        cursor.execute("""
            INSERT OR REPLACE INTO ontology_nodes
            (id, name, wikidata_qid, wikidata_label, wikidata_description, layer,
             node_type, category, synonyms_json, parent_qids_json, instance_of_qids_json,
             confidence, last_used, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            node.id,
            node.name,
            node.wikidata_qid,
            node.wikidata_label,
            node.wikidata_description,
            node.layer,
            node.node_type,
            node.category,
            json.dumps(node.synonyms),
            json.dumps(node.parent_qids),
            json.dumps(node.instance_of_qids),
            node.confidence,
            now,
            node.created_at,
            now
        ))
        self.conn.commit()

    def get_ontology_node(self, qid: str) -> Optional['OntologyNode']:
        """Get ontology node by QID."""
        import json
        from .types import OntologyNode
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM ontology_nodes WHERE wikidata_qid = ?", (qid,))
        row = cursor.fetchone()
        if not row:
            return None

        return OntologyNode(
            id=row["id"],
            name=row["name"],
            wikidata_qid=row["wikidata_qid"],
            wikidata_label=row["wikidata_label"],
            wikidata_description=row["wikidata_description"],
            layer=row["layer"],
            node_type=row["node_type"],
            category=row["category"],
            synonyms=json.loads(row["synonyms_json"]),
            parent_qids=json.loads(row["parent_qids_json"]),
            instance_of_qids=json.loads(row["instance_of_qids_json"]),
            confidence=row["confidence"],
            created_at=row["created_at"],
            last_used=row["last_used"]
        )

    def get_all_ontology_nodes(self, layer: int = None) -> List['OntologyNode']:
        """Get all ontology nodes, optionally filtered by layer."""
        import json
        from .types import OntologyNode
        cursor = self.conn.cursor()

        if layer is not None:
            cursor.execute("SELECT * FROM ontology_nodes WHERE layer = ? ORDER BY name", (layer,))
        else:
            cursor.execute("SELECT * FROM ontology_nodes ORDER BY name")

        nodes = []
        for row in cursor.fetchall():
            nodes.append(OntologyNode(
                id=row["id"],
                name=row["name"],
                wikidata_qid=row["wikidata_qid"],
                wikidata_label=row["wikidata_label"],
                wikidata_description=row["wikidata_description"],
                layer=row["layer"],
                node_type=row["node_type"],
                category=row["category"],
                synonyms=json.loads(row["synonyms_json"]),
                parent_qids=json.loads(row["parent_qids_json"]),
                instance_of_qids=json.loads(row["instance_of_qids_json"]),
                confidence=row["confidence"],
                created_at=row["created_at"],
                last_used=row["last_used"]
            ))
        return nodes

    def save_ontology_edge(self, edge: 'OntologyRelation') -> None:
        """Save or update ontology edge."""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()

        cursor.execute("""
            INSERT OR REPLACE INTO ontology_edges
            (id, source_qid, target_qid, relation_type, weight, edge_source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            edge.id,
            edge.source_id,
            edge.target_id,
            edge.relation_type,
            edge.weight,
            edge.properties.get("edge_source", "wikidata"),
            now
        ))
        self.conn.commit()

    def get_node_edges(self, qid: str, direction: str = "outgoing") -> List['OntologyRelation']:
        """Get edges for a node.

        Args:
            qid: Node QID
            direction: "outgoing", "incoming", or "both"
        """
        import json
        from .types import OntologyRelation
        cursor = self.conn.cursor()

        if direction == "outgoing":
            cursor.execute("SELECT * FROM ontology_edges WHERE source_qid = ?", (qid,))
        elif direction == "incoming":
            cursor.execute("SELECT * FROM ontology_edges WHERE target_qid = ?", (qid,))
        else:  # both
            cursor.execute(
                "SELECT * FROM ontology_edges WHERE source_qid = ? OR target_qid = ?",
                (qid, qid)
            )

        edges = []
        for row in cursor.fetchall():
            edges.append(OntologyRelation(
                id=row["id"],
                source_id=row["source_qid"],
                target_id=row["target_qid"],
                relation_type=row["relation_type"],
                weight=row["weight"],
                properties={"edge_source": row["edge_source"]},
                created_at=row["created_at"]
            ))
        return edges

    def get_all_ontology_edges(self) -> List['OntologyRelation']:
        """Get all ontology edges."""
        from .types import OntologyRelation
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM ontology_edges")

        edges = []
        for row in cursor.fetchall():
            edges.append(OntologyRelation(
                id=row["id"],
                source_id=row["source_qid"],
                target_id=row["target_qid"],
                relation_type=row["relation_type"],
                weight=row["weight"],
                properties={"edge_source": row["edge_source"]},
                created_at=row["created_at"]
            ))
        return edges

    def delete_ontology_node(self, qid: str) -> bool:
        """Delete ontology node and its edges."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM ontology_nodes WHERE wikidata_qid = ?", (qid,))
        cursor.execute("DELETE FROM ontology_edges WHERE source_qid = ? OR target_qid = ?", (qid, qid))
        self.conn.commit()
        return cursor.rowcount > 0

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

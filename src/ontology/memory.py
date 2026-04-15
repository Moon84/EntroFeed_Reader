# -*- coding: utf-8 -*-
"""
Ontology Memory - Storage layer for user interests and content profiles.

This module provides storage for:
- User interests (SQLite)
- Content profiles (SQLite)
- Ontology graph (SQLite)
- Vector embeddings (ChromaDB)
"""
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from src.ontology.types import (
    InterestTag,
    UserInterest,
    ContentProfile,
    OntologyNode,
    OntologyRelation,
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

        # Ontology nodes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ontology_nodes (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                node_type TEXT NOT NULL,
                category TEXT DEFAULT '',
                description TEXT DEFAULT '',
                properties_json TEXT DEFAULT '{}',
                relations_json TEXT DEFAULT '[]',
                confidence REAL DEFAULT 1.0,
                created_at TEXT NOT NULL
            )
        """)

        # Ontology relations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ontology_relations (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                properties_json TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY (source_id) REFERENCES ontology_nodes(id),
                FOREIGN KEY (target_id) REFERENCES ontology_nodes(id)
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_interests_tag ON user_interests(tag_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_profiles_entry ON content_profiles(entry_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ontology_nodes_name ON ontology_nodes(name)")

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

    # ============ Ontology Nodes ============

    def save_ontology_node(self, node: OntologyNode) -> None:
        """Save or update ontology node."""
        import json
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO ontology_nodes
            (id, name, node_type, category, description, properties_json, relations_json, confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            node.id,
            node.name,
            node.node_type,
            node.category,
            node.description,
            json.dumps(node.properties),
            json.dumps(node.relations),
            node.confidence,
            node.created_at
        ))
        self.conn.commit()

    def get_ontology_node(self, node_id: str) -> Optional[OntologyNode]:
        """Get ontology node by ID."""
        import json
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM ontology_nodes WHERE id = ?", (node_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return OntologyNode(
            id=row["id"],
            name=row["name"],
            node_type=row["node_type"],
            category=row["category"],
            description=row["description"],
            properties=json.loads(row["properties_json"]),
            relations=json.loads(row["relations_json"]),
            confidence=row["confidence"],
            created_at=row["created_at"]
        )

    def search_ontology_nodes(self, query: str, limit: int = 20) -> List[OntologyNode]:
        """Search ontology nodes by name."""
        import json
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM ontology_nodes WHERE name LIKE ? LIMIT ?",
            (f"%{query}%", limit)
        )
        return [
            OntologyNode(
                id=row["id"],
                name=row["name"],
                node_type=row["node_type"],
                category=row["category"],
                description=row["description"],
                properties=json.loads(row["properties_json"]),
                relations=json.loads(row["relations_json"]),
                confidence=row["confidence"],
                created_at=row["created_at"]
            )
            for row in cursor.fetchall()
        ]

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

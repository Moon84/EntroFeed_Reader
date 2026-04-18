# -*- coding: utf-8 -*-
"""SQLite Storage Handler - Storage implementation using SQLite and ChromaDB.

This module provides a complete storage implementation using:
- SQLite for structured data (feeds, entries, settings, handlers)
- ChromaDB for vector storage (embeddings)
"""
import json
import sqlite3
from datetime import datetime
from time import time
from typing import Dict, List, Mapping, Optional, Type

import chromadb
from chromadb.config import Settings as ChromaSettings

from src.constants import DATA_DIR
from src.plugins.storage.handler import StorageHandler
from src.handlers import HandlerBase
from src.models.feed import EntryContent, Feed, FeedEntry
from src.settings import GlobalSettings


# Ensure data dir exists
DATA_DIR.mkdir(parents=True, exist_ok=True)


class SQLiteStorageHandler(StorageHandler):
    """SQLite-based storage handler with ChromaDB for embeddings."""

    def __init__(self):
        """Initialize SQLite storage."""
        self.db_path = DATA_DIR / "entrofeed.db"
        self.chroma_path = DATA_DIR / "chroma"

        self._init_sqlite()
        self._init_chroma()

    def _init_sqlite(self):
        """Initialize SQLite database with schema."""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        cursor = self.conn.cursor()

        # Feeds table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feeds (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT DEFAULT 'uncategorized',
                type TEXT DEFAULT 'rss',
                url TEXT NOT NULL UNIQUE,
                notify_destination TEXT,
                notify INTEGER DEFAULT 1,
                preview_only INTEGER DEFAULT 0,
                refresh_enabled INTEGER DEFAULT 1,
                use_script INTEGER DEFAULT 0,
                retrieve_content INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Feed entries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feed_entries (
                id TEXT PRIMARY KEY,
                feed_id TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                published_at INTEGER,
                updated_at INTEGER,
                content TEXT,
                authors TEXT DEFAULT '[]',
                preview TEXT,
                created_at TEXT NOT NULL,
                updated_at_entry TEXT NOT NULL,
                FOREIGN KEY (feed_id) REFERENCES feeds(id)
            )
        """)

        # Entry content table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entry_content (
                id TEXT PRIMARY KEY,
                entry_id TEXT NOT NULL UNIQUE,
                url TEXT NOT NULL,
                content TEXT,
                summary TEXT,
                unretrievable INTEGER DEFAULT 0,
                banned INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)

        # Poll state table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS poll_state (
                feed_id TEXT PRIMARY KEY,
                last_polled_at INTEGER,
                start_ts INTEGER,
                FOREIGN KEY (feed_id) REFERENCES feeds(id)
            )
        """)

        # Handlers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS handlers (
                id TEXT PRIMARY KEY,
                handler_type TEXT NOT NULL,
                config_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                settings_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entries_feed ON feed_entries(feed_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entries_published ON feed_entries(published_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_entry ON entry_content(entry_id)")

        # Migration: Add read/like/favorite columns if they don't exist
        cursor.execute("PRAGMA table_info(feed_entries)")
        existing_columns = [col[1] for col in cursor.fetchall()]
        if 'is_read' not in existing_columns:
            cursor.execute("ALTER TABLE feed_entries ADD COLUMN is_read INTEGER DEFAULT 0")
        if 'read_at' not in existing_columns:
            cursor.execute("ALTER TABLE feed_entries ADD COLUMN read_at INTEGER")
        if 'liked' not in existing_columns:
            cursor.execute("ALTER TABLE feed_entries ADD COLUMN liked INTEGER DEFAULT 0")
        if 'is_favorite' not in existing_columns:
            cursor.execute("ALTER TABLE feed_entries ADD COLUMN is_favorite INTEGER DEFAULT 0")

        # Token usage table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS token_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                model TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                total_tokens INTEGER
            )
        """)

        self.conn.commit()

    def _init_chroma(self):
        """Initialize ChromaDB for embeddings."""
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.chroma_path),
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        self.embeddings_collection = self.chroma_client.get_or_create_collection(
            name="entry_embeddings",
            metadata={"description": "Entry content embeddings"}
        )

    # ============ Feed Operations ============

    def clear_active_feeds(self) -> None:
        """Remove all feeds from database."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM feed_entries WHERE feed_id IN (SELECT id FROM feeds)")
        cursor.execute("DELETE FROM poll_state")
        cursor.execute("DELETE FROM feeds")
        self.conn.commit()

    def upsert_feed(self, feed: Feed) -> None:
        """Insert or update a feed."""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()

        cursor.execute("""
            INSERT OR REPLACE INTO feeds
            (id, name, category, type, url, notify_destination, notify,
             preview_only, refresh_enabled, use_script, retrieve_content, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            feed.id, feed.name, feed.category, feed.type, feed.url,
            feed.notify_destination, int(feed.notify), int(feed.preview_only),
            int(feed.refresh_enabled), int(feed.use_script), int(feed.retrieve_content),
            now, now
        ))
        self.conn.commit()

    def insert_feed(self, feed: Feed) -> None:
        """Insert a new feed (fails if exists)."""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO feeds
            (id, name, category, type, url, notify_destination, notify,
             preview_only, refresh_enabled, use_script, retrieve_content, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            feed.id, feed.name, feed.category, feed.type, feed.url,
            feed.notify_destination, int(feed.notify), int(feed.preview_only),
            int(feed.refresh_enabled), int(feed.use_script), int(feed.retrieve_content),
            now, now
        ))
        self.conn.commit()

    def get_feed(self, id: str) -> Feed:
        """Get feed by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM feeds WHERE id = ?", (id,))
        row = cursor.fetchone()

        if not row:
            raise ValueError(f"Feed {id} not found")

        return self._row_to_feed(row)

    def get_feeds(self) -> List[Feed]:
        """Get all feeds."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM feeds ORDER BY name")
        return [self._row_to_feed(row) for row in cursor.fetchall()]

    def _row_to_feed(self, row: sqlite3.Row) -> Feed:
        """Convert row to Feed."""
        return Feed(
            name=row["name"],
            category=row["category"],
            type=row["type"],
            url=row["url"],
            notify_destination=row["notify_destination"],
            notify=bool(row["notify"]),
            preview_only=bool(row["preview_only"]),
            refresh_enabled=bool(row["refresh_enabled"]),
            use_script=bool(row["use_script"]),
            retrieve_content=bool(row["retrieve_content"]),
        )

    # ============ Poll State ============

    def get_poll_state(self, feed: Feed) -> Optional[int]:
        """Get poll state timestamp for feed."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT last_polled_at FROM poll_state WHERE feed_id = ?", (feed.id,))
        row = cursor.fetchone()
        return row["last_polled_at"] if row else None

    def set_feed_start_ts(self, feed: Feed, start_ts: int) -> None:
        """Set start timestamp for feed."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO poll_state (feed_id, start_ts)
            VALUES (?, ?)
        """, (feed.id, start_ts))
        self.conn.commit()

    def get_feed_start_ts(self, feed: Feed) -> int:
        """Get start timestamp for feed."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT start_ts FROM poll_state WHERE feed_id = ?", (feed.id,))
        row = cursor.fetchone()
        return row["start_ts"] if row and row["start_ts"] else 0

    def update_poll_state(self, feed: Feed, now: int) -> None:
        """Update poll state."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO poll_state (feed_id, last_polled_at)
            VALUES (?, ?)
        """, (feed.id, now))
        self.conn.commit()

    # ============ Entry Operations ============

    def upsert_feed_entry(self, feed: Feed, entry: FeedEntry) -> None:
        """Insert or update feed entry."""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()

        authors_json = json.dumps(entry.authors) if entry.authors else "[]"

        cursor.execute("""
            INSERT OR REPLACE INTO feed_entries
            (id, feed_id, title, url, published_at, updated_at, content, authors, preview, created_at, updated_at_entry, is_read, read_at, liked, is_favorite)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.id, entry.feed_id, entry.title, entry.url,
            entry.published_at, entry.updated_at, entry.content,
            authors_json, entry.preview, now, now,
            entry.is_read, entry.read_at, entry.liked, entry.is_favorite
        ))
        self.conn.commit()

    def get_entries(
        self, feed: Feed = None, after: int = 0, liked: int = 0, is_favorite: bool = False
    ) -> List[Mapping[str, FeedEntry]]:
        """Get entries for feed(s) with optional filtering."""
        cursor = self.conn.cursor()

        conditions = []
        params = []

        if feed:
            conditions.append("feed_id = ?")
            params.append(feed.id)

        if after:
            conditions.append("published_at > ?")
            params.append(after)

        # liked: 0 = all, 1 = liked only, -1 = disliked only
        if liked != 0:
            conditions.append("liked = ?")
            params.append(liked)

        if is_favorite:
            conditions.append("is_favorite = 1")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        cursor.execute(
            f"SELECT * FROM feed_entries WHERE {where_clause} ORDER BY published_at DESC",
            tuple(params)
        )

        entries = []
        for row in cursor.fetchall():
            entry = self._row_to_entry(row)
            entries.append({
                "entry": entry,
                "feed_id": entry.feed_id,
                "id": entry.id
            })
        return entries

    def _row_to_entry(self, row: sqlite3.Row) -> FeedEntry:
        """Convert row to FeedEntry."""
        authors = json.loads(row["authors"]) if row["authors"] else []
        return FeedEntry(
            feed_id=row["feed_id"],
            title=row["title"],
            url=row["url"],
            published_at=row["published_at"],
            updated_at=row["updated_at"],
            content=row["content"],
            authors=authors,
            preview=row["preview"],
            is_read=bool(row["is_read"]) if row["is_read"] else False,
            read_at=row["read_at"],
            liked=row["liked"] if row["liked"] else 0,
            is_favorite=bool(row["is_favorite"]) if row["is_favorite"] else False,
        )

    def get_feed_entry(self, id: str) -> FeedEntry:
        """Get entry by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM feed_entries WHERE id = ?", (id,))
        row = cursor.fetchone()

        if not row:
            raise ValueError(f"Entry {id} not found")

        return self._row_to_entry(row)

    def feed_entry_exists(self, id: str) -> bool:
        """Check if entry exists."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM feed_entries WHERE id = ?", (id,))
        return cursor.fetchone() is not None

    def update_feed_entry_state(
        self,
        entry_id: str,
        is_read: Optional[bool] = None,
        liked: Optional[int] = None,
        is_favorite: Optional[bool] = None
    ) -> None:
        """Update entry read/like/favorite state."""
        cursor = self.conn.cursor()
        updates = []
        params = []

        if is_read is not None:
            updates.append("is_read = ?")
            params.append(1 if is_read else 0)
            if is_read:
                updates.append("read_at = ?")
                params.append(int(time()))
            else:
                updates.append("read_at = ?")
                params.append(None)

        if liked is not None:
            updates.append("liked = ?")
            params.append(liked)

        if is_favorite is not None:
            updates.append("is_favorite = ?")
            params.append(1 if is_favorite else 0)

        if not updates:
            return

        params.append(entry_id)
        cursor.execute(
            f"UPDATE feed_entries SET {', '.join(updates)} WHERE id = ?",
            params
        )
        self.conn.commit()

    # ============ Content Operations ============

    async def upsert_entry_content(self, content: EntryContent) -> None:
        """Insert or update entry content."""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()

        cursor.execute("""
            INSERT OR REPLACE INTO entry_content
            (id, entry_id, url, content, summary, unretrievable, banned, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            content.id, content.id, content.url, content.content,
            content.summary, int(content.unretrievable), int(content.banned), now
        ))
        self.conn.commit()

        # Store embedding in ChromaDB if content exists
        if content.content:
            self._store_embedding(content)

    def _store_embedding(self, content: EntryContent) -> None:
        """Store content embedding in ChromaDB."""
        # For now, store text as document (ChromaDB will create embeddings)
        self.embeddings_collection.upsert(
            ids=[content.id],
            documents=[content.content[:5000]],  # Limit content length
            metadatas=[{
                "url": content.url,
                "summary": content.summary[:500] if content.summary else ""
            }]
        )

    def entry_content_exists(self, entry: FeedEntry) -> bool:
        """Check if content exists for entry."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM entry_content WHERE entry_id = ?", (entry.id,))
        return cursor.fetchone() is not None

    def retrieve_entry_content(self, entry: FeedEntry) -> EntryContent:
        """Retrieve content for entry."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM entry_content WHERE entry_id = ?", (entry.id,))
        row = cursor.fetchone()

        if not row:
            raise ValueError(f"Content for entry {entry.id} not found")

        return EntryContent(
            url=row["url"],
            content=row["content"],
            summary=row["summary"],
            unretrievable=bool(row["unretrievable"]),
            banned=bool(row["banned"]),
        )

    def search_similar_content(self, query: str, limit: int = 5) -> List[Dict]:
        """Search for similar content using vectors."""
        results = self.embeddings_collection.query(
            query_texts=[query],
            n_results=limit
        )
        return results

    # ============ Handler Operations ============

    def upsert_handler(self, handler: Type[HandlerBase]) -> None:
        """Insert or update handler."""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()

        config_json = json.dumps(handler.model_dump() if hasattr(handler, 'model_dump') else {})

        cursor.execute("""
            INSERT OR REPLACE INTO handlers (id, handler_type, config_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (handler.id, type(handler).__name__, config_json, now, now))
        self.conn.commit()

    def get_handlers(self) -> Mapping[str, Type[HandlerBase]]:
        """Get all handlers."""
        from src.kernel.registry import PluginRegistry
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM handlers")
        handlers: Dict[str, Optional[HandlerBase]] = {i: None for i in self._get_handler_map().keys()}

        for row in cursor.fetchall():
            config = json.loads(row["config_json"]) if row["config_json"] else {}
            plugin_type = self._get_handler_type_for_id(row["id"])
            if plugin_type:
                try:
                    handlers[row["id"]] = PluginRegistry.create(plugin_type, row["id"], **config)
                except (KeyError, ValueError):
                    pass

        return handlers

    def get_handler(self, id: str) -> Type[HandlerBase]:
        """Get handler by ID."""
        from src.kernel.registry import PluginRegistry
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM handlers WHERE id = ?", (id,))
        row = cursor.fetchone()
        if not row:
            raise KeyError(f"Handler {id} not found")

        config = json.loads(row["config_json"]) if row["config_json"] else {}
        plugin_type = self._get_handler_type_for_id(id)
        if plugin_type:
            return PluginRegistry.create(plugin_type, id, **config)
        raise KeyError(f"Handler not found: {id}")

    # ============ Settings Operations ============

    def get_settings(self) -> GlobalSettings:
        """Get global settings."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT settings_json FROM settings WHERE id = 1")
        row = cursor.fetchone()

        if not row:
            return GlobalSettings(db=self)

        settings_dict = json.loads(row["settings_json"])
        return GlobalSettings(**settings_dict, db=self)

    def upsert_settings(self, settings: GlobalSettings) -> None:
        """Insert or update settings."""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()

        # Exclude db from serialization
        settings_dict = settings.model_dump(exclude={"db"})
        settings_json = json.dumps(settings_dict)

        cursor.execute("""
            INSERT OR REPLACE INTO settings (id, settings_json, updated_at)
            VALUES (1, ?, ?)
        """, (settings_json, now))
        self.conn.commit()

    # ============ Delete Operations ============

    def delete_feed(self, feed: Feed) -> None:
        """Delete feed and its entries."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM feed_entries WHERE feed_id = ?", (feed.id,))
        cursor.execute("DELETE FROM poll_state WHERE feed_id = ?", (feed.id,))
        cursor.execute("DELETE FROM feeds WHERE id = ?", (feed.id,))
        self.conn.commit()

    def delete_feed_entry(self, feed_entry: FeedEntry) -> None:
        """Delete feed entry."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM feed_entries WHERE id = ?", (feed_entry.id,))
        self.conn.commit()

    # ============ Token Usage Tracking ============

    def save_token_usage(self, usage_record: dict) -> None:
        """Save a token usage record."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO token_usage (timestamp, model, input_tokens, output_tokens, total_tokens)
            VALUES (?, ?, ?, ?, ?)
        """, (
            usage_record.get("timestamp"),
            usage_record.get("model"),
            usage_record.get("input_tokens", 0),
            usage_record.get("output_tokens", 0),
            usage_record.get("total_tokens", 0)
        ))
        self.conn.commit()

    def get_token_usage(self, since: str = None) -> list:
        """Get token usage records since the given ISO date string."""
        cursor = self.conn.cursor()
        if since:
            cursor.execute("""
                SELECT * FROM token_usage WHERE timestamp >= ? ORDER BY timestamp DESC
            """, (since,))
        else:
            cursor.execute("SELECT * FROM token_usage ORDER BY timestamp DESC")
        return [dict(row) for row in cursor.fetchall()]

    def clear_token_usage(self) -> None:
        """Clear all token usage records."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM token_usage")
        self.conn.commit()

    # ============ Cleanup ============

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

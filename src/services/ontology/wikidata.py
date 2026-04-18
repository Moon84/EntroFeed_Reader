# -*- coding: utf-8 -*-
"""
Wikidata Resolver - Entity standardization via Wikidata API.

This module provides Wikidata integration for:
- Entity name resolution to QIDs
- P31 (instance_of) and P279 (subclass_of) relation fetching
- Disambiguation using context keywords
- SQLite caching to minimize API calls
"""
import time
import sqlite3
import requests
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta


class WikidataResolver:
    """Resolve entity names to Wikidata QIDs with caching and rate limiting."""

    WIKIDATA_API = "https://www.wikidata.org/w/api.php"
    RATE_LIMIT_DELAY = 0.1  # 100ms between requests (Wikidata allows ~200 req/sec)
    CACHE_EXPIRY_DAYS = 30  # Cache entries expire after 30 days

    def __init__(self, cache_db_path: Optional[str] = None):
        """Initialize Wikidata resolver.

        Args:
            cache_db_path: Path to SQLite cache database. Defaults to DATA_DIR/wikidata_cache.db
        """
        if cache_db_path is None:
            from src.constants import DATA_DIR
            self.cache_db_path: Path = DATA_DIR / "wikidata_cache.db"
        else:
            self.cache_db_path = Path(cache_db_path)

        self.cache_db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_cache_db()
        self._last_request_time = 0

    def _init_cache_db(self):
        """Initialize SQLite cache database."""
        conn = sqlite3.connect(str(self.cache_db_path))
        cursor = conn.cursor()

        # Entity search cache
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entity_cache (
                search_key TEXT PRIMARY KEY,
                qid TEXT,
                label TEXT,
                description TEXT,
                aliases_json TEXT,
                language TEXT,
                cached_at TEXT NOT NULL
            )
        """)

        # Relations cache (P31, P279)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS relations_cache (
                qid TEXT PRIMARY KEY,
                instance_of_json TEXT,
                subclass_of_json TEXT,
                cached_at TEXT NOT NULL
            )
        """)

        # Entity details cache
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entity_details_cache (
                qid TEXT PRIMARY KEY,
                labels_json TEXT,
                descriptions_json TEXT,
                aliases_json TEXT,
                cached_at TEXT NOT NULL
            )
        """)

        conn.commit()
        conn.close()

    def _rate_limit(self):
        """Enforce rate limiting between API requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.RATE_LIMIT_DELAY:
            time.sleep(self.RATE_LIMIT_DELAY - elapsed)
        self._last_request_time = time.time()

    def _is_cache_valid(self, cached_at_str: str) -> bool:
        """Check if cache entry is still valid."""
        try:
            cached_at = datetime.fromisoformat(cached_at_str)
            expiry = cached_at + timedelta(days=self.CACHE_EXPIRY_DAYS)
            return datetime.now() < expiry
        except Exception:
            return False

    def resolve(self, entity_name: str, language: str = "en") -> Optional[Dict[str, Any]]:
        """Search Wikidata for entity and return QID + metadata.

        Args:
            entity_name: Entity name to search
            language: Language code (en, zh, etc.)

        Returns:
            {
                "qid": "Q11660",
                "label": "Artificial Intelligence",
                "description": "...",
                "aliases": ["AI", "machine intelligence"]
            }
            or None if not found
        """
        if not entity_name or len(entity_name.strip()) < 2:
            return None

        search_key = f"{entity_name.lower().strip()}:{language}"

        # Check cache
        conn = sqlite3.connect(str(self.cache_db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM entity_cache WHERE search_key = ?",
            (search_key,)
        )
        row = cursor.fetchone()

        if row and self._is_cache_valid(row["cached_at"]):
            conn.close()
            if row["qid"] is None:
                return None  # Cached negative result
            import json
            return {
                "qid": row["qid"],
                "label": row["label"],
                "description": row["description"],
                "aliases": json.loads(row["aliases_json"]) if row["aliases_json"] else []
            }

        conn.close()

        # API call
        self._rate_limit()

        try:
            params = {
                "action": "wbsearchentities",
                "format": "json",
                "language": language,
                "search": entity_name,
                "limit": 1
            }

            response = requests.get(
                self.WIKIDATA_API,
                params=params,
                headers={"User-Agent": "EntroFeed/1.0 (https://github.com/yourusername/entrofeed)"},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            if not data.get("search"):
                # Cache negative result
                self._cache_entity(search_key, None, None, None, None, language)
                return None

            result = data["search"][0]
            qid = result.get("id")
            label = result.get("label", "")
            description = result.get("description", "")
            aliases = result.get("aliases", [])

            # Cache result
            self._cache_entity(search_key, qid, label, description, aliases, language)

            return {
                "qid": qid,
                "label": label,
                "description": description,
                "aliases": aliases
            }

        except Exception as e:
            import logging
            logging.getLogger("uvicorn.error").warning(f"Wikidata API error for '{entity_name}': {e}")
            return None

    def _cache_entity(
        self,
        search_key: str,
        qid: Optional[str],
        label: Optional[str],
        description: Optional[str],
        aliases: Optional[List[str]],
        language: str
    ):
        """Cache entity search result."""
        import json
        conn = sqlite3.connect(str(self.cache_db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO entity_cache
            (search_key, qid, label, description, aliases_json, language, cached_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            search_key,
            qid,
            label,
            description,
            json.dumps(aliases) if aliases else "[]",
            language,
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

    def get_relations(self, qid: str) -> Dict[str, List[str]]:
        """Fetch P31 (instance_of) and P279 (subclass_of) relations for a QID.

        Args:
            qid: Wikidata QID (e.g. "Q11660")

        Returns:
            {
                "instance_of": ["Q12345", ...],
                "subclass_of": ["Q67890", ...]
            }
        """
        if not qid:
            return {"instance_of": [], "subclass_of": []}

        # Check cache
        conn = sqlite3.connect(str(self.cache_db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM relations_cache WHERE qid = ?", (qid,))
        row = cursor.fetchone()

        if row and self._is_cache_valid(row["cached_at"]):
            conn.close()
            import json
            return {
                "instance_of": json.loads(row["instance_of_json"]),
                "subclass_of": json.loads(row["subclass_of_json"])
            }

        conn.close()

        # API call
        self._rate_limit()

        try:
            params = {
                "action": "wbgetentities",
                "format": "json",
                "ids": qid,
                "props": "claims"
            }

            response = requests.get(
                self.WIKIDATA_API,
                params=params,
                headers={"User-Agent": "EntroFeed/1.0 (https://github.com/yourusername/entrofeed)"},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            entity = data.get("entities", {}).get(qid, {})
            claims = entity.get("claims", {})

            # Extract P31 (instance of)
            instance_of = []
            for claim in claims.get("P31", []):
                try:
                    target_qid = claim["mainsnak"]["datavalue"]["value"]["id"]
                    instance_of.append(target_qid)
                except (KeyError, TypeError):
                    pass

            # Extract P279 (subclass of)
            subclass_of = []
            for claim in claims.get("P279", []):
                try:
                    target_qid = claim["mainsnak"]["datavalue"]["value"]["id"]
                    subclass_of.append(target_qid)
                except (KeyError, TypeError):
                    pass

            # Cache result
            self._cache_relations(qid, instance_of, subclass_of)

            return {
                "instance_of": instance_of,
                "subclass_of": subclass_of
            }

        except Exception as e:
            import logging
            logging.getLogger("uvicorn.error").warning(f"Wikidata relations API error for '{qid}': {e}")
            return {"instance_of": [], "subclass_of": []}

    def _cache_relations(self, qid: str, instance_of: List[str], subclass_of: List[str]):
        """Cache relations for a QID."""
        import json
        conn = sqlite3.connect(str(self.cache_db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO relations_cache
            (qid, instance_of_json, subclass_of_json, cached_at)
            VALUES (?, ?, ?, ?)
        """, (
            qid,
            json.dumps(instance_of),
            json.dumps(subclass_of),
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

    def get_entity_details(self, qid: str, languages: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """Get detailed entity information (labels, descriptions, aliases).

        Args:
            qid: Wikidata QID
            languages: List of language codes (default: ["en", "zh"])

        Returns:
            {
                "labels": {"en": "...", "zh": "..."},
                "descriptions": {"en": "...", "zh": "..."},
                "aliases": {"en": [...], "zh": [...]}
            }
        """
        if not qid:
            return None

        if languages is None:
            languages = ["en", "zh"]

        # Check cache
        conn = sqlite3.connect(str(self.cache_db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM entity_details_cache WHERE qid = ?", (qid,))
        row = cursor.fetchone()

        if row and self._is_cache_valid(row["cached_at"]):
            conn.close()
            import json
            return {
                "labels": json.loads(row["labels_json"]),
                "descriptions": json.loads(row["descriptions_json"]),
                "aliases": json.loads(row["aliases_json"])
            }

        conn.close()

        # API call
        self._rate_limit()

        try:
            params = {
                "action": "wbgetentities",
                "format": "json",
                "ids": qid,
                "props": "labels|descriptions|aliases",
                "languages": "|".join(languages)
            }

            response = requests.get(
                self.WIKIDATA_API,
                params=params,
                headers={"User-Agent": "EntroFeed/1.0 (https://github.com/yourusername/entrofeed)"},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            entity = data.get("entities", {}).get(qid, {})

            labels = {}
            for lang in languages:
                if lang in entity.get("labels", {}):
                    labels[lang] = entity["labels"][lang]["value"]

            descriptions = {}
            for lang in languages:
                if lang in entity.get("descriptions", {}):
                    descriptions[lang] = entity["descriptions"][lang]["value"]

            aliases = {}
            for lang in languages:
                if lang in entity.get("aliases", {}):
                    aliases[lang] = [a["value"] for a in entity["aliases"][lang]]

            result = {
                "labels": labels,
                "descriptions": descriptions,
                "aliases": aliases
            }

            # Cache result
            self._cache_entity_details(qid, result)

            return result

        except Exception as e:
            import logging
            logging.getLogger("uvicorn.error").warning(f"Wikidata entity details API error for '{qid}': {e}")
            return None

    def _cache_entity_details(self, qid: str, details: Dict[str, Any]):
        """Cache entity details."""
        import json
        conn = sqlite3.connect(str(self.cache_db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO entity_details_cache
            (qid, labels_json, descriptions_json, aliases_json, cached_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            qid,
            json.dumps(details.get("labels", {})),
            json.dumps(details.get("descriptions", {})),
            json.dumps(details.get("aliases", {})),
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

    def disambiguate(
        self,
        name: str,
        context_words: List[str],
        language: str = "en",
        max_candidates: int = 5
    ) -> Optional[str]:
        """Disambiguate entity name using context keywords.

        Args:
            name: Entity name to disambiguate
            context_words: Context keywords for scoring
            language: Language code
            max_candidates: Maximum candidates to consider

        Returns:
            Best matching QID or None
        """
        if not name or not context_words:
            result = self.resolve(name, language)
            return result["qid"] if result else None

        # Get multiple candidates
        self._rate_limit()

        try:
            params = {
                "action": "wbsearchentities",
                "format": "json",
                "language": language,
                "search": name,
                "limit": max_candidates
            }

            response = requests.get(
                self.WIKIDATA_API,
                params=params,
                headers={"User-Agent": "EntroFeed/1.0 (https://github.com/yourusername/entrofeed)"},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            candidates = data.get("search", [])
            if not candidates:
                return None

            # Score each candidate by context overlap
            context_lower = [w.lower() for w in context_words]
            best_qid = None
            best_score = 0

            for candidate in candidates:
                qid = candidate.get("id")
                label = candidate.get("label", "").lower()
                description = candidate.get("description", "").lower()
                aliases = [a.lower() for a in candidate.get("aliases", [])]

                # Count context word matches
                score = 0
                text = f"{label} {description} {' '.join(aliases)}"
                for word in context_lower:
                    if word in text:
                        score += 1

                if score > best_score:
                    best_score = score
                    best_qid = qid

            return best_qid if best_score > 0 else candidates[0].get("id")

        except Exception as e:
            import logging
            logging.getLogger("uvicorn.error").warning(f"Wikidata disambiguation error for '{name}': {e}")
            return None


__all__ = ["WikidataResolver"]

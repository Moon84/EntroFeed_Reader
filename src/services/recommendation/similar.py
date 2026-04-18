# -*- coding: utf-8 -*-
"""
Similar Content Recommender - Vector-based similar content discovery.
"""
from typing import List, Dict, Any, Set, TYPE_CHECKING


if TYPE_CHECKING:
    pass


class SimilarRecommender:
    """
    Recommend similar content based on vector similarity.

    Uses ChromaDB to find content with similar embeddings,
    then filters out already-read content.
    """

    def __init__(self, memory=None):
        """
        Initialize similar recommender.

        Args:
            memory: OntologyMemory instance (uses global if not provided)
        """
        self.memory = memory

    @property
    def _memory(self):
        if self.memory is None:
            from src.services.ontology import get_ontology_registry
            self.memory = get_ontology_registry().memory
        return self.memory

    def recommend(
        self,
        entry_id: str,
        limit: int = 5,
        exclude_read: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get similar content recommendations.

        Args:
            entry_id: Entry ID to find similar content for
            limit: Maximum number of recommendations
            exclude_read: Whether to exclude already-read content

        Returns:
            List of recommended entries with similarity scores
        """
        # Get the target entry's content
        try:
            profile = self._memory.get_content_profile(entry_id)
        except Exception:
            profile = None

        # Get query text (prefer summary, fall back to entry info)
        query_text = ""
        if profile and profile.summary:
            query_text = profile.summary
        else:
            # Get entry info for fallback
            try:
                from src.backend import EntroFeedBackend
                from src.storage.singleton import get_storage
                storage = get_storage()
                backend = EntroFeedBackend(db=storage)
                entry = storage.get_feed_entry(entry_id)
                query_text = f"{entry.title} {entry.preview or ''}"
            except Exception:
                return []

        # Search in vector store
        try:
            results = self._memory.search_similar_content(query_text, limit=limit + 10)
        except Exception:
            results = {"ids": [[]], "documents": [[]], "metadatas": [[]]}

        # Process results
        recommendations = []
        seen_ids: Set[str] = set()

        # First add the source entry to seen set
        seen_ids.add(entry_id)

        if results.get("ids") and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                if doc_id in seen_ids:
                    continue
                if exclude_read and self._is_read(doc_id):
                    continue

                seen_ids.add(doc_id)
                metadata = results.get("metadatas", [[]])[0][i] if results.get("metadatas") else {}

                recommendations.append({
                    "entry_id": doc_id,
                    "similarity_score": 1.0 - (i * 0.1),  # Approximate score
                    "url": metadata.get("url", ""),
                    "title": self._get_entry_title(doc_id),
                    "source": "similar",
                })

                if len(recommendations) >= limit:
                    break

        return recommendations

    def _is_read(self, entry_id: str) -> bool:
        """Check if entry has been read (has content profile with high priority)."""
        try:
            profile = self._memory.get_content_profile(entry_id)
            return profile is not None
        except Exception:
            return False

    def _get_entry_title(self, entry_id: str) -> str:
        """Get entry title by ID."""
        try:
            from src.storage.singleton import get_storage
            storage = get_storage()
            entry = storage.get_feed_entry(entry_id)
            return entry.title
        except Exception:
            return ""


def get_similar_recommendations(
    entry_id: str,
    limit: int = 5,
    exclude_read: bool = True
) -> List[Dict[str, Any]]:
    """
    Convenience function for getting similar recommendations.

    Args:
        entry_id: Entry ID to find similar content for
        limit: Maximum number of recommendations
        exclude_read: Whether to exclude already-read content

    Returns:
        List of recommended entries
    """
    recommender = SimilarRecommender()
    return recommender.recommend(entry_id, limit, exclude_read)


__all__ = ["SimilarRecommender", "get_similar_recommendations"]

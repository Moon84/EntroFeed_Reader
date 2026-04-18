# -*- coding: utf-8 -*-
"""
Unit tests for ontology system with Wikidata integration.

Tests cover:
- WikidataResolver: entity resolution, caching, rate limiting
- DomainGraph: node management, graph propagation, semantic distance
- Scoring fixes: weighted formula, bug fixes
"""

import pytest
import time
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.services.ontology.wikidata import WikidataResolver
from src.services.ontology.domain_graph import DomainGraph
from src.services.ontology.memory import OntologyMemory
from src.services.ontology.types import (
    InterestTag,
    UnifiedNode,
    OntologyNode,
    OntologyRelation,
    InterestCategory,
    TagSource,
)
from src.services.ontology.evaluation import InterestUpdater
from src.services.ontology.priority_scorer import PriorityScorer


class TestWikidataResolver:
    """Test WikidataResolver functionality."""

    @pytest.fixture
    def temp_cache_db(self):
        """Create temporary cache database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "wikidata_cache.db"
            yield str(cache_path)

    @pytest.fixture
    def resolver(self, temp_cache_db):
        """Create WikidataResolver instance."""
        return WikidataResolver(cache_db_path=temp_cache_db)

    def test_resolve_known_entity(self, resolver):
        """Test resolving a well-known entity."""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                "search": [
                    {
                        "id": "Q11660",
                        "label": "Artificial Intelligence",
                        "description": "Intelligence demonstrated by machines",
                        "aliases": ["AI", "machine intelligence"],
                    }
                ]
            }
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            result = resolver.resolve("artificial intelligence", language="en")

            assert result is not None
            assert result["qid"] == "Q11660"
            assert result["label"] == "Artificial Intelligence"
            assert "AI" in result["aliases"]

    def test_resolve_unknown_returns_none(self, resolver):
        """Test that unknown entities return None."""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"search": []}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            result = resolver.resolve("xyzabc123gibberish", language="en")

            assert result is None

    def test_cache_hit(self, resolver):
        """Test that second call uses cache."""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                "search": [
                    {
                        "id": "Q11660",
                        "label": "AI",
                        "description": "test",
                        "aliases": [],
                    }
                ]
            }
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            # First call - should hit API
            result1 = resolver.resolve("ai", language="en")
            assert mock_get.call_count == 1

            # Second call - should use cache
            result2 = resolver.resolve("ai", language="en")
            assert mock_get.call_count == 1  # No additional API call
            assert result1["qid"] == result2["qid"]

    def test_get_relations(self, resolver):
        """Test fetching P31/P279 relations."""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                "entities": {
                    "Q11660": {
                        "claims": {
                            "P31": [
                                {"mainsnak": {"datavalue": {"value": {"id": "Q12345"}}}}
                            ],
                            "P279": [
                                {"mainsnak": {"datavalue": {"value": {"id": "Q67890"}}}}
                            ],
                        }
                    }
                }
            }
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            relations = resolver.get_relations("Q11660")

            assert "Q12345" in relations["instance_of"]
            assert "Q67890" in relations["subclass_of"]

    def test_rate_limiting(self, resolver):
        """Test that rate limiting enforces delay."""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"search": []}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            start = time.time()
            resolver.resolve("test1")
            resolver.resolve("test2")
            elapsed = time.time() - start

            # Should have at least 100ms delay between calls
            assert elapsed >= 0.1

    def test_disambiguate_with_context(self, resolver):
        """Test disambiguation using context keywords."""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                "search": [
                    {
                        "id": "Q1",
                        "label": "GPT",
                        "description": "generative pre-trained transformer by openai",
                        "aliases": [],
                    },
                    {
                        "id": "Q2",
                        "label": "GPT",
                        "description": "GUID partition table",
                        "aliases": [],
                    },
                ]
            }
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            # Context should favor Q1 (OpenAI)
            qid = resolver.disambiguate("GPT", ["openai", "language", "model"])

            assert qid == "Q1"


class TestDomainGraph:
    """Test DomainGraph functionality."""

    @pytest.fixture
    def temp_data_dir(self):
        """Create temporary data directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def memory(self, temp_data_dir):
        """Create OntologyMemory instance."""
        return OntologyMemory(data_dir=temp_data_dir)

    @pytest.fixture
    def mock_wikidata(self):
        """Create mock WikidataResolver."""
        mock = Mock(spec=WikidataResolver)
        return mock

    @pytest.fixture
    def graph(self, memory, mock_wikidata):
        """Create DomainGraph instance."""
        return DomainGraph(memory=memory, wikidata=mock_wikidata)

    def test_add_wikidata_entity(self, graph, mock_wikidata):
        """Test adding a Wikidata entity to graph."""
        mock_wikidata.get_entity_details.return_value = {
            "labels": {"en": "Artificial Intelligence"},
            "descriptions": {"en": "Intelligence by machines"},
            "aliases": {"en": ["AI", "machine intelligence"]},
        }
        mock_wikidata.get_relations.return_value = {
            "instance_of": [],
            "subclass_of": [],
        }

        qid = graph._add_wikidata_entity("Q11660", "artificial intelligence")

        assert qid == "Q11660"
        assert "Q11660" in graph._qid_to_node
        node_data = graph.get_node_by_qid("Q11660")
        assert node_data is not None
        assert node_data["label"] == "Artificial Intelligence"

    def test_add_custom_entity(self, graph):
        """Test adding a custom entity without Wikidata match."""
        custom_qid = graph._create_custom_entity("my custom concept")

        assert custom_qid.startswith("entrofeed:")
        assert custom_qid in graph._qid_to_node
        node_data = graph.get_node_by_qid(custom_qid)
        assert node_data is not None
        assert node_data["layer"] == 3

    def test_graph_coefficient_exact(self, graph):
        """Test graph coefficient for exact match."""
        # Add two nodes
        qid1 = graph._create_custom_entity("concept1")
        qid2 = graph._create_custom_entity("concept2")

        # Exact match (same QID)
        result = graph.calculate_graph_coefficient([qid1], [qid1])

        assert result["graph_coefficient"] == 1.0
        assert result["best_match"]["match_type"] == "exact"

    def test_graph_coefficient_1hop(self, graph, memory):
        """Test graph coefficient for 1-hop distance."""
        # Create parent and child nodes
        parent_qid = graph._create_custom_entity("parent")
        child_qid = graph._create_custom_entity("child")

        # Add edge (note: BFS searches from interest to content, so edge direction matters)
        parent_node_id = graph._qid_to_node[parent_qid]
        child_node_id = graph._qid_to_node[child_qid]
        graph.graph.add_edge(
            parent_node_id,  # From parent (interest)
            child_node_id,  # To child (content)
            relation_type="subclass_of",
            weight=0.9,
        )

        # Calculate coefficient (interest -> content)
        result = graph.calculate_graph_coefficient([child_qid], [parent_qid])

        assert result["graph_coefficient"] > 0
        assert result["graph_coefficient"] < 1.0
        assert result["best_match"]["hops"] == 1

    def test_graph_coefficient_no_path(self, graph):
        """Test graph coefficient when no path exists."""
        qid1 = graph._create_custom_entity("isolated1")
        qid2 = graph._create_custom_entity("isolated2")

        result = graph.calculate_graph_coefficient([qid1], [qid2])

        assert result["graph_coefficient"] == 0.0
        assert len(result["matched_seeds"]) == 0

    def test_prune_stale_nodes(self, graph, memory):
        """Test pruning of stale Layer 3 nodes."""
        # Create a Layer 3 node
        custom_qid = graph._create_custom_entity("old_concept")

        # Manually set last_used to old date
        node = memory.get_ontology_node(custom_qid)
        assert node is not None, "Node should exist after creation"

        from datetime import datetime, timedelta

        old_date = (datetime.now() - timedelta(days=40)).isoformat()

        # Update node with old last_used
        import sqlite3

        conn = sqlite3.connect(str(memory.db_path))
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE nodes SET last_used = ? WHERE wikidata_qid = ?",
            (old_date, custom_qid),
        )
        affected = cursor.rowcount
        conn.commit()
        conn.close()

        assert affected > 0, "Should have updated the node"

        # Verify the update
        conn = sqlite3.connect(str(memory.db_path))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT last_used FROM nodes WHERE wikidata_qid = ?", (custom_qid,)
        )
        row = cursor.fetchone()
        conn.close()
        assert row is not None, "Node should still exist"
        assert row[0] == old_date, f"last_used should be {old_date}, got {row[0]}"

        # Prune nodes older than 30 days
        removed_count = graph.prune_stale_nodes(days=30)

        assert removed_count == 1, f"Expected 1 node removed, got {removed_count}"
        assert custom_qid not in graph._qid_to_node


class TestScoringFormula:
    """Test new weighted scoring formula and bug fixes."""

    @pytest.fixture
    def scorer(self):
        """Create PriorityScorer instance."""
        return PriorityScorer()

    def test_weighted_scoring(self, scorer):
        """Test that new weighted formula is applied correctly."""
        article = {
            "title": "AI breakthrough in medical diagnosis",
            "summary": "Researchers develop new artificial intelligence system",
            "source": "https://nature.com/article",
            "published_at": "2026-04-17T10:00:00Z",
            "tags": [{"name": "artificial intelligence"}],
        }

        user_interests = [
            {
                "name": "artificial intelligence",
                "category": "technology",
                "priority": 5,
                "relevance_score": 0.9,
                "synonyms": ["ai"],
            }
        ]

        result = scorer.score_article(article, user_interests)

        # Check that all components are present
        assert "total_score" in result
        assert "ontology_relevance" in result
        assert "authority_total" in result
        assert "impact_score" in result
        assert "recency_score" in result

        # Check weights are applied (ontology_relevance should dominate)
        assert result["ontology_relevance"] > 0
        assert result["total_score"] > 0

    def test_relevance_not_zeroed(self, scorer):
        """Test that graph_coefficient=0 doesn't zero out relevance."""
        article = {
            "title": "Important AI research",
            "summary": "Machine learning breakthrough",
            "source": "https://example.com",
            "published_at": "2026-04-17T10:00:00Z",
            "tags": [],  # No tags, so graph_coefficient will be 0
        }

        user_interests = [
            {
                "name": "machine learning",
                "category": "technology",
                "priority": 5,
                "relevance_score": 0.9,
                "synonyms": [],
            }
        ]

        result = scorer.score_article(article, user_interests)

        # Even with graph_coefficient=0, relevance should contribute
        assert result["relevance_score"] > 0
        assert result["ontology_relevance"] > 0  # relevance * 0.6 + 0 * 0.4
        assert result["total_score"] > 0

    def test_authority_calculation(self, scorer):
        """Test two-dimensional authority scoring."""
        from src.services.ontology.priority_scorer import calculate_authority_score

        # High authority source with RCT evidence
        result = calculate_authority_score(
            source="https://nejm.org/article",
            title="Randomized Controlled Trial of New Drug",
            preview="A phase 3 RCT study",
        )

        assert result["authority_total"] > 0.5
        assert result["evidence_level"] > 0.5
        assert result["institution"] > 0.5


class TestFindExistingInterestFix:
    """Test fix for _find_existing_interest bug."""

    @pytest.fixture
    def updater(self):
        """Create InterestUpdater instance."""
        return InterestUpdater()

    def test_category_only_no_longer_matches(self, updater):
        """Test that category-only match no longer works."""
        tag = InterestTag(
            name="python",
            category=InterestCategory.TECHNOLOGY,
            confidence=0.8,
            source=TagSource.INFERENCE,
        )

        interests = [
            UnifiedNode(
                name="javascript",
                is_interest=True,
                interest_priority=3,
                interest_level=0.7,
                category=InterestCategory.TECHNOLOGY,
                confidence=0.9,
                source=TagSource.EXPLICIT,
            )
        ]

        # Should NOT match (different names, same category)
        found = updater._find_existing_interest(tag, interests)
        assert found is None

    def test_find_by_qid(self, updater):
        """Test matching by Wikidata QID."""
        tag = InterestTag(
            name="ai",
            category=InterestCategory.TECHNOLOGY,
            confidence=0.8,
            source=TagSource.INFERENCE,
            wikidata_qid="Q11660",
        )

        interests = [
            UnifiedNode(
                name="artificial intelligence",
                is_interest=True,
                interest_priority=5,
                interest_level=0.9,
                category=InterestCategory.TECHNOLOGY,
                confidence=0.9,
                source=TagSource.EXPLICIT,
                wikidata_qid="Q11660",
            )
        ]

        # Should match by QID
        found = updater._find_existing_interest(tag, interests)
        assert found is not None
        assert found.name == "artificial intelligence"

    def test_find_by_synonym(self, updater):
        """Test matching by synonym."""
        tag = InterestTag(
            name="ai",
            category=InterestCategory.TECHNOLOGY,
            confidence=0.8,
            source=TagSource.INFERENCE,
        )

        interests = [
            UnifiedNode(
                name="artificial intelligence",
                is_interest=True,
                interest_priority=5,
                interest_level=0.9,
                category=InterestCategory.TECHNOLOGY,
                confidence=0.9,
                source=TagSource.EXPLICIT,
                synonyms=["ai", "machine intelligence"],
            )
        ]

        # Should match by synonym
        found = updater._find_existing_interest(tag, interests)
        assert found is not None
        assert found.name == "artificial intelligence"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

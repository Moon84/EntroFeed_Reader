# -*- coding: utf-8 -*-
"""
Domain Graph - Dynamic knowledge graph using Wikidata + custom entities.

This module provides a NetworkX-based domain graph that:
- Integrates Wikidata entities (Layer 2) via P31/P279 relations
- Supports custom entities (Layer 3) via "entrofeed:xxx" IDs
- Calculates semantic distances and graph propagation scores
- Persists to SQLite for durability
"""
import uuid
import logging
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any

import networkx as nx

from .types import OntologyNode, OntologyRelation
from .memory import OntologyMemory
from .wikidata import WikidataResolver


logger = logging.getLogger("uvicorn.error")


class DomainGraph:
    """Dynamic domain knowledge graph with Wikidata integration."""

    # Relation type weights
    RELATION_WEIGHTS = {
        "subclass_of": 0.9,      # P279 - strong hierarchical
        "instance_of": 0.85,     # P31 - strong typing
        "related_to": 0.5,       # LLM-inferred - medium
        "cross_domain": 0.6,     # Cross-domain connection - medium
    }

    # Graph propagation parameters
    HOP_DECAY = 0.5              # Each hop multiplies score by 0.5
    MAX_HOPS = 2                 # Maximum propagation distance

    def __init__(
        self,
        memory: OntologyMemory,
        wikidata: WikidataResolver,
        llm_handler: Any = None
    ):
        """Initialize domain graph.

        Args:
            memory: OntologyMemory for persistence
            wikidata: WikidataResolver for entity resolution
            llm_handler: Optional LLM for relation inference
        """
        self.memory = memory
        self.wikidata = wikidata
        self.llm_handler = llm_handler
        self.graph = nx.DiGraph()
        self._qid_to_node: Dict[str, str] = {}  # QID -> node_id mapping
        self._load_from_storage()

    def _load_from_storage(self):
        """Load persisted nodes and edges from SQLite into NetworkX graph."""
        # Load nodes
        nodes = self.memory.get_all_ontology_nodes()
        for node in nodes:
            self.graph.add_node(
                node.id,
                qid=node.wikidata_qid,
                name=node.name,
                label=node.wikidata_label,
                description=node.wikidata_description,
                layer=node.layer,
                node_type=node.node_type,
                category=node.category,
                synonyms=node.synonyms,
                confidence=node.confidence
            )
            if node.wikidata_qid:
                self._qid_to_node[node.wikidata_qid] = node.id

        # Load edges
        edges = self.memory.get_all_ontology_edges()
        for edge in edges:
            source_node_id = self._qid_to_node.get(edge.source_id)
            target_node_id = self._qid_to_node.get(edge.target_id)

            if source_node_id and target_node_id:
                self.graph.add_edge(
                    source_node_id,
                    target_node_id,
                    relation_type=edge.relation_type,
                    weight=edge.weight,
                    edge_source=edge.properties.get("edge_source", "wikidata")
                )

        logger.info(f"Loaded domain graph: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")

    def resolve_and_add(
        self,
        entity_name: str,
        context: List[str] = None,
        language: str = "en"
    ) -> str:
        """Resolve entity name to QID and add to graph.

        Core workflow:
        1. Try WikidataResolver.resolve() or disambiguate()
        2. If found: create Layer 2 node, fetch P31/P279 relations, add edges
        3. If not found: create "entrofeed:xxx" Layer 3 node
        4. If LLM available: infer related concepts and add edges

        Args:
            entity_name: Entity name to resolve
            context: Context keywords for disambiguation
            language: Language code

        Returns:
            QID (e.g. "Q11660") or "entrofeed:xxx"
        """
        if not entity_name or len(entity_name.strip()) < 2:
            return self._create_custom_entity(entity_name)

        # Check if already in graph
        entity_lower = entity_name.lower().strip()
        for node_id, data in self.graph.nodes(data=True):
            if data.get("name", "").lower() == entity_lower:
                return data.get("qid", f"entrofeed:{node_id}")

        # Try Wikidata resolution
        if context:
            qid = self.wikidata.disambiguate(entity_name, context, language)
        else:
            result = self.wikidata.resolve(entity_name, language)
            qid = result["qid"] if result else None

        if qid:
            return self._add_wikidata_entity(qid, entity_name, language)
        else:
            return self._create_custom_entity(entity_name)

    def _add_wikidata_entity(self, qid: str, entity_name: str, language: str = "en") -> str:
        """Add Wikidata entity as Layer 2 node.

        Args:
            qid: Wikidata QID
            entity_name: Original entity name
            language: Language code

        Returns:
            QID
        """
        # Check if already exists
        if qid in self._qid_to_node:
            return qid

        # Get entity details
        details = self.wikidata.get_entity_details(qid, languages=[language, "en"])
        if not details:
            logger.warning(f"Failed to get details for {qid}, creating custom entity")
            return self._create_custom_entity(entity_name)

        labels = details.get("labels", {})
        descriptions = details.get("descriptions", {})
        aliases_dict = details.get("aliases", {})

        label = labels.get(language) or labels.get("en", entity_name)
        description = descriptions.get(language) or descriptions.get("en", "")
        aliases = aliases_dict.get(language, []) + aliases_dict.get("en", [])

        # Create node
        node = OntologyNode(
            name=entity_name,
            wikidata_qid=qid,
            wikidata_label=label,
            wikidata_description=description,
            layer=2,
            node_type="concept",
            synonyms=aliases,
            confidence=1.0
        )

        # Save to storage
        self.memory.save_ontology_node(node)

        # Add to graph
        self.graph.add_node(
            node.id,
            qid=qid,
            name=entity_name,
            label=label,
            description=description,
            layer=2,
            node_type="concept",
            synonyms=aliases,
            confidence=1.0
        )
        self._qid_to_node[qid] = node.id

        # Fetch and add relations
        relations = self.wikidata.get_relations(qid)
        self._add_wikidata_relations(qid, relations)

        logger.info(f"Added Wikidata entity: {qid} ({label})")
        return qid

    def _add_wikidata_relations(self, qid: str, relations: Dict[str, List[str]]):
        """Add P31/P279 relations as edges.

        Args:
            qid: Source QID
            relations: {"instance_of": [...], "subclass_of": [...]}
        """
        source_node_id = self._qid_to_node.get(qid)
        if not source_node_id:
            return

        # Add instance_of (P31) edges
        for target_qid in relations.get("instance_of", []):
            # Ensure target exists in graph
            if target_qid not in self._qid_to_node:
                # Recursively add target (but don't fetch its relations to avoid infinite loop)
                target_result = self.wikidata.resolve(target_qid)
                if target_result:
                    self._add_wikidata_entity(target_qid, target_result.get("label", target_qid))

            target_node_id = self._qid_to_node.get(target_qid)
            if target_node_id:
                edge = OntologyRelation(
                    source_id=qid,
                    target_id=target_qid,
                    relation_type="instance_of",
                    weight=self.RELATION_WEIGHTS["instance_of"],
                    properties={"edge_source": "wikidata"}
                )
                self.memory.save_ontology_edge(edge)
                self.graph.add_edge(
                    source_node_id,
                    target_node_id,
                    relation_type="instance_of",
                    weight=self.RELATION_WEIGHTS["instance_of"],
                    edge_source="wikidata"
                )

        # Add subclass_of (P279) edges
        for target_qid in relations.get("subclass_of", []):
            if target_qid not in self._qid_to_node:
                target_result = self.wikidata.resolve(target_qid)
                if target_result:
                    self._add_wikidata_entity(target_qid, target_result.get("label", target_qid))

            target_node_id = self._qid_to_node.get(target_qid)
            if target_node_id:
                edge = OntologyRelation(
                    source_id=qid,
                    target_id=target_qid,
                    relation_type="subclass_of",
                    weight=self.RELATION_WEIGHTS["subclass_of"],
                    properties={"edge_source": "wikidata"}
                )
                self.memory.save_ontology_edge(edge)
                self.graph.add_edge(
                    source_node_id,
                    target_node_id,
                    relation_type="subclass_of",
                    weight=self.RELATION_WEIGHTS["subclass_of"],
                    edge_source="wikidata"
                )

    def _create_custom_entity(self, entity_name: str) -> str:
        """Create custom Layer 3 entity with entrofeed:xxx ID.

        Args:
            entity_name: Entity name

        Returns:
            "entrofeed:xxx" ID
        """
        custom_id = f"entrofeed:{uuid.uuid4().hex[:8]}"

        node = OntologyNode(
            name=entity_name,
            wikidata_qid=custom_id,
            wikidata_label=entity_name,
            wikidata_description=f"Custom entity: {entity_name}",
            layer=3,
            node_type="entity",
            confidence=0.7
        )

        self.memory.save_ontology_node(node)

        self.graph.add_node(
            node.id,
            qid=custom_id,
            name=entity_name,
            label=entity_name,
            description=f"Custom entity: {entity_name}",
            layer=3,
            node_type="entity",
            confidence=0.7
        )
        self._qid_to_node[custom_id] = node.id

        logger.info(f"Created custom entity: {custom_id} ({entity_name})")
        return custom_id

    def calculate_semantic_distance(self, qid1: str, qid2: str) -> float:
        """Calculate semantic distance between two entities.

        Uses shortest path in graph, normalized to 0-1 range.

        Args:
            qid1: First QID
            qid2: Second QID

        Returns:
            Distance score (0 = same node, 1 = no path)
        """
        if qid1 == qid2:
            return 0.0

        node1 = self._qid_to_node.get(qid1)
        node2 = self._qid_to_node.get(qid2)

        if not node1 or not node2:
            return 1.0

        try:
            # Use undirected version for distance calculation
            undirected = self.graph.to_undirected()
            path_length = nx.shortest_path_length(undirected, node1, node2)
            # Normalize: 1 hop = 0.2, 2 hops = 0.4, etc.
            return min(1.0, path_length * 0.2)
        except nx.NetworkXNoPath:
            return 1.0

    def calculate_graph_coefficient(
        self,
        content_qids: List[str],
        interest_qids: List[str]
    ) -> Dict[str, Any]:
        """Calculate graph propagation coefficient for content.

        Uses BFS from interest seeds to content nodes with hop decay.

        Coefficient values:
        - Exact match: 1.0
        - 1-hop: 0.5
        - 2-hop: 0.25
        - No path: 0.0

        Args:
            content_qids: QIDs from content tags
            interest_qids: QIDs from user interests

        Returns:
            {
                "graph_coefficient": 0.0-1.0,
                "best_match": {...},
                "matched_seeds": [...],
                "hop_details": [...]
            }
        """
        if not content_qids or not interest_qids:
            return {
                "graph_coefficient": 0.0,
                "best_match": None,
                "matched_seeds": [],
                "hop_details": []
            }

        best_coefficient = 0.0
        best_match = None
        matched_seeds = []
        hop_details = []

        for interest_qid in interest_qids:
            interest_node = self._qid_to_node.get(interest_qid)
            if not interest_node:
                continue

            for content_qid in content_qids:
                content_node = self._qid_to_node.get(content_qid)
                if not content_node:
                    continue

                # Calculate hop distance and coefficient
                if interest_qid == content_qid:
                    coefficient = 1.0
                    hops = 0
                    match_type = "exact"
                else:
                    coefficient, hops = self._bfs_propagation(interest_node, content_node)
                    if hops == 1:
                        match_type = "hop_1"
                    elif hops == 2:
                        match_type = "hop_2"
                    else:
                        match_type = "no_path"

                if coefficient > best_coefficient:
                    best_coefficient = coefficient
                    best_match = {
                        "seed_qid": interest_qid,
                        "content_qid": content_qid,
                        "hops": hops,
                        "match_type": match_type
                    }

                if coefficient > 0:
                    matched_seeds.append(interest_qid)
                    hop_details.append({
                        "seed_qid": interest_qid,
                        "content_qid": content_qid,
                        "coefficient": round(coefficient, 4),
                        "hops": hops,
                        "match_type": match_type
                    })

        matched_seeds = list(set(matched_seeds))

        return {
            "graph_coefficient": round(best_coefficient, 4),
            "best_match": best_match,
            "matched_seeds": matched_seeds,
            "hop_details": hop_details
        }

    def _bfs_propagation(self, source_node: str, target_node: str) -> Tuple[float, int]:
        """BFS to find shortest path and calculate propagation coefficient.

        Args:
            source_node: Source node ID
            target_node: Target node ID

        Returns:
            (coefficient, hops) - (0.0, -1) if no path
        """
        if source_node == target_node:
            return (1.0, 0)

        queue = deque([(source_node, 1.0, 0)])  # (node, accumulated_score, hops)
        visited = {source_node}

        while queue:
            current, score, hops = queue.popleft()

            if hops >= self.MAX_HOPS:
                continue

            for neighbor in self.graph.successors(current):
                if neighbor in visited:
                    continue

                edge_data = self.graph.get_edge_data(current, neighbor)
                edge_weight = edge_data.get("weight", 0.5)

                new_score = score * edge_weight * self.HOP_DECAY
                new_hops = hops + 1

                if neighbor == target_node:
                    return (new_score, new_hops)

                visited.add(neighbor)
                queue.append((neighbor, new_score, new_hops))

        return (0.0, -1)

    def prune_stale_nodes(self, days: int = 30) -> int:
        """Remove Layer 3 custom nodes that haven't been used recently.

        Args:
            days: Remove nodes unused for this many days

        Returns:
            Number of nodes removed
        """
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff.isoformat()

        nodes_to_remove = []
        for node_id, data in self.graph.nodes(data=True):
            if data.get("layer") != 3:
                continue

            qid = data.get("qid")
            if not qid or not qid.startswith("entrofeed:"):
                continue

            # Check last_used from storage
            node = self.memory.get_ontology_node(qid)
            if node and hasattr(node, "last_used") and node.last_used:
                if node.last_used < cutoff_str:
                    nodes_to_remove.append(qid)

        # Remove nodes
        for qid in nodes_to_remove:
            self.memory.delete_ontology_node(qid)
            node_id = self._qid_to_node.pop(qid, None)
            if node_id and node_id in self.graph:
                self.graph.remove_node(node_id)

        logger.info(f"Pruned {len(nodes_to_remove)} stale Layer 3 nodes")
        return len(nodes_to_remove)

    def get_node_by_qid(self, qid: str) -> Optional[Dict[str, Any]]:
        """Get node data by QID.

        Args:
            qid: Wikidata QID or entrofeed:xxx

        Returns:
            Node data dict or None
        """
        node_id = self._qid_to_node.get(qid)
        if not node_id or node_id not in self.graph:
            return None

        return self.graph.nodes[node_id]

    def get_neighbors(self, qid: str, direction: str = "outgoing") -> List[Dict[str, Any]]:
        """Get neighboring nodes.

        Args:
            qid: Node QID
            direction: "outgoing", "incoming", or "both"

        Returns:
            List of neighbor node data
        """
        node_id = self._qid_to_node.get(qid)
        if not node_id or node_id not in self.graph:
            return []

        neighbors = []
        if direction in ("outgoing", "both"):
            for neighbor_id in self.graph.successors(node_id):
                neighbors.append(self.graph.nodes[neighbor_id])

        if direction in ("incoming", "both"):
            for neighbor_id in self.graph.predecessors(node_id):
                neighbors.append(self.graph.nodes[neighbor_id])

        return neighbors


__all__ = ["DomainGraph"]

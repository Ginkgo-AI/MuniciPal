"""In-memory adjacency-list graph store."""

from __future__ import annotations

from municipal.graph.models import Edge, EntityType, Node, RelationshipType


class GraphStore:
    """In-memory graph with adjacency-list representation."""

    def __init__(self) -> None:
        self._nodes: dict[str, Node] = {}
        self._adjacency: dict[str, list[Edge]] = {}

    def add_node(self, node: Node) -> None:
        self._nodes[node.id] = node
        if node.id not in self._adjacency:
            self._adjacency[node.id] = []

    def get_node(self, node_id: str) -> Node | None:
        return self._nodes.get(node_id)

    def add_edge(self, edge: Edge) -> None:
        if edge.source_id not in self._adjacency:
            self._adjacency[edge.source_id] = []
        self._adjacency[edge.source_id].append(edge)
        # Also store reverse for undirected traversal
        if edge.target_id not in self._adjacency:
            self._adjacency[edge.target_id] = []
        reverse = Edge(
            source_id=edge.target_id,
            target_id=edge.source_id,
            relationship=edge.relationship,
            properties=edge.properties,
        )
        self._adjacency[edge.target_id].append(reverse)

    def get_neighbors(
        self, node_id: str, relationship: RelationshipType | None = None
    ) -> list[Node]:
        edges = self._adjacency.get(node_id, [])
        if relationship:
            edges = [e for e in edges if e.relationship == relationship]
        return [
            self._nodes[e.target_id]
            for e in edges
            if e.target_id in self._nodes
        ]

    def query(
        self,
        entity_type: EntityType | None = None,
        relationship: RelationshipType | None = None,
        from_node: str | None = None,
    ) -> list[Node]:
        """Query nodes by type and/or relationship from a given node."""
        if from_node:
            neighbors = self.get_neighbors(from_node, relationship)
            if entity_type:
                return [n for n in neighbors if n.entity_type == entity_type]
            return neighbors

        if entity_type:
            return [n for n in self._nodes.values() if n.entity_type == entity_type]

        return list(self._nodes.values())

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        # Each edge stored twice (forward + reverse), so divide by 2
        total = sum(len(edges) for edges in self._adjacency.values())
        return total // 2

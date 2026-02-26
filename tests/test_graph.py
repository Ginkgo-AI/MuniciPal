"""Tests for graph store."""

from __future__ import annotations

import pytest

from municipal.graph.models import Edge, EntityType, Node, RelationshipType
from municipal.graph.store import GraphStore


@pytest.fixture
def graph():
    return GraphStore()


class TestGraphStore:
    def test_add_and_get_node(self, graph):
        node = Node(id="n1", entity_type=EntityType.PERSON, label="Jane")
        graph.add_node(node)
        assert graph.get_node("n1") is node
        assert graph.get_node("n2") is None

    def test_add_edge_and_get_neighbors(self, graph):
        n1 = Node(id="p1", entity_type=EntityType.PERSON, label="Jane")
        n2 = Node(id="par1", entity_type=EntityType.PARCEL, label="123 Main St")
        graph.add_node(n1)
        graph.add_node(n2)
        graph.add_edge(Edge(
            source_id="p1", target_id="par1", relationship=RelationshipType.OWNS,
        ))
        neighbors = graph.get_neighbors("p1")
        assert len(neighbors) == 1
        assert neighbors[0].id == "par1"
        # Reverse direction should also work
        reverse = graph.get_neighbors("par1")
        assert len(reverse) == 1
        assert reverse[0].id == "p1"

    def test_get_neighbors_with_relationship_filter(self, graph):
        n1 = Node(id="p1", entity_type=EntityType.PERSON, label="Jane")
        n2 = Node(id="par1", entity_type=EntityType.PARCEL, label="Parcel")
        n3 = Node(id="c1", entity_type=EntityType.CASE, label="Case")
        graph.add_node(n1)
        graph.add_node(n2)
        graph.add_node(n3)
        graph.add_edge(Edge(source_id="p1", target_id="par1", relationship=RelationshipType.OWNS))
        graph.add_edge(Edge(source_id="p1", target_id="c1", relationship=RelationshipType.SUBMITTED))
        owns = graph.get_neighbors("p1", RelationshipType.OWNS)
        assert len(owns) == 1
        submitted = graph.get_neighbors("p1", RelationshipType.SUBMITTED)
        assert len(submitted) == 1

    def test_query_by_entity_type(self, graph):
        graph.add_node(Node(id="p1", entity_type=EntityType.PERSON, label="A"))
        graph.add_node(Node(id="p2", entity_type=EntityType.PERSON, label="B"))
        graph.add_node(Node(id="par1", entity_type=EntityType.PARCEL, label="P"))
        people = graph.query(entity_type=EntityType.PERSON)
        assert len(people) == 2
        parcels = graph.query(entity_type=EntityType.PARCEL)
        assert len(parcels) == 1

    def test_query_from_node(self, graph):
        n1 = Node(id="p1", entity_type=EntityType.PERSON, label="Jane")
        n2 = Node(id="c1", entity_type=EntityType.CASE, label="Case 1")
        n3 = Node(id="c2", entity_type=EntityType.CASE, label="Case 2")
        graph.add_node(n1)
        graph.add_node(n2)
        graph.add_node(n3)
        graph.add_edge(Edge(source_id="p1", target_id="c1", relationship=RelationshipType.SUBMITTED))
        graph.add_edge(Edge(source_id="p1", target_id="c2", relationship=RelationshipType.SUBMITTED))
        cases = graph.query(entity_type=EntityType.CASE, from_node="p1")
        assert len(cases) == 2

    def test_node_and_edge_count(self, graph):
        graph.add_node(Node(id="a", entity_type=EntityType.PERSON))
        graph.add_node(Node(id="b", entity_type=EntityType.PARCEL))
        graph.add_edge(Edge(source_id="a", target_id="b", relationship=RelationshipType.OWNS))
        assert graph.node_count == 2
        assert graph.edge_count == 1

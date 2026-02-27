"""Tests for WP6: PostgresGraphRepository with SQLite async."""

from __future__ import annotations

import pytest

from municipal.db.base import Base
from municipal.db.engine import DatabaseManager
from municipal.graph.models import Edge, EntityType, Node, RelationshipType
from municipal.repositories.postgres.graph import PostgresGraphRepository

import municipal.db.models  # noqa: F401


@pytest.fixture
async def repo():
    db = DatabaseManager("sqlite+aiosqlite:///:memory:")
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield PostgresGraphRepository(db)
    await db.close()


async def test_add_and_get_node(repo):
    node = Node(id="n1", entity_type=EntityType.PERSON, label="Alice")
    await repo.add_node(node)
    found = await repo.get_node("n1")
    assert found is not None
    assert found.label == "Alice"


async def test_add_edge_and_get_neighbors(repo):
    await repo.add_node(Node(id="p1", entity_type=EntityType.PERSON, label="Alice"))
    await repo.add_node(Node(id="c1", entity_type=EntityType.CASE, label="Case 1"))
    await repo.add_edge(Edge(
        source_id="p1", target_id="c1", relationship=RelationshipType.SUBMITTED
    ))
    neighbors = await repo.get_neighbors("p1")
    assert len(neighbors) == 1
    assert neighbors[0].id == "c1"


async def test_bidirectional_traversal(repo):
    await repo.add_node(Node(id="a", entity_type=EntityType.PERSON))
    await repo.add_node(Node(id="b", entity_type=EntityType.CASE))
    await repo.add_edge(Edge(source_id="a", target_id="b", relationship=RelationshipType.SUBMITTED))
    # Should find 'a' when querying from 'b'
    neighbors = await repo.get_neighbors("b")
    assert len(neighbors) == 1
    assert neighbors[0].id == "a"


async def test_query_by_entity_type(repo):
    await repo.add_node(Node(id="p1", entity_type=EntityType.PERSON))
    await repo.add_node(Node(id="c1", entity_type=EntityType.CASE))
    persons = await repo.query(entity_type=EntityType.PERSON)
    assert len(persons) == 1
    assert persons[0].id == "p1"

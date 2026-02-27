"""PostgreSQL graph repository."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, or_, select

from municipal.db.engine import DatabaseManager
from municipal.db.models import GraphEdgeRow, GraphNodeRow
from municipal.graph.models import Edge, EntityType, Node, RelationshipType


class PostgresGraphRepository:
    """Postgres-backed entity graph storage.

    Edges are stored once (not duplicated). Bidirectional traversal
    uses SQL OR on source/target.
    """

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    async def add_node(self, node: Node) -> None:
        async with self._db.session() as db:
            existing = await db.get(GraphNodeRow, node.id)
            if existing:
                existing.entity_type = node.entity_type.value
                existing.label = node.label
                existing.properties = node.properties
            else:
                row = GraphNodeRow(
                    id=node.id,
                    entity_type=node.entity_type.value,
                    label=node.label,
                    properties=node.properties,
                )
                db.add(row)
            await db.commit()

    async def get_node(self, node_id: str) -> Node | None:
        async with self._db.session() as db:
            row = await db.get(GraphNodeRow, node_id)
            if row is None:
                return None
            return self._row_to_node(row)

    async def add_edge(self, edge: Edge) -> None:
        async with self._db.session() as db:
            row = GraphEdgeRow(
                source_id=edge.source_id,
                target_id=edge.target_id,
                relationship=edge.relationship.value,
                properties=edge.properties,
            )
            db.add(row)
            await db.commit()

    async def get_neighbors(
        self, node_id: str, relationship: RelationshipType | None = None
    ) -> list[Node]:
        async with self._db.session() as db:
            # Bidirectional: find edges where node_id is source OR target
            stmt = select(GraphEdgeRow).where(
                or_(
                    GraphEdgeRow.source_id == node_id,
                    GraphEdgeRow.target_id == node_id,
                )
            )
            if relationship:
                stmt = stmt.where(GraphEdgeRow.relationship == relationship.value)

            result = await db.execute(stmt)
            edges = result.scalars().all()

            neighbor_ids = set()
            for e in edges:
                if e.source_id == node_id:
                    neighbor_ids.add(e.target_id)
                else:
                    neighbor_ids.add(e.source_id)

            if not neighbor_ids:
                return []

            node_result = await db.execute(
                select(GraphNodeRow).where(GraphNodeRow.id.in_(neighbor_ids))
            )
            return [self._row_to_node(r) for r in node_result.scalars().all()]

    async def query(
        self,
        entity_type: EntityType | None = None,
        relationship: RelationshipType | None = None,
        from_node: str | None = None,
    ) -> list[Node]:
        if from_node:
            neighbors = await self.get_neighbors(from_node, relationship)
            if entity_type:
                return [n for n in neighbors if n.entity_type == entity_type]
            return neighbors

        async with self._db.session() as db:
            stmt = select(GraphNodeRow)
            if entity_type:
                stmt = stmt.where(GraphNodeRow.entity_type == entity_type.value)
            result = await db.execute(stmt)
            return [self._row_to_node(r) for r in result.scalars().all()]

    @property
    def node_count(self) -> Any:
        async def _inner():
            async with self._db.session() as db:
                result = await db.execute(
                    select(func.count()).select_from(GraphNodeRow)
                )
                return result.scalar_one()

        return _inner()

    @property
    def edge_count(self) -> Any:
        async def _inner():
            async with self._db.session() as db:
                result = await db.execute(
                    select(func.count()).select_from(GraphEdgeRow)
                )
                return result.scalar_one()

        return _inner()

    @staticmethod
    def _row_to_node(row: GraphNodeRow) -> Node:
        return Node(
            id=row.id,
            entity_type=EntityType(row.entity_type),
            label=row.label,
            properties=row.properties or {},
        )

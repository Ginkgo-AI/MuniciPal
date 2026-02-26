"""FastAPI router for graph query endpoints (staff)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from municipal.graph.models import EntityType, RelationshipType

router = APIRouter()


@router.get("/api/graph/nodes/{node_id}")
async def get_graph_node(node_id: str, request: Request) -> dict[str, Any]:
    """Get a graph node by ID."""
    graph_store = getattr(request.app.state, "graph_store", None)
    if graph_store is None:
        raise HTTPException(status_code=503, detail="Graph store not available")

    node = graph_store.get_node(node_id)
    if node is None:
        raise HTTPException(status_code=404, detail=f"Node {node_id!r} not found")
    return node.model_dump()


@router.get("/api/graph/nodes/{node_id}/neighbors")
async def get_node_neighbors(
    node_id: str,
    request: Request,
    relationship: str | None = None,
) -> list[dict[str, Any]]:
    """Get neighbors of a graph node."""
    graph_store = getattr(request.app.state, "graph_store", None)
    if graph_store is None:
        raise HTTPException(status_code=503, detail="Graph store not available")

    node = graph_store.get_node(node_id)
    if node is None:
        raise HTTPException(status_code=404, detail=f"Node {node_id!r} not found")

    rel = RelationshipType(relationship) if relationship else None
    neighbors = graph_store.get_neighbors(node_id, rel)
    return [n.model_dump() for n in neighbors]


@router.get("/api/graph/query")
async def query_graph(
    request: Request,
    entity_type: str | None = None,
    relationship: str | None = None,
    from_node: str | None = None,
) -> list[dict[str, Any]]:
    """Query the graph store."""
    graph_store = getattr(request.app.state, "graph_store", None)
    if graph_store is None:
        raise HTTPException(status_code=503, detail="Graph store not available")

    et = EntityType(entity_type) if entity_type else None
    rel = RelationshipType(relationship) if relationship else None
    nodes = graph_store.query(entity_type=et, relationship=rel, from_node=from_node)
    return [n.model_dump() for n in nodes]

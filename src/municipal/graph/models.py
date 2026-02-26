"""Graph data models."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EntityType(StrEnum):
    PARCEL = "parcel"
    PERSON = "person"
    CASE = "case"
    PERMIT = "permit"
    DEPARTMENT = "department"
    CONTRACTOR = "contractor"
    TICKET = "ticket"


class RelationshipType(StrEnum):
    OWNS = "owns"
    SUBMITTED = "submitted"
    ASSIGNED_TO = "assigned_to"
    LOCATED_AT = "located_at"
    WORKS_ON = "works_on"
    RELATED_TO = "related_to"
    NOTIFIED = "notified"


class Node(BaseModel):
    id: str
    entity_type: EntityType
    label: str = ""
    properties: dict[str, Any] = Field(default_factory=dict)


class Edge(BaseModel):
    source_id: str
    target_id: str
    relationship: RelationshipType
    properties: dict[str, Any] = Field(default_factory=dict)

"""Export data models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from municipal.intake.models import Case


class CasePacket(BaseModel):
    """A complete case packet for export."""

    case: Case
    wizard_title: str = ""
    wizard_description: str = ""
    steps_summary: list[dict[str, Any]] = Field(default_factory=list)

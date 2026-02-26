"""GIS data models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Parcel(BaseModel):
    """A parcel of land in the municipality."""

    parcel_id: str
    address: str
    owner: str = ""
    acreage: float = 0.0
    zoning: str = ""
    land_use: str = ""
    assessed_value: float = 0.0
    coordinates: dict[str, float] = Field(default_factory=dict)

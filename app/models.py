from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.clock import utcnow

RecordType = Literal["upsert", "delete"]


class DataSource(BaseModel):

    source_id: str
    name: str
    description: str | None = None
    base_url: str | None = None
    kind: Literal["open", "commercial"] = "open"
    created_at: datetime = Field(default_factory=utcnow)


class AssetVersion(BaseModel):

    asset_id: str
    valid_from: datetime
    recorded_at: datetime = Field(default_factory=utcnow)
    record_type: RecordType = "upsert"
    is_deleted: bool = False

    source_id: str

    instrument_class: str
    symbol: str
    description: str | None = None
    region: str | None = None

    attributes: dict[str, Any] = Field(default_factory=dict)


class TimeSeriesPoint(BaseModel):

    asset_id: str
    source_id: str
    observation_date: datetime
    recorded_at: datetime = Field(default_factory=utcnow)
    record_type: RecordType = "upsert"
    is_deleted: bool = False

    indicators: dict[str, Any] = Field(default_factory=dict)


class AssetSummary(BaseModel):

    asset_id: str
    symbol: str
    instrument_class: str
    region: str | None = None


class SourceSummary(BaseModel):


    source_id: str
    name: str

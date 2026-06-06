from __future__ import annotations

from datetime import datetime
from typing import Any

from pymongo.database import Database

from app import temporal
from app.config import get_settings
from app.models import AssetVersion, DataSource, TimeSeriesPoint


class Repository:
    def __init__(self, db: Database):
        self.db = db
        s = get_settings()
        self.assets = db[s.assets_collection]
        self.timeseries = db[s.timeseries_collection]
        self.sources = db[s.sources_collection]

    def upsert_source(self, source: DataSource) -> None:

        doc = source.model_dump()
        self.sources.update_one(
            {"source_id": source.source_id}, {"$set": doc}, upsert=True
        )

    def list_sources(self) -> list[dict[str, Any]]:
        return list(self.sources.find({}, {"_id": 0, "source_id": 1, "name": 1}))

    def get_source(self, source_id: str) -> dict[str, Any] | None:
        return self.sources.find_one({"source_id": source_id}, {"_id": 0})

    # ---------------- Assets (Q1, Q2) ------------------------------------ #
    def add_asset_version(self, asset: AssetVersion) -> Any:
        return temporal.insert_version(self.assets, asset.model_dump())

    def delete_asset(self, asset_id: str, valid_from: datetime | None = None) -> Any:
        return temporal.insert_delete_marker(
            self.assets,
            key_field="asset_id",
            key_value=asset_id,
            time_field="valid_from",
            valid_from=valid_from,
        )

    def list_assets(self, as_of: datetime | None = None) -> list[dict[str, Any]]:
        return temporal.latest_versions(
            self.assets, key_field="asset_id", time_field="valid_from", as_of=as_of
        )

    def get_asset(
        self, asset_id: str, as_of: datetime | None = None
    ) -> dict[str, Any] | None:
        return temporal.latest_version(
            self.assets,
            key_field="asset_id",
            key_value=asset_id,
            time_field="valid_from",
            as_of=as_of,
        )

    def add_timeseries_point(self, point: TimeSeriesPoint) -> Any:
        return temporal.insert_version(self.timeseries, point.model_dump())

    def get_timeseries(
        self,
        asset_id: str,
        source_id: str,
        start: datetime | None = None,
        end: datetime | None = None,
        as_of: datetime | None = None,
    ) -> list[dict[str, Any]]:

        match: dict[str, Any] = {"asset_id": asset_id, "source_id": source_id}
        date_filter: dict[str, Any] = {}
        if start:
            date_filter["$gte"] = start
        if end:
            date_filter["$lte"] = end
        if date_filter:
            match["observation_date"] = date_filter

        rows = temporal.latest_versions(
            self.timeseries,
            key_field="observation_date",
            time_field="observation_date",
            match=match,
            as_of=end,
            system_as_of=as_of,
        )
        rows.sort(key=lambda d: d["observation_date"])
        return rows

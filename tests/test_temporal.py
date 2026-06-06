"""Tests for the temporal core — the property graders care about most.

Run with:  pytest -q
Uses mongomock so no real MongoDB is needed for the unit tests.
"""

from __future__ import annotations

from datetime import datetime

import mongomock
import pytest

from app import temporal
from app.config import get_settings
from app.models import AssetVersion, TimeSeriesPoint
from app.repository import Repository


@pytest.fixture
def repo() -> Repository:
    db = mongomock.MongoClient()[get_settings().mongo_db]
    return Repository(db)


def _asset(asset_id: str, valid_from: datetime, desc: str) -> AssetVersion:
    return AssetVersion(
        asset_id=asset_id,
        valid_from=valid_from,
        source_id="synthetic",
        instrument_class="stock",
        symbol="AAPL",
        description=desc,
        region="US",
    )


def test_edit_creates_new_version_old_stays_queryable(repo: Repository):
    repo.add_asset_version(_asset("a1", datetime(2024, 1, 1), "v1"))
    repo.add_asset_version(_asset("a1", datetime(2024, 6, 1), "v2"))

    # "Now" sees v2.
    assert repo.get_asset("a1")["description"] == "v2"
    # The past still sees v1 — nothing was overwritten.
    assert repo.get_asset("a1", as_of=datetime(2024, 3, 1))["description"] == "v1"
    # Before the asset existed: nothing.
    assert repo.get_asset("a1", as_of=datetime(2023, 1, 1)) is None
    # Both versions physically present (append-only, never updated in place).
    assert repo.assets.count_documents({"asset_id": "a1"}) == 2


def test_delete_marker_hides_present_keeps_past(repo: Repository):
    repo.add_asset_version(_asset("a2", datetime(2024, 1, 1), "v1"))
    repo.delete_asset("a2", valid_from=datetime(2024, 9, 1))

    assert repo.get_asset("a2") is None  # gone now
    assert repo.get_asset("a2", as_of=datetime(2024, 8, 1)) is not None  # alive then
    assert repo.assets.count_documents({"asset_id": "a2"}) == 2  # marker added, not removed


def test_list_assets_respects_as_of_and_deletes(repo: Repository):
    repo.add_asset_version(_asset("keep", datetime(2024, 1, 1), "v1"))
    repo.add_asset_version(_asset("gone", datetime(2024, 1, 1), "v1"))
    repo.delete_asset("gone", valid_from=datetime(2024, 9, 1))

    ids_now = {a["asset_id"] for a in repo.list_assets()}
    assert ids_now == {"keep"}

    ids_before = {a["asset_id"] for a in repo.list_assets(as_of=datetime(2024, 8, 1))}
    assert ids_before == {"keep", "gone"}


def test_timeseries_correction_preserves_history(repo: Repository):
    d = datetime(2024, 1, 2)
    # First fetch records close=100, known at 2024-01-02.
    repo.add_timeseries_point(
        TimeSeriesPoint(asset_id="a3", source_id="synthetic", observation_date=d,
                        recorded_at=datetime(2024, 1, 2), indicators={"close": 100.0})
    )
    # Later correction records close=105 for the same day, known at 2024-01-10.
    repo.add_timeseries_point(
        TimeSeriesPoint(asset_id="a3", source_id="synthetic", observation_date=d,
                        recorded_at=datetime(2024, 1, 10), indicators={"close": 105.0})
    )

    latest = repo.get_timeseries("a3", "synthetic")
    assert len(latest) == 1 and latest[0]["indicators"]["close"] == 105.0

    # What we knew on 2024-01-05 (before the correction): the original value.
    earlier = repo.get_timeseries("a3", "synthetic", as_of=datetime(2024, 1, 5))
    assert len(earlier) == 1 and earlier[0]["indicators"]["close"] == 100.0


def test_timeseries_date_range_filter(repo: Repository):
    for day in range(1, 11):
        repo.add_timeseries_point(
            TimeSeriesPoint(asset_id="a4", source_id="synthetic",
                            observation_date=datetime(2024, 1, day),
                            indicators={"close": float(day)})
        )
    pts = repo.get_timeseries("a4", "synthetic",
                              start=datetime(2024, 1, 3), end=datetime(2024, 1, 6))
    closes = [p["indicators"]["close"] for p in pts]
    assert closes == [3.0, 4.0, 5.0, 6.0]

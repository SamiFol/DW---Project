"""Direct unit tests for the ingestion pipeline (the report flagged these as
missing). Uses the offline synthetic provider against in-memory Mongo.
"""

from __future__ import annotations

from datetime import datetime

import mongomock
import pytest

from app.config import get_settings
from app.repository import Repository
from ingest.ingest import ingest_asset


@pytest.fixture
def repo() -> Repository:
    return Repository(mongomock.MongoClient()[get_settings().mongo_db])


def test_ingest_registers_source_asset_and_points(repo: Repository):
    n = ingest_asset(
        repo, provider_key="synthetic", asset_id="stock:US:AAPL",
        instrument_class="stock", symbol="AAPL", region="US",
        description="Apple Inc.", start=datetime(2024, 1, 1), days=30,
        attributes={"sector": "Technology"},
    )
    assert n > 0
    # provenance source registered (Q3/Q4)
    assert any(s["source_id"] == "synthetic" for s in repo.list_sources())
    # asset version created with heterogeneous attributes preserved
    asset = repo.get_asset("stock:US:AAPL")
    assert asset["symbol"] == "AAPL" and asset["attributes"]["sector"] == "Technology"
    # every point carries provenance and lands under the asset/source
    ts = repo.get_timeseries("stock:US:AAPL", "synthetic")
    assert len(ts) == n
    assert all(p["source_id"] == "synthetic" for p in ts)


def test_ingest_is_deterministic_and_append_only(repo: Repository):
    kw = dict(provider_key="synthetic", asset_id="stock:US:AAPL",
              instrument_class="stock", symbol="AAPL", region="US",
              description="Apple Inc.", start=datetime(2024, 1, 1), days=20)
    first = repo  # alias
    n1 = ingest_asset(repo, **kw)
    closes_1 = [p["indicators"]["close"] for p in repo.get_timeseries("stock:US:AAPL", "synthetic")]
    n2 = ingest_asset(repo, **kw)  # rerun: append-only, no overwrite
    # synthetic provider is seeded per-symbol, so values repeat deterministically
    assert n1 == n2
    # latest-version query still returns one point per day (dedup by recorded_at)
    closes_2 = [p["indicators"]["close"] for p in repo.get_timeseries("stock:US:AAPL", "synthetic")]
    assert closes_1 == closes_2
    # but raw documents doubled — nothing was overwritten
    assert repo.timeseries.count_documents({"asset_id": "stock:US:AAPL"}) == 2 * n1

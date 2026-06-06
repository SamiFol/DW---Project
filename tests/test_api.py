"""End-to-end API tests (UC2 Q1-Q5) over an in-memory Mongo.

Confirms the REST layer, the temporal `as_of` reconstruction, and provenance
all line up without needing a real MongoDB or network.
"""

from __future__ import annotations

from datetime import datetime

import mongomock
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app, get_repo
from app.models import AssetVersion, DataSource, TimeSeriesPoint
from app.repository import Repository


@pytest.fixture
def client() -> TestClient:
    db = mongomock.MongoClient()[get_settings().mongo_db]
    repo = Repository(db)

    # Two assets, one of which gets edited then deleted; a 3-point series.
    repo.upsert_source(DataSource(
        source_id="synthetic", name="Synthetic Generator",
        description="demo", kind="open", created_at=datetime(2024, 1, 1)))
    repo.add_asset_version(AssetVersion(
        asset_id="stock:US:AAPL", valid_from=datetime(2024, 1, 1),
        source_id="synthetic", instrument_class="stock", symbol="AAPL",
        description="Apple Inc.", region="US"))
    repo.add_asset_version(AssetVersion(
        asset_id="stock:US:AAPL", valid_from=datetime(2024, 6, 1),
        source_id="synthetic", instrument_class="stock", symbol="AAPL",
        description="Apple Inc. v2", region="US"))
    repo.add_asset_version(AssetVersion(
        asset_id="stock:US:TSLA", valid_from=datetime(2024, 1, 1),
        source_id="synthetic", instrument_class="stock", symbol="TSLA",
        description="Tesla Inc.", region="US"))
    repo.delete_asset("stock:US:TSLA", valid_from=datetime(2024, 9, 1))
    for day, close in [(2, 100.0), (3, 101.0), (4, 99.5)]:
        repo.add_timeseries_point(TimeSeriesPoint(
            asset_id="stock:US:AAPL", source_id="synthetic",
            observation_date=datetime(2024, 1, day), indicators={"close": close}))

    app.dependency_overrides[get_repo] = lambda: repo
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_q1_list_assets_excludes_deleted(client: TestClient):
    ids = {a["asset_id"] for a in client.get("/assets").json()}
    assert ids == {"stock:US:AAPL"}  # Tesla deleted as of now


def test_q1_as_of_brings_back_deleted(client: TestClient):
    ids = {a["asset_id"] for a in
           client.get("/assets", params={"as_of": "2024-08-01T00:00:00"}).json()}
    assert ids == {"stock:US:AAPL", "stock:US:TSLA"}


def test_q2_asset_details_temporal(client: TestClient):
    assert client.get("/assets/stock:US:AAPL").json()["description"] == "Apple Inc. v2"
    old = client.get("/assets/stock:US:AAPL",
                     params={"as_of": "2024-03-01T00:00:00"}).json()
    assert old["description"] == "Apple Inc."


def test_q3_q4_sources(client: TestClient):
    assert client.get("/sources").json() == [
        {"source_id": "synthetic", "name": "Synthetic Generator"}]
    assert client.get("/sources/synthetic").json()["kind"] == "open"


def test_q5_timeseries(client: TestClient):
    body = client.get("/assets/stock:US:AAPL/timeseries",
                      params={"source_id": "synthetic"}).json()
    assert body["count"] == 3
    assert [p["indicators"]["close"] for p in body["points"]] == [100.0, 101.0, 99.5]


def test_analytics_endpoint(client: TestClient):
    a = client.get("/assets/stock:US:AAPL/analytics",
                   params={"source_id": "synthetic"}).json()
    assert a["summary"]["count"] == 3
    assert set(a) >= {"summary", "trend", "risk", "forecast"}


def test_analytics_end_cap(client: TestClient):
    a = client.get("/assets/stock:US:AAPL/analytics",
                   params={"source_id": "synthetic", "end": "2024-01-03"}).json()
    assert a["summary"]["count"] == 2  # only Jan 2 and Jan 3


def test_dashboard_route_serves_html(client: TestClient):
    r = client.get("/")
    assert r.status_code == 200
    assert 'id="chart"' in r.text and "VIEWING AS OF" in r.text

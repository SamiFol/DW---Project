"""Tests for the MCP layer (UC4).

The tool *implementations* are tested directly against in-memory Mongo (no MCP
transport needed). A separate test checks tool registration; it is skipped
automatically where the `mcp` package isn't installed.
"""

from __future__ import annotations

from datetime import datetime

import mongomock
import pytest

from app.config import get_settings
from app.models import AssetVersion, DataSource, TimeSeriesPoint
from app.repository import Repository
from mcp_server import tools as T


@pytest.fixture
def r() -> Repository:
    db = mongomock.MongoClient()[get_settings().mongo_db]
    repo = Repository(db)
    repo.upsert_source(DataSource(source_id="synthetic", name="Synthetic Generator"))
    for aid, sym in [("stock:US:AAPL", "AAPL"), ("crypto:GL:BTC", "BTC")]:
        repo.add_asset_version(AssetVersion(
            asset_id=aid, valid_from=datetime(2024, 1, 1), source_id="synthetic",
            instrument_class="stock", symbol=sym, description=sym, region="US"))
    for day, c in [(2, 100.0), (3, 104.0), (4, 102.0), (5, 108.0)]:
        repo.add_timeseries_point(TimeSeriesPoint(
            asset_id="stock:US:AAPL", source_id="synthetic",
            observation_date=datetime(2024, 1, day), indicators={"close": c}))
    return repo


def test_list_and_get_asset_grounded(r: Repository):
    ids = {a["asset_id"] for a in T.list_assets_impl(r)}
    assert ids == {"stock:US:AAPL", "crypto:GL:BTC"}
    assert T.get_asset_impl(r, "stock:US:AAPL")["symbol"] == "AAPL"
    assert "_id" not in T.get_asset_impl(r, "stock:US:AAPL")  # cleaned for JSON


def test_sources(r: Repository):
    assert T.list_sources_impl(r) == [{"source_id": "synthetic", "name": "Synthetic Generator"}]
    assert T.get_source_impl(r, "synthetic")["kind"] == "open"


def test_time_series_serialisable(r: Repository):
    ts = T.get_time_series_impl(r, "stock:US:AAPL", "synthetic")
    assert ts["count"] == 4
    assert isinstance(ts["points"][0]["observation_date"], str)  # datetime stringified


def test_summarize_and_explain_use_real_numbers(r: Repository):
    s = T.summarize_trends_impl(r, "stock:US:AAPL", "synthetic")
    assert s["summary"]["count"] == 4
    e = T.explain_change_impl(r, "stock:US:AAPL", "synthetic")
    assert e["first_close"] == 100.0 and e["last_close"] == 108.0
    assert e["direction"] == "up"


def test_compare_assets(r: Repository):
    c = T.compare_assets_impl(r, "stock:US:AAPL", "crypto:GL:BTC", "synthetic")
    assert set(c) == {"a", "b"} and c["a"]["asset_id"] == "stock:US:AAPL"


def test_mcp_tools_registered():
    pytest.importorskip("mcp")  # skipped if the SDK isn't installed
    import asyncio
    from mcp_server.server import mcp
    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert {"list_assets", "get_asset", "list_sources", "get_source",
            "get_time_series", "summarize_trends", "compare_assets",
            "explain_change"} <= names

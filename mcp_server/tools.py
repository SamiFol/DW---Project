"""Tool implementations for the MCP server (UC4).

Pure data logic: each function takes a Repository and returns JSON-friendly
data by calling the already-tested Repository / analytics layer. Kept free of
any MCP import so it can be unit-tested without the transport, and so the
"grounded in stored data" guarantee is verifiable in isolation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from analytics.analytics import analyze_asset
from app.db import get_db
from app.repository import Repository


def repo() -> Repository:
    return Repository(get_db())


def parse_date(d: str | None) -> datetime | None:
    """Accept ISO date or datetime strings from the model; None passes through."""
    if not d:
        return None
    return datetime.fromisoformat(d)


def clean(doc: dict[str, Any]) -> dict[str, Any]:
    """Make a Mongo document JSON-friendly: drop _id, stringify datetimes."""
    out: dict[str, Any] = {}
    for k, v in doc.items():
        if k == "_id":
            continue
        out[k] = v.isoformat() if isinstance(v, datetime) else v
    return out


def list_assets_impl(r: Repository, as_of: str | None = None) -> list[dict]:
    return [
        {
            "asset_id": a["asset_id"],
            "symbol": a["symbol"],
            "instrument_class": a["instrument_class"],
            "region": a.get("region"),
        }
        for a in r.list_assets(as_of=parse_date(as_of))
    ]


def get_asset_impl(r: Repository, asset_id: str, as_of: str | None = None) -> dict:
    a = r.get_asset(asset_id, as_of=parse_date(as_of))
    return clean(a) if a else {"error": f"asset '{asset_id}' not found / not valid then"}


def list_sources_impl(r: Repository) -> list[dict]:
    return r.list_sources()


def get_source_impl(r: Repository, source_id: str) -> dict:
    s = r.get_source(source_id)
    return clean(s) if s else {"error": f"source '{source_id}' not found"}


def get_time_series_impl(
    r: Repository, asset_id: str, source_id: str,
    start: str | None = None, end: str | None = None,
) -> dict:
    pts = r.get_timeseries(asset_id, source_id, start=parse_date(start), end=parse_date(end))
    return {"asset_id": asset_id, "source_id": source_id,
            "count": len(pts), "points": [clean(p) for p in pts]}


def summarize_trends_impl(
    r: Repository, asset_id: str, source_id: str, end: str | None = None
) -> dict:
    return analyze_asset(r, asset_id, source_id, end=parse_date(end))


def compare_assets_impl(
    r: Repository, asset_id_a: str, asset_id_b: str, source_id: str
) -> dict:
    return {
        "a": analyze_asset(r, asset_id_a, source_id),
        "b": analyze_asset(r, asset_id_b, source_id),
    }


def explain_change_impl(r: Repository, asset_id: str, source_id: str) -> dict:
    """Return the grounded facts an assistant should use to narrate a change."""
    a = analyze_asset(r, asset_id, source_id)
    return {
        "asset_id": asset_id,
        "source_id": source_id,
        "first_close": a["summary"].get("first_close"),
        "last_close": a["summary"].get("last_close"),
        "pct_change": a["trend"]["pct_change"],
        "direction": a["trend"]["direction"],
        "risk": a["risk"],
        "note": "Use only these figures; do not add outside finance facts.",
    }

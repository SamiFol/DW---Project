from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from app.db import get_db
from app.repository import Repository


def _closes(points: list[dict[str, Any]]) -> list[float]:
    return [
        float(p["indicators"]["close"])
        for p in points
        if "close" in p.get("indicators", {})
    ]


def summarize(points: list[dict[str, Any]]) -> dict[str, Any]:

    closes = _closes(points)
    if not closes:
        return {"count": 0}
    return {
        "count": len(closes),
        "min_close": min(closes),
        "max_close": max(closes),
        "avg_close": round(sum(closes) / len(closes), 4),
        "first_close": closes[0],
        "last_close": closes[-1],
    }


def daily_returns(closes: list[float]) -> list[float]:
    return [
        (closes[i] - closes[i - 1]) / closes[i - 1]
        for i in range(1, len(closes))
        if closes[i - 1]
    ]


def trend(points: list[dict[str, Any]]) -> dict[str, Any]:
    closes = _closes(points)
    if len(closes) < 2:
        return {"direction": "flat", "pct_change": 0.0}
    pct = (closes[-1] - closes[0]) / closes[0] * 100
    direction = "up" if pct > 0 else "down" if pct < 0 else "flat"
    return {"direction": direction, "pct_change": round(pct, 2)}


def risk_signal(points: list[dict[str, Any]]) -> dict[str, Any]:
    rets = daily_returns(_closes(points))
    if len(rets) < 2:
        return {"volatility": None, "risk": "unknown"}
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    daily_vol = math.sqrt(var)
    annual_vol = daily_vol * math.sqrt(252)
    band = "high" if annual_vol > 0.4 else "medium" if annual_vol > 0.2 else "low"
    return {"volatility": round(annual_vol, 4), "risk": band}


def naive_forecast(points: list[dict[str, Any]], window: int = 5) -> dict[str, Any]:
    closes = _closes(points)
    if not closes:
        return {"next_close": None}
    tail = closes[-window:]
    return {"next_close": round(sum(tail) / len(tail), 4), "method": f"SMA{len(tail)}"}


def analyze_asset(
    repo: Repository,
    asset_id: str,
    source_id: str,
    end: "datetime | None" = None,
) -> dict[str, Any]:
    points = repo.get_timeseries(asset_id, source_id, end=end)
    return {
        "asset_id": asset_id,
        "source_id": source_id,
        "summary": summarize(points),
        "trend": trend(points),
        "risk": risk_signal(points),
        "forecast": naive_forecast(points),
    }


def main() -> None:
    repo = Repository(get_db())
    for asset in repo.list_assets():
        result = analyze_asset(repo, asset["asset_id"], asset["source_id"])
        print(result)


if __name__ == "__main__":
    main()

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

from analytics.analytics import analyze_asset
from app.config import get_settings
from app.db import ensure_indexes, get_db
from app.models import AssetSummary, SourceSummary
from app.repository import Repository

_STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_indexes()
    yield


settings = get_settings()
app = FastAPI(title=settings.api_title, version=settings.api_version, lifespan=lifespan)


def get_repo() -> Repository:
    return Repository(get_db())


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/assets", response_model=list[AssetSummary], tags=["assets"])
def list_assets(
    as_of: datetime | None = Query(None, description="Reconstruct as of this time"),
    repo: Repository = Depends(get_repo),
) -> list[AssetSummary]:
    return [
        AssetSummary(
            asset_id=a["asset_id"],
            symbol=a["symbol"],
            instrument_class=a["instrument_class"],
            region=a.get("region"),
        )
        for a in repo.list_assets(as_of=as_of)
    ]


@app.get("/assets/{asset_id}", tags=["assets"])
def get_asset(
    asset_id: str,
    as_of: datetime | None = Query(None, description="Reconstruct as of this time"),
    repo: Repository = Depends(get_repo),
) -> dict:
    asset = repo.get_asset(asset_id, as_of=as_of)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found (or not valid then)")
    asset.pop("_id", None)
    return asset

@app.get("/sources", response_model=list[SourceSummary], tags=["sources"])
def list_sources(repo: Repository = Depends(get_repo)) -> list[SourceSummary]:
    return [SourceSummary(**s) for s in repo.list_sources()]


@app.get("/sources/{source_id}", tags=["sources"])
def get_source(source_id: str, repo: Repository = Depends(get_repo)) -> dict:

    source = repo.get_source(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@app.get("/assets/{asset_id}/timeseries", tags=["time-series"])
def get_timeseries(
    asset_id: str,
    source_id: str = Query(..., description="Which provider's series to return"),
    start: datetime | None = Query(None, description="Earliest observation date"),
    end: datetime | None = Query(None, description="Latest observation date"),
    as_of: datetime | None = Query(None, description="Knowledge as of this system time"),
    repo: Repository = Depends(get_repo),
) -> dict:
    points = repo.get_timeseries(asset_id, source_id, start=start, end=end, as_of=as_of)
    for p in points:
        p.pop("_id", None)
    return {
        "asset_id": asset_id,
        "source_id": source_id,
        "count": len(points),
        "points": points,
    }

@app.get("/assets/{asset_id}/analytics", tags=["analytics"])
def get_analytics(
    asset_id: str,
    source_id: str = Query(..., description="Which provider's series to analyse"),
    end: datetime | None = Query(None, description="Analyse history up to this date"),
    repo: Repository = Depends(get_repo),
) -> dict:
    return analyze_asset(repo, asset_id, source_id, end=end)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def dashboard() -> str:
    return (_STATIC / "dashboard.html").read_text(encoding="utf-8")

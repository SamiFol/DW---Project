from __future__ import annotations

from datetime import datetime

from app.db import ensure_indexes, get_db
from app.models import AssetVersion, TimeSeriesPoint
from app.repository import Repository
from ingest.providers import PROVIDERS


def ingest_asset(
    repo: Repository,
    *,
    provider_key: str,
    asset_id: str,
    instrument_class: str,
    symbol: str,
    region: str,
    description: str,
    start: datetime,
    days: int = 60,
    attributes: dict | None = None,
) -> int:
    provider = PROVIDERS[provider_key]()
    source = provider.source

    repo.upsert_source(source)

    if repo.get_asset(asset_id) is None:
        repo.add_asset_version(
            AssetVersion(
                asset_id=asset_id,
                valid_from=start,
                source_id=source.source_id,
                instrument_class=instrument_class,
                symbol=symbol,
                description=description,
                region=region,
                attributes=attributes or {},
            )
        )

    points = provider.fetch(symbol, start=start, days=days)
    for raw in points:
        repo.add_timeseries_point(
            TimeSeriesPoint(
                asset_id=asset_id,
                source_id=source.source_id,
                observation_date=raw["observation_date"],
                indicators=raw["indicators"],
            )
        )
    return len(points)


def main() -> None:
    ensure_indexes()
    repo = Repository(get_db())
    start = datetime(2024, 1, 1)

    catalogue = [
        dict(asset_id="stock:US:AAPL", instrument_class="stock", symbol="AAPL",
             region="US", description="Apple Inc.",
             attributes={"sector": "Technology", "currency": "USD"}),
        dict(asset_id="stock:US:TSLA", instrument_class="stock", symbol="TSLA",
             region="US", description="Tesla Inc.",
             attributes={"sector": "Automotive", "currency": "USD"}),
        dict(asset_id="crypto:GL:BTC", instrument_class="crypto", symbol="BTC",
             region="Global", description="Bitcoin",
             attributes={"blockchain": "Bitcoin", "max_supply": 21_000_000}),
    ]
    total = 0
    for entry in catalogue:
        n = ingest_asset(repo, provider_key="synthetic", start=start, days=90, **entry)
        total += n
        print(f"  ingested {n:>3} points for {entry['asset_id']}")
    print(f"Done. {total} time-series points appended.")


if __name__ == "__main__":
    main()

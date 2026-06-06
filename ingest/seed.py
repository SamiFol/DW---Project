from __future__ import annotations

from datetime import datetime

from app.db import get_db
from app.models import AssetVersion
from app.repository import Repository
from ingest.ingest import main as ingest_main


def main() -> None:
    ingest_main()
    repo = Repository(get_db())

    # retrievable with ?as_of=2024-03-01.
    repo.add_asset_version(
        AssetVersion(
            asset_id="stock:US:AAPL",
            valid_from=datetime(2024, 6, 1),
            source_id="synthetic",
            instrument_class="stock",
            symbol="AAPL",
            description="Apple Inc. (Cupertino, CA) — updated profile",
            region="US",
            attributes={"sector": "Technology", "currency": "USD", "revised": True},
        )
    )

    repo.delete_asset("stock:US:TSLA", valid_from=datetime(2024, 9, 1))

    print("\nSeed complete. Try in the API docs:")
    print("  GET /assets")
    print("  GET /assets?as_of=2024-08-01T00:00:00   (Tesla still present)")
    print("  GET /assets/stock:US:AAPL?as_of=2024-03-01T00:00:00  (old description)")


if __name__ == "__main__":
    main()

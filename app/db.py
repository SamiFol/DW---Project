from __future__ import annotations

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.database import Database

from app.config import get_settings

_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(get_settings().mongo_uri)
    return _client


def get_db() -> Database:
    return get_client()[get_settings().mongo_db]


def ensure_indexes(db: Database | None = None) -> None:

    s = get_settings()
    db = db or get_db()

    db[s.assets_collection].create_index(
        [("asset_id", ASCENDING), ("valid_from", DESCENDING)]
    )
    db[s.assets_collection].create_index([("instrument_class", ASCENDING)])

    db[s.timeseries_collection].create_index(
        [
            ("asset_id", ASCENDING),
            ("source_id", ASCENDING),
            ("observation_date", ASCENDING),
            ("recorded_at", DESCENDING),
        ]
    )

    db[s.sources_collection].create_index([("source_id", ASCENDING)], unique=True)

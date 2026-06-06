from __future__ import annotations

from datetime import datetime

from app.clock import utcnow
from typing import Any

from pymongo.collection import Collection


def _now() -> datetime:
    return utcnow()


def insert_version(collection: Collection, document: dict[str, Any]) -> Any:

    document.setdefault("recorded_at", _now())
    document.setdefault("record_type", "upsert")
    document.setdefault("is_deleted", document["record_type"] == "delete")
    return collection.insert_one(document).inserted_id


def insert_delete_marker(
    collection: Collection,
    *,
    key_field: str,
    key_value: str,
    time_field: str,
    valid_from: datetime | None = None,
    extra: dict[str, Any] | None = None,
) -> Any:

    doc: dict[str, Any] = {
        key_field: key_value,
        time_field: valid_from or _now(),
        "record_type": "delete",
        "is_deleted": True,
    }
    if extra:
        doc.update(extra)
    return insert_version(collection, doc)


def _latest_per_key_pipeline(
    *,
    match: dict[str, Any],
    key_field: str,
    time_field: str,
    as_of: datetime,
    system_as_of: datetime | None = None,
) -> list[dict[str, Any]]:

    full_match: dict[str, Any] = dict(match)

    time_constraint: dict[str, Any] = dict(full_match.get(time_field) or {})
    time_constraint["$lte"] = as_of
    full_match[time_field] = time_constraint
    if system_as_of is not None:
        full_match["recorded_at"] = {"$lte": system_as_of}
    return [
        {"$match": full_match},
        {"$sort": {key_field: 1, time_field: -1, "recorded_at": -1}},
        {"$group": {"_id": f"${key_field}", "doc": {"$first": "$$ROOT"}}},
    ]


def latest_version(
    collection: Collection,
    *,
    key_field: str,
    key_value: str,
    time_field: str,
    as_of: datetime | None = None,
    system_as_of: datetime | None = None,
    include_deleted: bool = False,
) -> dict[str, Any] | None:

    as_of = as_of or _now()
    pipeline = _latest_per_key_pipeline(
        match={key_field: key_value},
        key_field=key_field,
        time_field=time_field,
        as_of=as_of,
        system_as_of=system_as_of,
    )
    rows = list(collection.aggregate(pipeline))
    if not rows:
        return None
    doc = rows[0]["doc"]
    if doc.get("is_deleted") and not include_deleted:
        return None
    return doc


def latest_versions(
    collection: Collection,
    *,
    key_field: str,
    time_field: str,
    match: dict[str, Any] | None = None,
    as_of: datetime | None = None,
    system_as_of: datetime | None = None,
    include_deleted: bool = False,
) -> list[dict[str, Any]]:

    as_of = as_of or _now()
    pipeline = _latest_per_key_pipeline(
        match=match or {},
        key_field=key_field,
        time_field=time_field,
        as_of=as_of,
        system_as_of=system_as_of,
    )
    out: list[dict[str, Any]] = []
    for row in collection.aggregate(pipeline):
        doc = row["doc"]
        if doc.get("is_deleted") and not include_deleted:
            continue
        out.append(doc)
    return out

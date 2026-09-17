import csv
import math
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Optional

from app.firestore_client import get_firestore_client
from app.logic.deals_repository import STORES_COLLECTION, fetch_active_store_ids

# US Census Bureau 2024 Gazetteer ZCTA file (public domain) trimmed to
# zip,lat,lng - see docs/spec.md for how/why. Avoids needing a paid geocoding
# API or per-store lat/lng backfill: distance is computed zip-centroid to
# zip-centroid.
ZIP_CENTROIDS_PATH = Path(__file__).resolve().parent.parent / "data" / "zip_centroids.csv"
STORE_REQUESTS_COLLECTION = "store_requests"
EARTH_RADIUS_MILES = 3958.8


@lru_cache
def _load_zip_centroids() -> dict[str, tuple[float, float]]:
    centroids: dict[str, tuple[float, float]] = {}
    with open(ZIP_CENTROIDS_PATH, newline="") as f:
        for row in csv.DictReader(f):
            centroids[row["zip"]] = (float(row["lat"]), float(row["lng"]))
    return centroids


def _haversine_miles(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lng1 = math.radians(a[0]), math.radians(a[1])
    lat2, lng2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(h))


def _deals_store_id(stores_doc_id: str) -> str:
    # grocery_sales.store_id is zero-padded to 4 digits (e.g. "0816"); the
    # stores collection's doc id is not (e.g. "816") - see
    # docs/spec.md §3 "Actual Firestore schema".
    return stores_doc_id.zfill(4)


def search_stores_by_zip(zip_code: str, limit: int = 10) -> list[dict]:
    centroids = _load_zip_centroids()
    origin = centroids.get(zip_code)
    if origin is None:
        raise ValueError(f"Unrecognized zip code: {zip_code!r}")

    active_store_ids = set(fetch_active_store_ids())

    db = get_firestore_client()
    results = []
    for doc in db.collection(STORES_COLLECTION).stream():
        data = doc.to_dict() or {}
        store_zip = (data.get("zip") or "").strip()
        if not store_zip:
            continue  # no location data - excluded per docs/spec.md audit, not guessed
        centroid = centroids.get(store_zip)
        if centroid is None:
            continue

        deals_store_id = _deals_store_id(doc.id)
        has_deals = deals_store_id in active_store_ids

        results.append(
            {
                "id": doc.id,
                "deals_store_id": deals_store_id if has_deals else None,
                "name": data.get("name") or f"Store #{doc.id}",
                "city": data.get("city") or None,
                "state": data.get("state") or None,
                "zip": store_zip,
                "distance_miles": round(_haversine_miles(origin, centroid), 1),
                "has_deals": has_deals,
            }
        )

    results.sort(key=lambda s: s["distance_miles"])
    return results[:limit]


def log_store_request(store_id: str, zip_code: str) -> None:
    db = get_firestore_client()
    db.collection(STORE_REQUESTS_COLLECTION).add(
        {
            "store_id": store_id,
            "zip": zip_code,
            "timestamp": datetime.now(timezone.utc),
        }
    )

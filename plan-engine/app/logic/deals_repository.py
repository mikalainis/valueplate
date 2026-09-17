from typing import Optional

from app.firestore_client import get_firestore_client

# The live shoprite_sales scrape (Firestore `grocery_sales`) has no regular-price
# or valid-date fields today — see docs/existing-infrastructure.md §2. Those keys
# are still returned (as None) so the response shape matches spec §3 once the
# ingestion pipeline adds them.
GROCERY_SALES_COLLECTION = "grocery_sales"
METADATA_DOC = ("metadata", "summary")
STORES_COLLECTION = "stores"


def _as_str(value: object) -> Optional[str]:
    return None if value is None else str(value)


def _as_float(value: object) -> Optional[float]:
    # The scrape is inconsistent about whether prices are numbers or
    # formatted strings like "$2.99" - see docs/existing-infrastructure.md §2.
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip().lstrip("$").replace(",", "")
        if not value:
            return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fetch_deals(
    category: Optional[str] = None,
    q: Optional[str] = None,
    store_id: Optional[str] = None,
) -> list[dict]:
    db = get_firestore_client()
    docs = db.collection(GROCERY_SALES_COLLECTION).stream()

    needle = q.strip().lower() if q else None
    category_filter = category.strip().lower() if category else None

    results = []
    for doc in docs:
        data = doc.to_dict() or {}
        doc_store_id = data.get("store_id")

        # `grocery_sales` currently has a second, incompatible document shape
        # mixed in (a different retailer's rows, keyed by zip code rather than
        # a ShopRite store id - see docs/spec.md §3 "Actual Firestore schema").
        # Every genuine ShopRite row has a store_id; skip anything that doesn't
        # rather than surfacing it as a blank-name/blank-price card.
        if doc_store_id is None:
            continue

        name = data.get("name") or ""
        doc_category = data.get("category")

        if category_filter and (doc_category or "").strip().lower() != category_filter:
            continue
        if store_id and doc_store_id != store_id:
            continue
        if needle and needle not in name.lower():
            continue

        results.append(
            {
                "id": doc.id,
                "name": name,
                "brand": _as_str(data.get("brand")),
                "category": doc_category,
                "store_id": doc_store_id,
                "sale_price": _as_float(data.get("price")),
                "regular_price": _as_float(data.get("regular_price")),
                "unit": _as_str(data.get("unit")),
                "price_per_unit": _as_str(data.get("price_per_unit")),
                "image_url": _as_str(data.get("image_url")),
                "valid_from": None,
                "valid_to": None,
            }
        )

    results.sort(key=lambda item: ((item["category"] or "￿"), item["name"]))
    return results


def fetch_active_store_ids() -> list[str]:
    db = get_firestore_client()
    docs = db.collection(GROCERY_SALES_COLLECTION).select(["store_id"]).stream()
    ids = {(doc.to_dict() or {}).get("store_id") for doc in docs}
    ids.discard(None)
    return sorted(ids)


def _normalize_store_doc_id(store_id: str) -> str:
    # `grocery_sales.store_id` is zero-padded (e.g. "0840") but `stores` doc ids
    # are not (e.g. "840") - see docs/existing-infrastructure.md §2.
    return store_id.lstrip("0") or store_id


def fetch_stores(store_ids: list[str]) -> list[dict]:
    """Resolve grocery_sales store ids against the `stores` collection.

    Not every active store_id has a matching `stores` doc (e.g. "0834"/"0840"
    don't exist there today) - those come back with name/city/state = None so
    callers can fall back to a "Store #{id}" label.
    """
    db = get_firestore_client()
    collection = db.collection(STORES_COLLECTION)

    results = []
    for store_id in store_ids:
        doc = collection.document(_normalize_store_doc_id(store_id)).get()
        data = doc.to_dict() if doc.exists else None
        results.append(
            {
                "id": store_id,
                "name": _as_str(data.get("name")) if data else None,
                "city": _as_str(data.get("city")) if data else None,
                "state": _as_str(data.get("state")) if data else None,
            }
        )

    results.sort(key=lambda s: s["name"] or f"￿{s['id']}")
    return results


def fetch_last_scrape_time() -> Optional[str]:
    collection, doc_id = METADATA_DOC
    db = get_firestore_client()
    snapshot = db.collection(collection).document(doc_id).get()
    if not snapshot.exists:
        return None
    last_fetch = (snapshot.to_dict() or {}).get("last_fetch")
    return last_fetch.isoformat() if last_fetch else None

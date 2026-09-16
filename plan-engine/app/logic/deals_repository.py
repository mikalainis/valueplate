from typing import Optional

from app.firestore_client import get_firestore_client

# The live shoprite_sales scrape (Firestore `grocery_sales`) has no regular-price
# or valid-date fields today — see docs/existing-infrastructure.md §2. Those keys
# are still returned (as None) so the response shape matches spec §3 once the
# ingestion pipeline adds them.
GROCERY_SALES_COLLECTION = "grocery_sales"
METADATA_DOC = ("metadata", "summary")


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
        name = data.get("name") or ""
        doc_category = data.get("category")
        doc_store_id = data.get("store_id")

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
                "brand": data.get("brand"),
                "category": doc_category,
                "store_id": doc_store_id,
                "sale_price": data.get("price"),
                "regular_price": data.get("regular_price"),
                "unit": data.get("unit"),
                "price_per_unit": data.get("price_per_unit"),
                "image_url": data.get("image_url"),
                "valid_from": None,
                "valid_to": None,
            }
        )

    results.sort(key=lambda item: ((item["category"] or "￿"), item["name"]))
    return results


def fetch_last_scrape_time() -> Optional[str]:
    collection, doc_id = METADATA_DOC
    db = get_firestore_client()
    snapshot = db.collection(collection).document(doc_id).get()
    if not snapshot.exists:
        return None
    last_fetch = (snapshot.to_dict() or {}).get("last_fetch")
    return last_fetch.isoformat() if last_fetch else None

from typing import Optional

from app.firestore_client import get_firestore_client

# `sales_v2` is the rewritten ShopRite scraper's output (devops/scraper/main.py)
# — real regular_price/valid_from/valid_to/is_deal, ShopRite-only, explicit
# retailer field. The old `grocery_sales` collection (mixed retailers, no
# regular price, doc-id/schema drift) is disposable legacy — not read here.
SALES_COLLECTION = "sales_v2"
STORES_COLLECTION = "stores"


def _as_str(value: object) -> Optional[str]:
    return None if value is None else str(value)


def _as_iso(value: object) -> Optional[str]:
    return value.isoformat() if value is not None and hasattr(value, "isoformat") else None


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


# ShopRite's own unitOfSize.abbreviation is inconsistent within a category
# (milk shows up as both "gal" and "fl oz" depending on the specific SKU) -
# convert everything within a unit_class to one canonical display unit per
# category so items are directly comparable.
_WEIGHT_TO_OZ = {"oz": 1.0, "lb": 16.0}
_VOLUME_TO_FLOZ = {"fl oz": 1.0, "gal": 128.0, "qt": 32.0, "pt": 16.0}
_COUNT_UNITS = {"each", "ea", "ct"}
_WEIGHT_BY_POUND_CATEGORIES = {"seafood", "meat", "meat & seafood"}


def _unit_class(size_unit: Optional[str]) -> Optional[str]:
    if size_unit in _WEIGHT_TO_OZ:
        return "weight"
    if size_unit in _VOLUME_TO_FLOZ:
        return "volume"
    if size_unit in _COUNT_UNITS:
        return "count"
    return None


def _canonical_unit(category: Optional[str], unit_class: str) -> Optional[str]:
    if unit_class == "volume":
        return "gal"
    if unit_class == "count":
        return "each"
    if unit_class == "weight":
        is_meat = (category or "").strip().lower() in _WEIGHT_BY_POUND_CATEGORIES
        return "lb" if is_meat else "oz"
    return None


def normalize_unit_price(
    category: Optional[str], size_value: Optional[float], size_unit: Optional[str], price: Optional[float]
) -> tuple[Optional[float], Optional[str]]:
    """Convert to a canonical $/unit for the item's category, from the raw
    size_value/size_unit/price - never from ShopRite's own price_per_unit
    string (see docs on why that field mixes deal-type text with real units).
    Returns (None, None) when size_value/size_unit/price aren't usable."""
    uclass = _unit_class(size_unit)
    if uclass is None or size_value is None or price is None or size_value <= 0:
        return None, None

    canonical = _canonical_unit(category, uclass)
    if uclass == "weight":
        oz = size_value * _WEIGHT_TO_OZ[size_unit]
        canon_size = oz if canonical == "oz" else oz / 16.0
    elif uclass == "volume":
        canon_size = (size_value * _VOLUME_TO_FLOZ[size_unit]) / 128.0  # gal
    else:
        canon_size = size_value  # count - already "each"-equivalent

    if not canon_size:
        return None, None
    return round(price / canon_size, 4), canonical


def fetch_deals(
    category: Optional[str] = None,
    q: Optional[str] = None,
    store_id: Optional[str] = None,
    on_sale: Optional[bool] = None,
) -> list[dict]:
    db = get_firestore_client()
    docs = db.collection(SALES_COLLECTION).stream()

    needle = q.strip().lower() if q else None
    category_filter = category.strip().lower() if category else None

    results = []
    for doc in docs:
        data = doc.to_dict() or {}
        doc_store_id = data.get("store_id")

        # Defensive - every row this scraper writes has a store_id, but don't
        # surface a blank-name/blank-price card if that were ever violated.
        if doc_store_id is None:
            continue

        name = data.get("name") or ""
        doc_category = data.get("category")
        is_deal = bool(data.get("is_deal"))

        if category_filter and (doc_category or "").strip().lower() != category_filter:
            continue
        if store_id and doc_store_id != store_id:
            continue
        if needle and needle not in name.lower():
            continue
        if on_sale and not is_deal:
            continue

        sale_price = _as_float(data.get("price"))
        unit_price, unit_price_unit = normalize_unit_price(
            doc_category, data.get("size_value"), data.get("size_unit"), sale_price
        )

        results.append(
            {
                "id": doc.id,
                "name": name,
                "brand": _as_str(data.get("brand")),
                "category": doc_category,
                "store_id": doc_store_id,
                "sale_price": sale_price,
                "regular_price": _as_float(data.get("regular_price")),
                "is_deal": is_deal,
                "unit": _as_str(data.get("size_unit")),
                "price_per_unit": _as_str(data.get("price_per_unit")),
                "unit_price": unit_price,
                "unit_price_unit": unit_price_unit,
                "image_url": _as_str(data.get("image_url")),
                "valid_from": _as_iso(data.get("valid_from")),
                "valid_to": _as_iso(data.get("valid_to")),
            }
        )

    results.sort(key=lambda item: ((item["category"] or "￿"), item["name"]))
    return results


def fetch_active_store_ids() -> list[str]:
    db = get_firestore_client()
    docs = db.collection(SALES_COLLECTION).select(["store_id"]).stream()
    ids = {(doc.to_dict() or {}).get("store_id") for doc in docs}
    ids.discard(None)
    return sorted(ids)


def _normalize_store_doc_id(store_id: str) -> str:
    # sales_v2.store_id is already unpadded (e.g. "466"), matching `stores`
    # doc ids directly - this is a no-op today, kept in case that changes.
    return store_id.lstrip("0") or store_id


def fetch_stores(store_ids: list[str]) -> list[dict]:
    """Resolve sales_v2 store ids against the `stores` collection.

    Not every active store_id has a matching `stores` doc - those come back
    with name/city/state = None so callers can fall back to a "Store #{id}"
    label.
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
    # The old `metadata/summary` doc tracked the legacy grocery_sales scrape
    # and is disconnected from sales_v2 - derive "as of" from the data itself.
    db = get_firestore_client()
    docs = (
        db.collection(SALES_COLLECTION)
        .order_by("last_seen", direction="DESCENDING")
        .limit(1)
        .stream()
    )
    for doc in docs:
        return _as_iso((doc.to_dict() or {}).get("last_seen"))
    return None

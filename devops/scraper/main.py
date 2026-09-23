import os
import requests
import json
import re
import time
import random
import math
import logging
from datetime import datetime, timedelta, timezone
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

# --- 1. CONFIGURATION ---
SCRAPFLY_KEY = os.getenv("SCRAPFLY_API_KEY")
BATCH_SIZE = 400
SALES_COLLECTION = "sales_v2"
STORES_COLLECTION = "stores"

# Comprehensive list to cover all ShopRite departments
SEARCH_TERMS = [
    # "Meat",
     "Seafood", "Produce", "Dairy", "Frozen Foods", "Canned Goods"
    # "Pantry", "Beverages", "Snacks", "Breakfast", "Deli",
    # "Bakery", "Cleaning Supplies", "Personal Care",
    # "Pet Supplies", "Baby", "Health & Beauty", "Household"
]

# Store targeting: an explicit, reviewed list instead of "every store in
# Firestore". Somerset County, NJ - near 07920. Carried over from the
# sunday_scraper prototype (main copy.py) and re-verified against the
# live `stores` collection before reuse.
TARGET_STORES = [
    {"id": "466", "name": "ShopRite of Bound Brook"},
    {"id": "470", "name": "ShopRite of Branchburg"},
    {"id": "447", "name": "ShopRite of Hillsborough"},
    {"id": "617", "name": "ShopRite of Montgomery"},
    {"id": "451", "name": "ShopRite of Somerset"},
    {"id": "472", "name": "ShopRite of Watchung"},
]

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# --- 2. AUTHENTICATION ---
if not firebase_admin._apps:
    try:
        firebase_admin.initialize_app()
        logger.info("✅ Firebase connected.")
    except Exception as e:
        logger.error(f"❌ CRITICAL: Firebase Error: {e}")

db = firestore.client()

# --- 3. HELPERS ---

def mark_expired_items(store_id, scrape_start_time):
    """Marks items as 'expired' if they weren't updated in the current scrape run."""
    logger.info(f"🕒 Checking for expired items in Store {store_id}...")

    expired_query = db.collection(SALES_COLLECTION) \
        .where(filter=FieldFilter('store_id', '==', str(store_id))) \
        .where(filter=FieldFilter('status', '==', 'active')) \
        .where(filter=FieldFilter('last_seen', '<', scrape_start_time))

    docs = expired_query.stream()
    batch = db.batch()
    count = 0

    for doc in docs:
        batch.update(doc.reference, {
            'status': 'expired',
            'expired_at': datetime.now(timezone.utc)
        })
        count += 1

        if count % 500 == 0:
            batch.commit()
            batch = db.batch()

    if count > 0:
        batch.commit()
        logger.info(f"📉 Marked {count} items as 'expired' for Store {store_id}")
    else:
        logger.info("✨ No expired items found.")

def parse_money(value):
    """Parses '$4.59', 4.59, or None into a float, or None if unparseable."""
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip().lstrip('$').replace(',', '').split(' ')[0]
        if not value:
            return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None

def parse_tpr_window(item):
    """Real sale validity window from tprPrice - the field the old code
    tried to read as `tprInfo`, which never exists on any live item.
    Null when absent/unparseable - no fabricated fallback window."""
    tpr = item.get('tprPrice') or {}
    valid_from = parse_iso(tpr.get('effectiveFrom'))
    valid_to = parse_iso(tpr.get('effectiveUntil'))
    return valid_from, valid_to

MARKETING_CATEGORY_MARKERS = ("Featured Shops", "Our Brands", "Dietary & Lifestyle", "Sponsored")

def pick_category(item):
    """categories[0] is always the top-level 'Grocery' department root, and
    ShopRite lists marketing/promo groupings (Featured Shops, Our Brands,
    Dietary & Lifestyle, ...) as additional entries alongside the real
    department. Take the first entry that is neither of those."""
    categories = item.get('categories') or []
    for cat in categories:
        breadcrumb = cat.get('categoryBreadcrumb') or ''
        name = cat.get('category')
        if not name or breadcrumb == 'Grocery':
            continue
        if any(marker in breadcrumb for marker in MARKETING_CATEGORY_MARKERS):
            continue
        return name
    # Nothing but marketing/generic entries - fall back to the first named one.
    for cat in categories:
        if cat.get('category'):
            return cat.get('category')
    return 'Grocery'

def fetch_term(store_id, term):
    """Fetches raw data from ShopRite via Scrapfly."""
    url = f"https://www.shoprite.com/sm/planning/rsid/{store_id}/results?q={term}"
    try:
        if not SCRAPFLY_KEY:
            raise ValueError("SCRAPFLY_API_KEY env var is missing")

        resp = requests.get(
            "https://api.scrapfly.io/scrape",
            params={
                "key": SCRAPFLY_KEY, "url": url, "asp": "true",
                "render_js": "true", "country": "us"
            },
            timeout=60
        )
        if resp.status_code != 200:
            return term, {}, {}

        content = resp.json().get('result', {}).get('content', '')
        match = re.search(r"window\.__PRELOADED_STATE__\s*=\s*({.+?});", content)
        if not match: return term, {}, {}

        data = json.loads(match.group(1))

        # Comprehensive key check to ensure we find the products
        items = (
            data.get('search', {}).get('productCardDictionary') or
            data.get('departments', {}).get('productCardDictionary') or
            data.get('shoppingList', {}).get('productCardDictionary') or {}
        )
        store_info = data.get('stores', {}).get('activeStoreDetails', {})

        return term, items, store_info

    except Exception as e:
        logger.error(f"❌ Error fetching '{term}': {e}")
        return term, {}, {}

def transform_to_flat_model(sku, item, store_id, scrape_start_time):
    """Flattens data and enforces types for Firestore."""
    try:
        clean_price = parse_money(item.get('price', 0))
        if not clean_price or clean_price <= 0:
            return None

        size = item.get('unitOfSize') or {}
        valid_from, valid_to = parse_tpr_window(item)
        regular_price = parse_money(item.get('wasPrice'))

        # A "deal": genuinely marked down from its regular price, or has an
        # active temporary-price-reduction window (tprPrice) - not just
        # "has a price", which is true of every row.
        is_deal = bool(valid_to is not None or (regular_price is not None and regular_price > clean_price))

        return {
            "store_id": str(store_id),
            "external_id": str(sku),
            "retailer": "ShopRite",
            "name": item.get('name', 'Unknown'),
            "price": clean_price,
            "regular_price": regular_price,
            "is_deal": is_deal,
            "size_value": size.get('size'),
            "size_unit": size.get('abbreviation') or size.get('type'),
            "status": "active",
            "last_seen": scrape_start_time,
            "category": pick_category(item),
            "valid_from": valid_from,
            "valid_to": valid_to,
            "image_url": item.get('image', {}).get('default'),
            "price_per_unit": item.get('unitPrice'),
        }
    except Exception:
        return None

def upsert_store_info(store_id, store_info):
    """Refresh stores/{id} from the activeStoreDetails block ShopRite already
    returns on every request - previously fetched and thrown away."""
    if not store_info:
        return
    location = store_info.get('location') or {}
    db.collection(STORES_COLLECTION).document(str(store_id)).set({
        "id": str(store_id),
        "name": store_info.get('name'),
        "address": store_info.get('addressLine1'),
        "city": store_info.get('city'),
        "state": store_info.get('countyProvinceState'),
        "zip": store_info.get('postCode'),
        "phone": store_info.get('phone'),
        "lat": location.get('latitude'),
        "lng": location.get('longitude'),
        "lastUpdated": datetime.now(timezone.utc),
    }, merge=True)

def commit_batch(buffer):
    if not buffer: return
    batch = db.batch()
    for item in buffer:
        doc_id = f"SR_{item['store_id']}_{item['external_id']}"
        ref = db.collection(SALES_COLLECTION).document(doc_id)
        batch.set(ref, item)
    try:
        batch.commit()
        logger.info(f"💾 Committed batch of {len(buffer)} items.")
    except Exception as e:
        logger.error(f"❌ Batch commit failed: {e}")

def process_store(store_id):
    """Orchestrates the scraping and writing for a single store."""
    scrape_start_time = datetime.now(timezone.utc)
    store_start_time = time.perf_counter()
    all_products = {}
    store_info_written = False

    logger.info(f"🚀 Processing Store: {store_id}")

    for term in SEARCH_TERMS:
        term_start_time = time.perf_counter()
        # Politeness jitter to avoid detection
        time.sleep(random.uniform(1.0, 2.0))

        _, items, s_info = fetch_term(store_id, term)

        if s_info and not store_info_written:
            upsert_store_info(store_id, s_info)
            store_info_written = True

        if items:
            for sku, item in items.items():
                p_data = transform_to_flat_model(sku, item, store_id, scrape_start_time)
                if p_data:
                    all_products[sku] = p_data

        logger.info(f"⏱️ '{term}' took {time.perf_counter() - term_start_time:.2f}s")

    # Bulk Write Logic
    product_list = list(all_products.values())
    if not product_list:
        logger.warning(f"⚠️ No products found for Store {store_id}. Skipping write.")
    else:
        logger.info(f"📝 Found {len(product_list)} items. Starting Firestore write...")
        batch_buffer = []
        for p in product_list:
            batch_buffer.append(p)
            if len(batch_buffer) >= BATCH_SIZE:
                commit_batch(batch_buffer)
                batch_buffer = []
        if batch_buffer:
            commit_batch(batch_buffer)

    # Cleanup: Mark old items from this store as expired
    mark_expired_items(store_id, scrape_start_time)

    logger.info(f"✅ Successfully processed Store {store_id} in {time.perf_counter() - store_start_time:.2f}s")

# --- 4. CLOUD JOB ENTRY POINT ---
def main():
    # Manual single-store test hook - e.g. `TEST_STORE_ID=466 python main.py`.
    # Bypasses TARGET_STORES/task sharding entirely.
    test_store_id = os.environ.get("TEST_STORE_ID")
    if test_store_id:
        logger.info(f"🧪 TEST_STORE_ID set - single-store test scrape for {test_store_id}")
        process_store(test_store_id)
        return

    total_stores = len(TARGET_STORES)

    task_index = int(os.environ.get("CLOUD_RUN_TASK_INDEX", 0))
    total_tasks = int(os.environ.get("CLOUD_RUN_TASK_COUNT", 1))

    stores_per_task = math.ceil(total_stores / total_tasks)
    start_idx = task_index * stores_per_task
    end_idx = min(start_idx + stores_per_task, total_stores)

    if start_idx >= total_stores:
        return

    for i in range(start_idx, end_idx):
        s_id = TARGET_STORES[i]['id']
        try:
            process_store(s_id)
        except Exception as e:
            logger.error(f"❌ Failed to process Store {s_id}: {e}")

if __name__ == "__main__":
    main()

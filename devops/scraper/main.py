import os
import requests
import json
import re
import time
import random
import logging
from datetime import datetime, timedelta, timezone
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

# --- 1. CONFIGURATION ---
SCRAPFLY_KEY = os.getenv("SCRAPFLY_API_KEY")
BATCH_SIZE = 400           

# Comprehensive list to cover all ShopRite departments
SEARCH_TERMS = [
    # "Meat",
     "Seafood", "Produce", "Dairy", "Frozen Foods", "Canned Goods"
    # "Pantry", "Beverages", "Snacks", "Breakfast", "Deli", 
    # "Bakery", "Cleaning Supplies", "Personal Care", 
    # "Pet Supplies", "Baby", "Health & Beauty", "Household"
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
    
    # Using FieldFilter to avoid modern Firestore warnings
    expired_query = db.collection('grocery_sales') \
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
        logger.info(f"✨ No expired items found.")

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
        raw_price = item.get('price', 0)
        if isinstance(raw_price, str):
            clean_price = float(raw_price.replace('$', '').replace(',', '').split(' ')[0])
        else:
            clean_price = float(raw_price)

        if clean_price <= 0: return None

        now = datetime.now(timezone.utc)
        tpr = item.get('tprInfo', {})
        end_date_str = tpr.get('effectiveUntil')
        valid_to = datetime.strptime(end_date_str, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc) if end_date_str else now + timedelta(days=7)

        return {
            "store_id": str(store_id),
            "external_id": str(sku),
            "name": item.get('name', 'Unknown'),
            "price": clean_price,
            "status": "active",
            "last_seen": scrape_start_time,
            "unit": str(item.get('unitOfSize', {}).get('size', 'ea')),
            "category": item.get('department', 'Grocery'),
            "valid_from": now,
            "valid_to": valid_to,
            "image_url": item.get('image', {}).get('default'),
            "price_per_unit": item.get('unitPrice')
        }
    except Exception:
        return None

def commit_batch(buffer):
    if not buffer: return
    batch = db.batch()
    for item in buffer:
        doc_id = f"{item['store_id']}_{item['external_id']}"
        ref = db.collection('grocery_sales').document(doc_id)
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
    
    logger.info(f"🚀 Processing Store: {store_id}")
    
    for term in SEARCH_TERMS:
        term_start_time = time.perf_counter()
        # Politeness jitter to avoid detection
        time.sleep(random.uniform(1.0, 2.0))
        
        _, items, s_info = fetch_term(store_id, term)
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
    logger.info("Fetching all stores from Firestore...")
    
    # REMOVE .limit(1) once you have verified this run works
    # docs = list(db.collection('stores').limit(1).stream())
    docs = list(db.collection('stores').stream())
    
    
    all_stores = []
    for doc in docs:
        data = doc.to_dict()
        all_stores.append(data)
    
    all_stores.sort(key=lambda x: x.get('id', '000'))
    total_stores = len(all_stores)

    task_index = int(os.environ.get("CLOUD_RUN_TASK_INDEX", 0))
    total_tasks = int(os.environ.get("CLOUD_RUN_TASK_COUNT", 55))

    import math
    stores_per_task = math.ceil(total_stores / total_tasks)
    start_idx = task_index * stores_per_task
    end_idx = min(start_idx + stores_per_task, total_stores)

    if start_idx >= total_stores:
        return

    for i in range(start_idx, end_idx):
        s_id = all_stores[i].get('id')
        try:
            process_store(s_id)
        except Exception as e:
            logger.error(f"❌ Failed to process Store {s_id}: {e}")

if __name__ == "__main__":
    main()
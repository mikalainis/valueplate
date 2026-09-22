import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import firestore

# --- SETUP ---
app = FastAPI()

# --- ENABLE CORS (CRITICAL FOR BROWSER ACCESS) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (change this to your specific domain in production)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PricePilotAPI")

# Connect to Firestore
try:
    db = firestore.Client()
    logger.info("✅ Connected to Firestore")
except Exception as e:
    logger.error(f"❌ Failed to connect to Firestore: {e}")
    db = None

@app.get("/")
def health_check():
    return {"status": "API is online", "service": "Price Pilot"}

@app.get("/sales/{store_id}")
def get_sales(store_id: str):
    """
    Fetches sales for a specific store from the 'grocery_sales' collection.
    """
    if not db:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        logger.info(f"🔎 Fetching sales for Store {store_id}...")
        
        # Query the flat 'grocery_sales' collection
        sales_ref = db.collection('grocery_sales').where("store_id", "==", store_id)
        docs = sales_ref.stream()

        results = []
        for doc in docs:
            results.append(doc.to_dict())

        logger.info(f"✅ Found {len(results)} items for Store {store_id}.")
        return results

    except Exception as e:
        logger.error(f"❌ Error reading DB: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

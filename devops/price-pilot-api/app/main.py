from fastapi import FastAPI, HTTPException, Depends
from typing import List
from datetime import datetime

from app.database import get_db
from app.schemas import SaleItemRead

app = FastAPI(title="GrocerySmart Plan Engine", version="0.1.0")

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "plan-engine"}

@app.get("/sales/{store_id}", response_model=List[SaleItemRead])
def get_active_sales(store_id: str, db = Depends(get_db)):
    """
    Fetches currently active sales for a specific store.
    Used to prime the optimization algorithm.
    """
    try:
        sales_ref = db.collection("grocery_sales")
        
        # Query: Filter by store_id and ensure sale is still valid
        # Note: You need a composite index in Firestore for this query to work!
        query = sales_ref.where("store_id", "==", store_id)\
                         .where("valid_to", ">=", datetime.now())
        
        results = []
        for doc in query.stream():
            data = doc.to_dict()
            # Attach the ID for reference
            data['id'] = doc.id
            results.append(SaleItemRead(**data))
            
        return results

    except Exception as e:
        # In production, log the full stack trace
        print(f"Error fetching sales: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error accessing Sales Data")
from pathlib import Path
from typing import List, Optional

import redis
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from google.auth.exceptions import DefaultCredentialsError
from pydantic import BaseModel, Field

load_dotenv(Path(__file__).resolve().parent.parent / ".env.local")

# Import your existing logic
from app.firestore_client import FirestoreCredentialsError
from app.logic.nutrition_calculator import NutritionCalculator, FamilyMember, NutritionNeeds
from app.logic.deals_repository import (
    fetch_active_store_ids,
    fetch_deals,
    fetch_last_scrape_time,
    fetch_stores,
)
from app.logic.stores_repository import log_store_request, search_stores_by_zip

app = FastAPI()
calc = NutritionCalculator()

@app.exception_handler(FirestoreCredentialsError)
@app.exception_handler(DefaultCredentialsError)
async def firestore_credentials_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": f"Firestore credentials unavailable: {exc}"},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://valueplate.us",
        "https://www.valueplate.us",
        "https://studio-2558023820-f94a5.web.app",
        "https://studio-2558023820-f94a5.firebaseapp.com",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# --- Shared Infrastructure ---
def get_redis() -> Optional[redis.Redis]:
    host = os.getenv("REDIS_HOST")
    if not host:
        return None
    try:
        return redis.Redis(
            host=host,
            port=int(os.getenv("REDIS_PORT", "6379")),
            decode_responses=True,
            socket_connect_timeout=2.0,
        )
    except Exception:
        return None

# --- Routes ---


class DealItem(BaseModel):
    id: str
    name: str
    brand: Optional[str] = None
    category: Optional[str] = None
    store_id: Optional[str] = None
    sale_price: Optional[float] = None
    regular_price: Optional[float] = None
    is_deal: bool = False
    unit: Optional[str] = None
    price_per_unit: Optional[str] = None
    unit_price: Optional[float] = None
    unit_price_unit: Optional[str] = None
    image_url: Optional[str] = None
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None


class DealsResponse(BaseModel):
    items: List[DealItem]
    total: int
    as_of: Optional[str] = None


class StoreItem(BaseModel):
    id: str
    name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None


class StoresResponse(BaseModel):
    items: List[StoreItem]


class StoreSearchResult(BaseModel):
    id: str
    deals_store_id: Optional[str] = None
    name: str
    city: Optional[str] = None
    state: Optional[str] = None
    zip: str
    distance_miles: float
    has_deals: bool


class StoreSearchResponse(BaseModel):
    items: List[StoreSearchResult]


class StoreRequestBody(BaseModel):
    store_id: str = Field(..., min_length=1, max_length=64, description="Store identifier")
    zip: str = Field(..., min_length=5, max_length=10, pattern=r"^\d{5}(-\d{4})?$", description="US ZIP code")

    model_config = {
        "extra": "forbid",
        "str_strip_whitespace": True,
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "plan-engine"}


@app.get("/api/deals", response_model=DealsResponse)
async def get_deals(
    category: Optional[str] = None,
    q: Optional[str] = None,
    store_id: Optional[str] = None,
    on_sale: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
):
    """
    Sale items from `sales_v2` (devops/scraper/main.py's rewritten ShopRite
    scraper). Pass on_sale=true to get only items that are actually marked
    down (regular_price > price, or an active tprPrice window) rather than
    the full catalog.
    """
    limit = max(1, min(limit, 200))
    offset = max(0, offset)

    try:
        matches = fetch_deals(category=category, q=q, store_id=store_id, on_sale=on_sale)
        page = matches[offset : offset + limit]

        return DealsResponse(
            items=[DealItem(**item) for item in page],
            total=len(matches),
            as_of=fetch_last_scrape_time(),
        )
    except (FirestoreCredentialsError, DefaultCredentialsError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Firestore credentials unavailable: {exc}",
        )

@app.get("/api/stores", response_model=StoresResponse)
async def get_stores():
    """
    Stores that currently have items in `sales_v2`, resolved against the
    `stores` collection for human-readable names/locations.
    """
    try:
        store_ids = fetch_active_store_ids()
        stores = fetch_stores(store_ids)
        return StoresResponse(items=[StoreItem(**s) for s in stores])
    except (FirestoreCredentialsError, DefaultCredentialsError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Firestore credentials unavailable: {exc}",
        )


@app.get("/api/stores/search", response_model=StoreSearchResponse)
async def get_stores_search(zip: str, limit: int = 10):
    """
    Nearest stores to a zip code, sorted by distance. Distance is computed
    zip-centroid to zip-centroid (see app/logic/stores_repository.py) - no
    paid geocoding API, no per-store lat/lng needed. Stores with no `zip` on
    file are excluded rather than guessed at (see docs/spec.md §3 audit).
    `has_deals` reconciles the stores-collection id against the zero-padded
    id grocery_sales actually uses.
    """
    limit = max(1, min(limit, 50))
    try:
        results = search_stores_by_zip(zip.strip(), limit=limit)
    except (FirestoreCredentialsError, DefaultCredentialsError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Firestore credentials unavailable: {exc}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return StoreSearchResponse(items=[StoreSearchResult(**r) for r in results])


MAX_STORE_REQUEST_BYTES = 2048  # 2KB limit for store request JSON


@app.post("/api/stores/request", status_code=204)
async def post_store_request(body: StoreRequestBody, request: Request):
    """Logs interest in a not-yet-scraped store so we know what to add next."""
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_STORE_REQUEST_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Request payload exceeds maximum size limit (2KB)",
        )
    log_store_request(body.store_id, body.zip)


@app.post("/generate-optimized-plan")
async def generate_plan(
    members: List[FamilyMember], 
    store_ids: List[str],
    r_client: Optional[redis.Redis] = Depends(get_redis)
):
    """
    Combines Harris-Benedict needs with real-time grocery sales.
    """
    # 1. Calculate the target macros for the household
    household_needs = calc.calculate_household_needs(members)
    target_daily_cals = household_needs.total_weekly_calories / 7

    # 2. Query Elasticsearch for recipes matching the macro profile
    # Mocking recipe retrieval for architectural flow
    suitable_recipes = [
        {
            "id": "r1", 
            "name": "Pan-Seared Salmon", 
            "calories": 650, 
            "ingredients": [
                {"name": "Atlantic Salmon Fillet", "qty": 0.5, "base_price": 7.99}
            ]
        }
    ]

    # 3. Cross-reference with Redis for sale optimization (optional)
    optimized_plan = []
    for recipe in suitable_recipes:
        current_cost = 0.0
        for ing in recipe["ingredients"]:
            # Check local stores for sales
            cheapest = ing["base_price"]
            if r_client:
                for s_id in store_ids:
                    try:
                        sale_data = r_client.get(f"sale:{s_id}:{ing['name']}")
                        if sale_data:
                            # Logic to parse and compare sale prices
                            pass
                    except Exception:
                        pass
            current_cost += cheapest
            
        optimized_plan.append({
            "name": recipe["name"],
            "cost": round(current_cost, 2),
            "cal_contribution": recipe["calories"]
        })

    return {
        "nutritional_targets": household_needs,
        "suggested_plan": optimized_plan
    }
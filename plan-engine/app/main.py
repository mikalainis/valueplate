from pathlib import Path
from typing import List, Optional

import redis
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv(Path(__file__).resolve().parent.parent / ".env.local")

# Import your existing logic
from app.logic.nutrition_calculator import NutritionCalculator, FamilyMember, NutritionNeeds
from app.logic.deals_repository import fetch_deals, fetch_last_scrape_time

app = FastAPI()
calc = NutritionCalculator()

# Local dev only: allow the Vite dev server to call this API directly.
# Tighten this before deploying anywhere real.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# --- Shared Infrastructure ---
def get_redis():
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=6379,
        decode_responses=True
    )

# --- Routes ---


class DealItem(BaseModel):
    id: str
    name: str
    brand: Optional[str] = None
    category: Optional[str] = None
    store_id: Optional[str] = None
    sale_price: Optional[float] = None
    regular_price: Optional[float] = None
    unit: Optional[str] = None
    price_per_unit: Optional[str] = None
    image_url: Optional[str] = None
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None


class DealsResponse(BaseModel):
    items: List[DealItem]
    total: int
    as_of: Optional[str] = None


@app.get("/api/deals", response_model=DealsResponse)
async def get_deals(
    category: Optional[str] = None,
    q: Optional[str] = None,
    store_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """
    Sale items from the existing shoprite_sales scrape (Firestore `grocery_sales`
    — see docs/existing-infrastructure.md). No Postgres/§3 schema exists yet, so
    this reads Firestore directly; regular_price/valid_from/valid_to are always
    None today because the current scrape output doesn't carry them.
    """
    limit = max(1, min(limit, 200))
    offset = max(0, offset)

    matches = fetch_deals(category=category, q=q, store_id=store_id)
    page = matches[offset : offset + limit]

    return DealsResponse(
        items=[DealItem(**item) for item in page],
        total=len(matches),
        as_of=fetch_last_scrape_time(),
    )

@app.post("/generate-optimized-plan")
async def generate_plan(
    members: List[FamilyMember], 
    store_ids: List[str],
    r_client: redis.Redis = Depends(get_redis)
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

    # 3. Cross-reference with Redis for sale optimization
    optimized_plan = []
    for recipe in suitable_recipes:
        current_cost = 0.0
        for ing in recipe["ingredients"]:
            # Check local stores for sales
            cheapest = ing["base_price"]
            for s_id in store_ids:
                sale_data = r_client.get(f"sale:{s_id}:{ing['name']}")
                if sale_data:
                    # Logic to parse and compare sale prices
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
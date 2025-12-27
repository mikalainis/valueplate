from fastapi import FastAPI, Depends, HTTPException
from typing import List
import redis
import os

# Import your existing logic
from app.nutrition_calculator import NutritionCalculator, FamilyMember, NutritionNeeds

app = FastAPI()
calc = NutritionCalculator()

# --- Shared Infrastructure ---
def get_redis():
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"), 
        port=6379, 
        decode_responses=True
    )

# --- Routes ---

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
import numpy as np
import pandas as pd
from typing import List, Dict
import redis
import json

class PlanOptimizer:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def generate_plan(self, user_stores: List[str], recipes: List[Dict]) -> Dict:
        """
        Optimizes meal selection based on real-time sales in user-selected stores.
        """
        optimized_recipes = []
        
        for recipe in recipes:
            total_recipe_cost = 0.0
            ingredients_on_sale = []

            for ing in recipe['ingredients']:
                # Lookup price in Redis using the key pattern from our Go Sync Service
                # sale:{store_id}:{item_name}
                cheapest_price = float('inf')
                sale_found = False

                for store_id in user_stores:
                    cache_key = f"sale:{store_id}:{ing['name']}"
                    sale_data = self.redis.get(cache_key)
                    
                    if sale_data:
                        data = json.loads(sale_data)
                        if data['sale_price'] < cheapest_price:
                            cheapest_price = data['sale_price']
                            sale_found = True

                # If no sale found, fallback to standard price or skip (per business logic)
                current_price = cheapest_price if sale_found else ing['base_price']
                total_recipe_cost += (current_price * ing['quantity'])
                
                if sale_found:
                    ingredients_on_sale.append(ing['name'])

            optimized_recipes.append({
                "recipe_id": recipe["id"],
                "total_cost": round(total_recipe_cost, 2),
                "on_sale_count": len(ingredients_on_sale),
                "savings_items": ingredients_on_sale
            })

        # Sort by lowest cost and return top recommendations
        df = pd.DataFrame(optimized_recipes)
        top_plans = df.sort_values(by="total_cost").head(7).to_dict(orient="records")
        
        return top_plans
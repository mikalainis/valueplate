import redis
import json

# Connect to the Redis container
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Mock Sales Data for "Whole Foods" (store_001) and "Kroger" (store_002)
mock_sales = [
    {"store_id": "store_001", "name": "Atlantic Salmon Fillet", "sale_price": 6.99},
    {"store_id": "store_001", "name": "Green Asparagus", "sale_price": 1.49},
    {"store_id": "store_002", "name": "Spiral Smoked Ham", "sale_price": 0.89},
    {"store_id": "store_002", "name": "Sweet Potatoes", "sale_price": 0.45}
]

def seed():
    print("Seeding Redis with mock sales...")
    for item in mock_sales:
        # Key format matches our Sync Service: sale:{store_id}:{item_name}
        key = f"sale:{item['store_id']}:{item['name']}"
        r.set(key, json.dumps(item))
    print("Done! Plan Engine can now find discounted items.")

if __name__ == "__main__":
    seed()
import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "backend", ".env"))

# Set up path to import backend modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from services.prediction_tracker import tracker
from services.price_service import price_service

async def test_verification():
    print("Testing Angel One Auth first...")
    is_authed = await price_service.authenticate()
    print(f"Auth Success: {is_authed}")
    
    print("\nStarting manual verification test...")
    await tracker.run_cleanup_and_verification(source="manual")
    stats = tracker.get_stats()
    print("\n--- Current Stats ---")
    for k, v in stats.items():
        if k != "recent_performance":
            print(f"{k}: {v}")
    print("-------------------")

if __name__ == "__main__":
    asyncio.run(test_verification())

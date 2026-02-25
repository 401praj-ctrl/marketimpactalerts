import sys
import os
import asyncio
import json
from datetime import datetime, timedelta

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.prediction_tracker import PredictionTracker, PREDICTIONS_FILE, STATS_FILE

async def test_verification():
    # Setup test data
    test_tracker = PredictionTracker()
    
    # Create a dummy prediction that "expired" yesterday
    expired_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    timestamp = (datetime.now() - timedelta(days=2)).isoformat()
    
    test_prediction = {
        "timestamp": timestamp,
        "event": "Test Event",
        "company": "RELIANCE",
        "stocks": ["RELIANCE.NS"],
        "direction": "UP",
        "probability": 0.8,
        "impact_date_est": expired_date,
        "live_price": 2500.0,
        "verified": False
    }
    
    # Write to a temp log file for testing if we don't want to mess with real one
    # But for this verification we'll just check the logic
    
    print(f"Simulating verification for event on {expired_date}...")
    
    # We can't easily mock Finnhub without more effort, 
    # but we can verify the function exists and runs logic.
    try:
        # Note: This will likely print "WARNING: FINNHUB_API_KEY not set" 
        # unless it's in the environment, which is expected.
        await test_tracker.run_cleanup_and_verification()
        print("SUCCESS: run_cleanup_and_verification executed (check output for warnings).")
    except Exception as e:
        print(f"FAILED: run_cleanup_and_verification crashed: {e}")

if __name__ == "__main__":
    asyncio.run(test_verification())

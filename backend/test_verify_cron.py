import asyncio
import os
import sys
import json
from datetime import datetime, timedelta

# Add parent directory to sys.path to import services
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.prediction_tracker import PredictionTracker
from services.price_service import price_service

async def test_full_verification():
    print("--- [TEST] Full Verification Resilience Test ---")
    tracker = PredictionTracker()
    
    # Check if predictions file exists
    pred_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "predictions_log.jsonl")
    if not os.path.exists(pred_file):
        print(f"DEBUG: No predictions file found at {pred_file}. Creating a dummy prediction for testing.")
        # Ensure data dir exists
        os.makedirs(os.path.dirname(pred_file), exist_ok=True)
        
        # Create a dummy prediction that needs verification
        # Event happened in the past, impact date is also in the past
        dummy = {
            "stocks": ["NSE:RELIANCE"],
            "event": "Dummy Resilience Test",
            "timestamp": (datetime.now() - timedelta(days=2)).isoformat(),
            "impact_date_est": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
            "probability": 85,
            "impact_direction": "UP",
            "tier": "Tier-1",
            "live_price": 1393.9,
            "predicted_price": 1420.0,
            "verified": False
        }
        with open(pred_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(dummy) + "\n")
        print(f"DEBUG: Created dummy prediction for NSE:RELIANCE.")

    print("\n[STEP 1] Running verification flow...")
    # This should run through all pending predictions
    # We expect it to hit AngelOne errors (due to missing creds) but fall back to YFinance without crashing
    try:
        await tracker.run_cleanup_and_verification(source="manual-test")
        print("\n[SUCCESS] Verification flow completed without unhandled exceptions.")
    except Exception as e:
        print(f"\n[FATAL] Verification flow CRASHED: {e}")
        import traceback
        traceback.print_exc()

    print("\n--- [TEST COMPLETE] ---")

if __name__ == "__main__":
    asyncio.run(test_full_verification())

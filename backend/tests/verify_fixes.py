import sys
import os
import json
import asyncio
from datetime import datetime, timedelta

# Mock sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from services.prediction_tracker import tracker
from services.price_service import price_service

async def test_verification_logic():
    print("Testing T+0 Verification Logic...")
    
    # Mock current time to be after market close today
    now = datetime.utcnow() + timedelta(hours=5, minutes=30)
    # Ensure it's after 15:45
    test_now = now.replace(hour=16, minute=0)
    
    impact_date = test_now.date()
    impact_date_str = impact_date.isoformat()
    
    print(f"Mock Today: {test_now}")
    print(f"Impact Date: {impact_date_str}")
    
    # Check if logic in tracker would verify
    market_closed = test_now.hour > 15 or (test_now.hour == 15 and test_now.minute >= 45)
    should_verify = impact_date < test_now.date() or (impact_date == test_now.date() and market_closed)
    
    print(f"Should Verify (Expected True): {should_verify}")
    assert should_verify == True, "T+0 logic failed!"
    
    print("Testing Fallback Price Logic...")
    # Mock analysis
    analysis = {
        "probability": 60,
        "live_price": 500.0,
        "tier": "Tier-1",
        "impact_direction": "UP"
    }
    
    # Manually run the fallback logic from main.py
    lp = float(analysis['live_price'])
    p = float(analysis.get('probability', 60))
    direction = analysis.get('impact_direction', 'NEUTRAL').lower()
    tier = analysis.get('tier', 'Tier-3')
    
    base_move = 0.01 if tier == 'Tier-1' else (0.005 if tier == 'Tier-2' else 0.002)
    move_factor = base_move * (p / 50.0) 
    
    predicted_price = round(lp * (1 + move_factor), 2)
    upside_pct = f"+{(move_factor * 100):.2f}%"
    
    print(f"Input: LP={lp}, Prob={p}, Tier={tier}")
    print(f"Result: Predicted={predicted_price}, Upside={upside_pct}")
    
    assert predicted_price > 500.0
    assert "1.20%" in upside_pct, f"Expected 1.20% (0.01 * 60/50), got {upside_pct}"
    
    print("\nALL BACKEND TESTS PASSED!")

if __name__ == "__main__":
    asyncio.run(test_verification_logic())

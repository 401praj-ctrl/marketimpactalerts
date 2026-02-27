import asyncio
import os
import sys
import datetime
import json

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from services.price_service import price_service
from services.ai_service import validate_stocks
from services.prediction_tracker import tracker

# We import the notification function from main
# Since we are in the root, we need to handle the import carefully
from backend.main import send_onesignal_notification, save_alerts, load_alerts, load_devices

async def trigger_demo():
    print("START: Triggering Demo Alert (75% Probability)...")
    
    # 1. Mock Headline
    headline = "Reliance Industries and NVIDIA announce strategic partnership for 'Bharat AI' Cloud infrastructure across India."
    symbol = "NSE:RELIANCE"
    
    # 2. Fetch Live Price
    print(f"INFO: Fetching live price for {symbol}...")
    live_price = await price_service.get_live_price(symbol)
    if not live_price:
        live_price = 1390.0 # Fallback
    
    # 3. Construct Alert Mock
    # We simulate a 75% probability Tier-1 impact
    prob = 75
    lp = float(live_price)
    move = 0.015 # 1.5% for 75% prob
    pp = round(lp * (1 + move), 2)
    
    demo_alert = {
        "id": f"demo_{int(datetime.datetime.now().timestamp())}",
        "event": "Reliance-NVIDIA AI partnership",
        "company": "Reliance Industries",
        "sector": "Technology / AI",
        "stocks": [symbol],
        "impact": "high",
        "impact_direction": "UP",
        "impact_description": "A strategic partnership with NVIDIA positions Reliance as a leader in India's sovereign AI cloud. This move is expected to drive long-term value through cloud infrastructure and AI service subscriptions. The market sees this as a major positive catalyst.",
        "event_date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "impact_date_est": (datetime.datetime.now() + datetime.timedelta(days=2)).strftime("%Y-%m-%d"),
        "probability": prob,
        "live_price": lp,
        "predicted_price": pp,
        "upside_pct": f"+{(move*100):.2f}%",
        "currency": "INR",
        "tier": "Tier-1",
        "timestamp": datetime.datetime.now().isoformat(),
        "published": datetime.datetime.now().isoformat(),
        "article_summary": "Major deal between RIL and NVIDIA for India-wide AI cloud deployment.",
        "link": "https://example.com/demo-news"
    }

    # 4. Save to Cache
    print("INFO: Saving to cache...")
    alerts = load_alerts()
    # Add to top
    new_alerts = [demo_alert] + alerts
    save_alerts(new_alerts[:100])
    tracker.save_prediction(demo_alert)

    # 5. Send Notification
    print("INFO: Sending OneSignal Notification...")
    # Mock registered devices if none (usually segments are used anyway)
    devices = load_devices()
    
    # We call the function
    # Note: send_onesignal_notification in main.py uses hardcoded app_id correctly
    try:
        send_onesignal_notification([demo_alert], devices)
        print("SUCCESS: Demo alert triggered successfully!")
        print(f"Headline: {headline}")
        print(f"Price: {lp} -> Target: {pp} ({demo_alert['upside_pct']})")
    except Exception as e:
        print(f"FAILURE: Failed to send notification: {e}")

if __name__ == "__main__":
    asyncio.run(trigger_demo())

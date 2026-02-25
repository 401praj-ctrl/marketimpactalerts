import asyncio
import os
import json
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from services.price_service import price_service

async def debug_refresh():
    alerts_file = os.path.join('backend', 'data', 'cached_alerts.json')
    if not os.path.exists(alerts_file):
        print("Alerts file not found")
        return

    with open(alerts_file, 'r') as f:
        alerts = json.load(f)

    print(f"Loaded {len(alerts)} alerts")
    updated = False
    
    for alert in alerts[:30]:
        stocks = alert.get('stocks', [])
        if not stocks:
            print(f"No stocks for alert: {alert.get('event')}")
            continue
            
        symbol = stocks[0]
        print(f"Fetching price for {symbol}...")
        price = await price_service.get_live_price(symbol)
        
        if price:
            print(f"  Got price: {price}")
            if price != alert.get('live_price'):
                alert['live_price'] = price
                updated = True
        else:
            print(f"  FAILED to get price for {symbol}")

    if updated:
        with open(alerts_file, 'w') as f:
            json.dump(alerts, f, indent=2)
        print("Updated alerts file")
    else:
        print("No changes made to alerts file")

if __name__ == "__main__":
    asyncio.run(debug_refresh())

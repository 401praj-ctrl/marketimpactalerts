import asyncio
import json
import os
import sys
import datetime

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from services.ai_service import validate_stocks, MACRO_SECTOR_MAPPING
from services.price_service import price_service

CACHE_FILE = "backend/data/cached_alerts.json"

async def patch_cache():
    if not os.path.exists(CACHE_FILE):
        print("Cache file not found.")
        return

    with open(CACHE_FILE, "r") as f:
        alerts = json.load(f)

    print(f"Total alerts to check: {len(alerts)}")
    updated_count = 0

    for a in alerts:
        changed = False
        sector = a.get("sector", "Macro")
        stocks = a.get("stocks", [])
        
        # 1. Fix missing stocks using sector mapping
        if not stocks:
            new_stocks = validate_stocks([], sector=sector)
            if new_stocks:
                print(f"  [PATCH] Added stocks {new_stocks} for sector '{sector}'")
                a["stocks"] = new_stocks
                stocks = new_stocks
                changed = True

        # 2. Fix missing live_price
        if stocks and not a.get("live_price"):
            symbol = stocks[0]
            price = await price_service.get_live_price(symbol)
            if price:
                print(f"  [PATCH] Fetched live price {price} for {symbol}")
                a["live_price"] = price
                a["currency"] = price_service.get_currency_for_symbol(symbol)
                changed = True

        # 3. Fix missing predicted_price
        if a.get("live_price") and (not a.get("predicted_price") or a.get("predicted_price") == "None"):
            try:
                lp = float(a["live_price"])
                p = float(a.get("probability", 70))
                direction = a.get("impact_direction", "UP").lower()
                tier = a.get("tier", "Tier-2")
                
                base_move = 0.01 if tier == 'Tier-1' else (0.005 if tier == 'Tier-2' else 0.002)
                move_factor = base_move * (p / 50.0) 
                
                if direction == 'up':
                    a['predicted_price'] = round(lp * (1 + move_factor), 2)
                    a['upside_pct'] = f"+{(move_factor * 100):.2f}%"
                elif direction == 'down':
                    a['predicted_price'] = round(lp * (1 - move_factor), 2)
                    a['upside_pct'] = f"-{(move_factor * 100):.2f}%"
                else:
                    a['predicted_price'] = lp
                    a['upside_pct'] = "0.00%"
                
                print(f"  [PATCH] Calculated predicted price {a['predicted_price']} ({a['upside_pct']})")
                changed = True
            except Exception as e:
                print(f"  [ERROR] Failed to calculate price: {e}")

        if changed:
            updated_count += 1

    if updated_count > 0:
        with open(CACHE_FILE, "w") as f:
            json.dump(alerts, f, indent=2)
        print(f"\nSUCCESS: Updated {updated_count} alerts in cache.")
    else:
        print("\nNo updates needed.")

if __name__ == "__main__":
    asyncio.run(patch_cache())

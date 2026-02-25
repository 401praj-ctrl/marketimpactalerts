import json
import os
import sys
from datetime import datetime

os.chdir("backend")
sys.path.append(os.getcwd())

from main import cached_alerts, save_alerts, refresh_cached_prices
import asyncio

async def patch_alerts():
    print(f"Loaded {len(cached_alerts)} alerts from cached_alerts.json.")
    
    dirty = False
    new_date = "2026-02-25"
    
    for alert in cached_alerts:
        if alert.get("eventDate") == "2026-02-26":
            alert["eventDate"] = new_date
            # Also patch impact_date_est backwards if it was calculated based on the wrong day
            if alert.get("impact_date_est") == "2026-02-26":
                alert["impact_date_est"] = new_date
            dirty = True
            
        # Clear out current/target prices so refresh_cached_prices is forced to fetch fresh ones
        if "currentPrice" in alert:
            alert["currentPrice"] = ""
        if "targetPrice" in alert:
            alert["targetPrice"] = ""
            
    if dirty:
        print(f"Patched dates to {new_date}.")
        
    print("Forcing Angel One smart API price refresh across all past alerts...")
    await refresh_cached_prices()
    
    save_alerts(cached_alerts)
    print("Successfully patched dates and triggered price refresh.")

if __name__ == "__main__":
    asyncio.run(patch_alerts())

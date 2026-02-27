import json
import os

CACHE_FILE = "backend/data/cached_alerts.json"

def check_today_alerts():
    if not os.path.exists(CACHE_FILE):
        print("Cache file not found.")
        return

    with open(CACHE_FILE, "r") as f:
        alerts = json.load(f)

    print(f"Total alerts in cache: {len(alerts)}")
    print("-" * 30)

    for i, a in enumerate(alerts):
        stocks = a.get("stocks", [])
        lp = a.get("live_price")
        pp = a.get("predicted_price")
        event = a.get("event", "No Event")
        sector = a.get("sector", "No Sector")
        date = a.get("event_date", "No Date")
        
        status = []
        if not stocks: status.append("MISSING STOCKS")
        if not lp: status.append("MISSING LIVE_PRICE")
        if not pp: status.append("MISSING IMPACT_PRICE")
        
        if status:
            print(f"[{i}] [{date}] {event[:50]}...")
            print(f"    Sector: {sector}")
            print(f"    Status: {', '.join(status)}")
            print(f"    Raw: Stocks: {stocks}, LP: {lp}, PP: {pp}")
        else:
            # print(f"[{i}] {event[:50]}... OK")
            pass

if __name__ == "__main__":
    check_today_alerts()

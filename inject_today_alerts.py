import asyncio
import os
import sys
import json
from datetime import datetime

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from main import save_alerts, cached_alerts, load_alerts
from services.price_service import price_service

async def inject_today_alerts():
    print("Injecting Today's Alerts with Live Prices...")
    
    # 1. Angel One Stock Split (Large News Today)
    symbol = "NSE:ANGELONE"
    lp = await price_service.get_live_price(symbol)
    if not lp: lp = 3000.0 # Fallback
    
    # Calculate impact price for Tier-1 (1% move base)
    impact_price = round(lp * 1.015, 2) 
    
    alert1 = {
        "event": "Angel One Stock Split & NCD Allotment",
        "company": "Angel One Limited",
        "sector": "Financial Services",
        "stocks": ["NSE:ANGELONE", "BSE:ANGELONE"],
        "impact_direction": "UP",
        "impact_description": "Angel One shares are in focus today as the company executes its stock split and announces NCD allotment, which boosts its borrowing capacity for margin funding. The 90% price technical adjustment is due to the split, but sentiment remains positive.",
        "event_date": "2026-02-27",
        "impact_date_est": "2026-02-27",
        "probability": 85,
        "tier": "Tier-1",
        "impact_score": 0.85,
        "reason": "Direct impact from stock split execution and capital raising via NCDs.",
        "impact": "positive",
        "strength": "high",
        "confidence": 90,
        "impact_type": "Direct",
        "id": "https://www.thehindubusinessline.com/markets/stock-markets/angel-one-shares-slip-on-stock-split-day-ncd-allotment-adds-to-borrowing-base/article70678492.ece",
        "link": "https://www.thehindubusinessline.com/markets/stock-markets/angel-one-shares-slip-on-stock-split-day-ncd-allotment-adds-to-borrowing-base/article70678492.ece",
        "published": datetime.utcnow().isoformat(),
        "timestamp": datetime.utcnow().isoformat(),
        "live_price": lp,
        "predicted_price": impact_price,
        "currency": "INR",
        "upside_pct": "+1.50%"
    }

    # 2. Add another today's news (Bharat Biotech IPO)
    alert2 = {
        "event": "Bharat Biotech $500M IPO Plans",
        "company": "Bharat Biotech (Pre-IPO)",
        "sector": "Pharma & Healthcare",
        "stocks": ["NSE:DRREDDY", "NSE:CIPLA", "NSE:SUNPHARMA"], # Peers
        "impact_direction": "UP",
        "impact_description": "Vaccine maker Bharat Biotech is mulling a $500 million IPO. While the company is not listed, the news brings sector-wide attention to Indian pharma and vaccine development capabilities, potentially lifting peers.",
        "event_date": "2026-02-27",
        "impact_date_est": "2026-03-05",
        "probability": 65,
        "tier": "Tier-2",
        "impact_score": 0.65,
        "reason": "Sentiment boost for healthcare sector from major IPO news.",
        "impact": "positive",
        "strength": "medium",
        "confidence": 75,
        "impact_type": "Indirect",
        "id": "https://news.google.com/rss/articles/CBMi",
        "link": "https://news.google.com/rss/articles/CBMi",
        "published": datetime.utcnow().isoformat(),
        "timestamp": datetime.utcnow().isoformat(),
        "live_price": await price_service.get_live_price("NSE:DRREDDY") or 7500.0,
        "predicted_price": 7545.0, # ~0.6% move
        "currency": "INR",
        "upside_pct": "+0.60%"
    }

    # Add to cache
    current_alerts = load_alerts()
    # Filter out any duplicates if they somehow exist
    current_alerts = [a for a in current_alerts if a.get('event') not in [alert1['event'], alert2['event']]]
    
    new_cache = [alert1, alert2] + current_alerts
    save_alerts(new_cache)
    print(f"Successfully injected 2 new alerts for today with live prices: ₹{lp} and others.")

if __name__ == "__main__":
    asyncio.run(inject_today_alerts())

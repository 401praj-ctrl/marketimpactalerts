import asyncio
import os
import sys
import json
from datetime import datetime

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from main import analyze_headline_full, save_alerts, cached_alerts, processed_links, save_processed
from services.price_service import price_service

async def manual_backfill():
    print("Starting Manual Backfill for Today's Alerts...")
    
    # Links to force re-analysis
    links_to_reprocess = [
        "https://www.thehindubusinessline.com/markets/stock-markets/angel-one-shares-slip-on-stock-split-day-ncd-allotment-adds-to-borrowing-base/article70678492.ece",
        "https://www.livemint.com/market/stock-market-news/angel-one-stock-split-angel-one-share-price-crashes-90-today-here-s-what-actually-happened-11772089387625.html"
    ]
    
    for link in links_to_reprocess:
        print(f"Analyzing {link}...")
        # Simulating a simple headline for the prompt
        headline = "Angel One shares slip on stock split day; NCD allotment adds to borrowing base"
        if "livemint" in link:
            headline = "Angel One stock split: Share price crashes 90% today; here's what actually happened"
            
        # We'll use the analyze_headline_full logic but forced
        try:
            # Mock the headline object
            h = {
                "title": headline,
                "link": link,
                "published": datetime.utcnow().isoformat()
            }
            
            # This will call AI and Price service
            # We bypass the 'processed_links' check here
            from main import analyze_headline_full
            analysis = await analyze_headline_full(h, source="MANUAL_BACKFILL")
            
            if analysis and analysis.get("event") != "no impact":
                print(f"  SUCCESS! Alert generated for: {analysis['event']}")
                print(f"  Live Price: {analysis.get('live_price')}")
                print(f"  Impact Price: {analysis.get('predicted_price')}")
                
                # Add to cache and sync
                cached_alerts.insert(0, analysis)
                save_alerts(cached_alerts)
                
                # Ensure it's in processed_links
                if link not in processed_links:
                    processed_links.add(link)
                    save_processed(processed_links)
            else:
                print(f"  SKIP: AI returned no impact for {headline}")
                
        except Exception as e:
            print(f"  ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(manual_backfill())

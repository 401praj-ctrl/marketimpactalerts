from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services.rss_service import fetch_latest_headlines
from services.news_api_service import fetch_news_api_headlines
from services.news_data_service import fetch_news_data_headlines
from services.hacker_news_service import fetch_hacker_news_headlines
from services.social_media_service import fetch_social_media_headlines
from services.ai_service import analyze_headlines_bulk
from typing import List
import uvicorn
import datetime
from dateutil import parser as date_parser

app = FastAPI(title="Market Event Impact Alerts API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request, call_next):
    print(f"DEBUG: Incoming {request.method} {request.url}")
    response = await call_next(request)
    print(f"DEBUG: Sending {response.status_code}")
    return response

# Root path check
@app.get("/")
async def root():
    return {"message": "Market Impact Alerts API is running"}

@app.get("/health")
async def health():
    return {"status": "ok"}

import asyncio

# In-memory cache for alerts to simulate a real backend
cached_alerts = []

# Lock to prevent concurrent analysis
analysis_lock = asyncio.Lock()

# Set to track already analyzed headline links
processed_links = set()


from services.ai_service import identify_high_impact_events, perform_deep_analysis
from services.scraper_service import fetch_article_content

async def run_analysis(source="AUTOMATED"):
    async with analysis_lock:
        print("\n" + "="*50)
        print(f"STARTING {source} MARKET ANALYSIS")
        print("="*50)
        try:
            today = datetime.datetime.now().date()
            print(f"DEBUG: Filtering for live news date: {today}")
            
            # Fetch headlines concurrently
            results = await asyncio.gather(
                fetch_news_api_headlines(),
                fetch_news_data_headlines(),
                fetch_hacker_news_headlines(),
                fetch_social_media_headlines(),
                return_exceptions=True
            )
            
            # Fetch RSS headlines in a separate thread to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            rss_headlines = await loop.run_in_executor(None, fetch_latest_headlines)
            
            headlines = rss_headlines
            for res in results:
                if isinstance(res, list):
                    headlines.extend(res)
                else:
                    print(f"ERROR: News source failed: {res}")
            
            # Filter for TODAY'S and YESTERDAY'S news (48h window)
            live_headlines = []
            yesterday = today - datetime.timedelta(days=1)
            
            for h in headlines:
                try:
                    # Parse date (handle timezone aware/naive)
                    pub_dt = date_parser.parse(h['published'])
                    pub_date = pub_dt.date()
                    
                    if pub_date >= yesterday:
                        live_headlines.append(h)
                    else:
                        # Optional: Print skipped dates for debugging
                        # print(f"Skipped old news: {pub_date} (Title: {h['title'][:30]}...)")
                        pass
                except Exception:
                    # If date parsing fails, strictly keep it to ensure we don't miss "just now" items
                    # often realtime feeds might have weird formats, safer to include.
                    live_headlines.append(h)

            # Filter for new headlines only (not already analyzed)
            new_headlines = [h for h in live_headlines if h['link'] not in processed_links]
            
            old_count = len(headlines) - len(live_headlines)
            skipped_count = len(live_headlines) - len(new_headlines)
            
            print(f"DEBUG: Found {len(headlines)} headlines. {old_count} old/not-today. {skipped_count} already analyzed. {len(new_headlines)} fresh today.")
            
            if not new_headlines:
                print("DEBUG: All current headlines have already been analyzed. Skipping AI run.")
                print("="*50 + "\n")
                return

            # PASS 1: Identify high-impact candidates (bulk check)
            batch = new_headlines[:20]
            candidates = await identify_high_impact_events(batch) 
            
            # PASS 2: Selective Deep Dive for high-signal events
            final_alerts = []
            for candidate in candidates:
                # Selective trigger: if probability > 70 or strength is high
                if candidate.get('probability', 0) >= 70 or candidate.get('strength') == 'high':
                    print(f"  --> TRIGERING PASS 2 DEEP DIVE for: {candidate['event']}")
                    full_text = await fetch_article_content(candidate['link'])
                    deep_report = await perform_deep_analysis(full_text, candidate['event'])
                    
                    if deep_report:
                        # Merge deep report into candidate
                        candidate.update(deep_report)
                        print(f"      Status: Deep Analysis Complete.")
                    else:
                        print(f"      Status: Deep Analysis Failed. Falling back to Pass 1 data.")
                
                # Standardize schema
                candidate['timestamp'] = candidate.get('published', datetime.datetime.now().isoformat())
                candidate['article_summary'] = candidate.get('article_summary', candidate.get('reason', ''))
                
                # Filter out low probability alerts (e.g. Pass 2 rejected it)
                if candidate.get('probability', 0) >= 50:
                    final_alerts.append(candidate)
                    print(f"      Status: High probability ({candidate.get('probability')}%), Added alert.")
                else:
                    print(f"      Status: Low probability ({candidate.get('probability')}%), Skipping alert.")

            # Record these as processed
            for h in batch:
                processed_links.add(h['link'])

            if final_alerts:
                global cached_alerts
                # Add new alerts to the front
                cached_alerts = final_alerts + cached_alerts
                # Limit cache size
                cached_alerts = cached_alerts[:50]
                print(f"SUCCESS: Added {len(final_alerts)} new market impact alerts.")
            else:
                print("DEBUG: No significant market impact detected in Pass 1 batch.")
                
            print(f"DEBUG: Analysis finished. Total alerts in cache: {len(cached_alerts)}")
        except Exception as e:
            print(f"ERROR during analysis: {e}")
        print("="*50 + "\n")

async def background_scheduler():
    # Wait for app to be fully ready
    await asyncio.sleep(5)
    while True:
        await run_analysis(source="AUTOMATED")
        print("NEXT AUTOMATED ANALYSIS IN 60 MINUTES...")
        await asyncio.sleep(3600) # 60 minutes

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(background_scheduler())

@app.get("/alerts")
async def get_alerts():
    print(f"DEBUG: Returning {len(cached_alerts)} alerts")
    return cached_alerts

@app.post("/refresh")
async def refresh_alerts():
    print("\n" + "!"*50)
    print("RECEIVED USER REFRESH REQUEST")
    print("!"*50 + "\n")
    # Trigger analysis manually (respecting the lock)
    await run_analysis(source="USER REQUESTED")
    return cached_alerts

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

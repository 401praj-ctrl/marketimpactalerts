import sys
import os
import json
import asyncio
import datetime
import uvicorn
import requests
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dateutil import parser as date_parser
from typing import List
from pydantic import BaseModel

# Add the current directory (backend) to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Prioritize system environment variables (Render Dashboard)
if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')):
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
    print("DEBUG: Loaded configuration from local .env file")
else:
    print("DEBUG: No .env file found. Utilizing Render/System Environment Variables.")


from services.rss_service import fetch_latest_headlines
from services.news_api_service import fetch_news_api_headlines
from services.news_data_service import fetch_news_data_headlines
from services.hacker_news_service import fetch_hacker_news_headlines
from services.social_media_service import fetch_social_media_headlines
from services.ai_service import identify_high_impact_events, perform_deep_analysis
from services.scraper_service import fetch_article_content

app = FastAPI(title="ALPHA IMPACT API")

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

from fastapi.responses import Response

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

# File-based persistence
ALERTS_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
ALERTS_FILE = os.path.join(ALERTS_DATA_DIR, "cached_alerts.json")
PROCESSED_FILE = os.path.join(ALERTS_DATA_DIR, "processed_links.json")
DEVICES_FILE = os.path.join(ALERTS_DATA_DIR, "devices.json")
os.makedirs(ALERTS_DATA_DIR, exist_ok=True)

def load_alerts():
    if os.path.exists(ALERTS_FILE):
        try:
            with open(ALERTS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"ERROR loading alerts: {e}")
    return []

def save_alerts(alerts):
    try:
        with open(ALERTS_FILE, "w") as f:
            json.dump(alerts, f, indent=2)
    except Exception as e:
        print(f"ERROR saving alerts: {e}")

def load_processed():
    if os.path.exists(PROCESSED_FILE):
        try:
            with open(PROCESSED_FILE, "r") as f:
                return set(json.load(f))
        except Exception as e:
            print(f"ERROR loading processed links: {e}")
    return set()

def save_processed(links):
    try:
        with open(PROCESSED_FILE, "w") as f:
            json.dump(list(links), f)
    except Exception as e:
        print(f"ERROR saving processed links: {e}")

def load_devices():
    if os.path.exists(DEVICES_FILE):
        try:
            with open(DEVICES_FILE, "r") as f:
                return set(json.load(f))
        except Exception as e:
            print(f"ERROR loading devices: {e}")
    return set()

def save_devices(devices):
    try:
        with open(DEVICES_FILE, "w") as f:
            json.dump(list(devices), f)
    except Exception as e:
        print(f"ERROR saving devices: {e}")

def send_onesignal_notification(alerts, devices):
    if not alerts or not devices:
        return
    app_id = "7087a2bc-e285-49a9-a404-15be244a893f"
    api_key = os.environ.get("ONESIGNAL_REST_API_KEY", "")
    if not api_key:
        print("ERROR: ONESIGNAL_REST_API_KEY is not set. Cannot send push notifications.")
        return

    headers = {
        "Authorization": f"Basic {api_key}",
        "Content-Type": "application/json; charset=utf-8"
    }
    
    # We only send one notification for the most critical top alert
    top_alert = alerts[0]
    payload = {
        "app_id": app_id,
        "include_player_ids": list(devices),
        "headings": {"en": f"Market Alert: {top_alert.get('event', 'High Impact Event')}"},
        "contents": {"en": f"Confidence: {top_alert.get('probability')}% | Impact: {top_alert.get('impact_direction')} on {', '.join(top_alert.get('stocks', []))}"},
        "data": {"alert_id": top_alert.get('id')}
    }
    
    try:
        req = requests.post("https://onesignal.com/api/v1/notifications", headers=headers, json=payload, timeout=10)
        print(f"DEBUG: OneSignal push sent. Response: {req.status_code} {req.text}")
    except Exception as e:
        print(f"ERROR: Failed to send OneSignal push: {e}")

# Global State
cached_alerts = load_alerts()
processed_links = load_processed()
registered_devices = load_devices()
analysis_lock = asyncio.Lock()

async def run_analysis(source="AUTOMATED"):
    global cached_alerts
    global processed_links
    async with analysis_lock:
        print("\n" + "="*50)
        print(f"STARTING {source} ALPHA IMPACT ANALYSIS")
        print("="*50)
        try:
            today = datetime.datetime.now().date()
            print(f"DEBUG: Today's date: {today}")
            
            # Fetch headlines concurrently
            results = await asyncio.gather(
                fetch_news_api_headlines(),
                fetch_news_data_headlines(),
                fetch_hacker_news_headlines(),
                fetch_social_media_headlines(),
                return_exceptions=True
            )
            
            # RSS headlines (separate thread)
            loop = asyncio.get_event_loop()
            rss_headlines = await loop.run_in_executor(None, fetch_latest_headlines)
            
            headlines = rss_headlines
            for res in results:
                if isinstance(res, list):
                    headlines.extend(res)
                else:
                    print(f"ERROR: Source failed: {res}")
            
            # 72-hour window
            live_headlines = []
            three_days_ago = today - datetime.timedelta(days=2)
            for h in headlines:
                try:
                    pub_dt = date_parser.parse(h['published'])
                    if pub_dt.date() >= three_days_ago:
                        live_headlines.append(h)
                except:
                    live_headlines.append(h)

            new_headlines = [h for h in live_headlines if h['link'] not in processed_links]
            
            # Backup for empty cache
            if not new_headlines and source == "USER REQUESTED" and not cached_alerts:
                print("DEBUG: Empty cache. Forcing re-analysis of top 5 items.")
                new_headlines = live_headlines[:5]

            print(f"DEBUG: {len(new_headlines)} fresh items for analysis.")
            
            if not new_headlines:
                print("DEBUG: All processed. Skipping AI run.")
                print("="*50 + "\n")
                return

            candidates = await identify_high_impact_events(new_headlines[:20]) 
            final_alerts = []
            
            for candidate in candidates:
                # The AI already confirmed in Pass 1 this impacts stocks. We now do a full article Deep Dive on ALL of them.
                print(f"  --> DEEP DIVE: {candidate['event']}")
                full_text = await fetch_article_content(candidate['link'])
                deep_report = await perform_deep_analysis(full_text, candidate['event'])
                if deep_report:
                    candidate.update(deep_report)
                
                candidate['timestamp'] = candidate.get('published', datetime.datetime.now().isoformat())
                candidate['article_summary'] = candidate.get('article_summary', candidate.get('reason', ''))
                
                # Include all valid events that the AI identified as having an impact, regardless of the exact probability percentage.
                final_alerts.append(candidate)

            # Update Processed Links
            for h in new_headlines[:20]:
                processed_links.add(h['link'])
            save_processed(processed_links)

            if final_alerts:
                cached_alerts = final_alerts + cached_alerts
                cached_alerts = cached_alerts[:100]
                save_alerts(cached_alerts)
                print(f"SUCCESS: Added {len(final_alerts)} alerts.")
                send_onesignal_notification(final_alerts, registered_devices)
            else:
                print("DEBUG: No impact detected.")
                
        except Exception as e:
            print(f"ERROR: {e}")
        print("="*50 + "\n")

async def background_scheduler():
    await asyncio.sleep(5)
    while True:
        await run_analysis(source="AUTOMATED")
        await asyncio.sleep(60) # Run every minute continuously

async def self_ping():
    # Ping the health endpoint every 10 minutes to prevent Render free-tier from sleeping
    await asyncio.sleep(10)
    while True:
        try:
            port = int(os.environ.get("PORT", 8000))
            # Assume running on localhost for the ping
            url = f"http://localhost:{port}/health"
            # It's better to use the Render external URL if available, but localhost will keep the process active
            # If the user sets RENDER_EXTERNAL_URL env, we use that instead
            external_url = os.environ.get("RENDER_EXTERNAL_URL")
            ping_url = f"{external_url}/health" if external_url else url
            
            requests.get(ping_url, timeout=5)
            print(f"DEBUG: Self-ping successful to {ping_url}")
        except Exception as e:
            print(f"DEBUG: Self-ping failed: {e}")
        await asyncio.sleep(600)  # 10 minutes

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(background_scheduler())
    asyncio.create_task(self_ping())

@app.get("/")
async def root():
    return {"message": "ALPHA IMPACT API is running"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/alerts")
async def get_alerts():
    print(f"DEBUG: Returning {len(cached_alerts)} alerts")
    return cached_alerts

class DeviceRequest(BaseModel):
    player_id: str

@app.post("/register_device")
async def register_device(req: DeviceRequest):
    global registered_devices
    if req.player_id and req.player_id not in registered_devices:
        registered_devices.add(req.player_id)
        save_devices(registered_devices)
        print(f"DEBUG: Registered new device. Total devices: {len(registered_devices)}")
    return {"status": "ok"}

@app.post("/refresh")
async def refresh_alerts(background_tasks: BackgroundTasks):
    print("\nRECEIVED REFRESH REQUEST")
    if analysis_lock.locked():
        raise HTTPException(status_code=429, detail="Analysis already in progress. Please wait.")
    background_tasks.add_task(run_analysis, source="USER REQUESTED")
    return {"status": "Analysis started"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

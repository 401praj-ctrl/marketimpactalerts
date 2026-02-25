import sys
import os
import json
import asyncio
import datetime
import uvicorn
import requests
import httpx
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
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
from services.ai_service import identify_high_impact_events, perform_deep_analysis, start_new_cycle
from services.scraper_service import fetch_article_content
from services.prediction_tracker import tracker
from services.regime_service import regime_service
from services.price_service import price_service

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
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
ALERTS_FILE = os.path.join(DATA_DIR, "cached_alerts.json")
PROCESSED_FILE = os.path.join(DATA_DIR, "processed_links.json")
DEVICES_FILE = os.path.join(DATA_DIR, "devices.json")
LAST_RUN_FILE = os.path.join(DATA_DIR, "last_run_time.json")
CONFIG_FILE = os.path.join(DATA_DIR, "app_config.json")

# Ensure DATA_DIR exists
os.makedirs(DATA_DIR, exist_ok=True)

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
    if not alerts:
        return
    app_id = "7087a2bc-e285-49a9-a404-15be244a893f"
    api_key = os.environ.get("ONESIGNAL_REST_API_KEY", "").strip()
    if not api_key:
        print("ERROR: ONESIGNAL_REST_API_KEY is not set. Cannot send push notifications.")
        return

    # Debug: Confirm key presence without exposing it
    key_hint = f"...{api_key[-4:]}" if len(api_key) > 4 else "too-short"
    print(f"DEBUG: Attempting OneSignal push with key length {len(api_key)} (Hint: {key_hint})")

    headers = {
        "Authorization": f"Basic {api_key}",
        "Content-Type": "application/json; charset=utf-8"
    }
    
    # We only send one notification for the most critical top alert
    top_alert = alerts[0]
    # Target ALL users who have installed and enabled notifications
    payload = {
        "app_id": app_id,
        "included_segments": ["Total Subscriptions"],
        "headings": {"en": f"Market Alert: {top_alert.get('event', 'High Impact Event')}"},
        "contents": {"en": f"Confidence: {top_alert.get('probability')}% | Impact: {top_alert.get('impact_direction')} on {', '.join(top_alert.get('stocks', []))}"},
        "data": {"alert_id": top_alert.get('id')}
    }
    
    try:
        req = requests.post("https://onesignal.com/api/v1/notifications", headers=headers, json=payload, timeout=10)
        print(f"DEBUG: OneSignal push sent. Response: {req.status_code} {req.text}")
    except Exception as e:
        print(f"ERROR: Failed to send OneSignal push: {e}")

def load_last_run_time():
    if os.path.exists(LAST_RUN_FILE):
        try:
            with open(LAST_RUN_FILE, "r") as f:
                data = json.load(f)
                return data.get("last_run_time")
        except:
            pass
    # Default to 2 hours ago if no record exists
    return (datetime.datetime.now() - datetime.timedelta(hours=2)).isoformat()

def save_last_run_time(iso_time):
    try:
        with open(LAST_RUN_FILE, "w") as f:
            json.dump({"last_run_time": iso_time}, f)
    except Exception as e:
        print(f"ERROR saving last run time: {e}")

def get_ist_now():
    """Returns the current naive datetime in IST (UTC+5:30)."""
    return datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)

def parse_published_date(date_str):
    if not date_str: return None
    try:
        # First attempt basic ISO parsing if it's strictly formatted
        if "T" in date_str:
            try:
                # Handle cases like 2026-02-21T12:34:56.123Z
                clean_date = date_str.replace("Z", "+00:00")
                return datetime.datetime.fromisoformat(clean_date).replace(tzinfo=None)
            except: pass

        # Use dateutil.parser for maximum robustness (handles "Tue, 21 Feb 2026 ...")
        from dateutil import parser as d_parser
        dt = d_parser.parse(date_str)
        
        # ENSURE NAIVE: Strip timezone before any comparison or return
        if dt.tzinfo:
            dt = dt.replace(tzinfo=None)
            
        # If the date is surprisingly in the future (some feeds have bad clocks), cap it at now
        now = get_ist_now()
        if dt > now + datetime.timedelta(hours=24):
            return now
        return dt
    except Exception as e:
        print(f"DEBUG: Failed to parse date '{date_str}': {e}")
        return None

def migrate_legacy_alerts():
    """Converts any non-ISO timestamps in cached_alerts.json to ISO."""
    global cached_alerts
    changed = False
    print(f"DEBUG: Starting legacy alert migration for {len(cached_alerts)} items...")
    
    for alert in cached_alerts:
        ts = alert.get('timestamp', '')
        # Check if it looks like a standardized ISO already (YYYY-MM-DDTHH...)
        if not (isinstance(ts, str) and len(ts) >= 19 and ts[4] == '-' and ts[7] == '-' and 'T' in ts):
            print(f"  --> Migrating timestamp: {ts}")
            parsed = parse_published_date(ts)
            if parsed:
                alert['timestamp'] = parsed.isoformat()
                changed = True
            else:
                # Fallback to now if unparseable
                alert['timestamp'] = get_ist_now().isoformat()
                changed = True
    
    if changed:
        print("DEBUG: Migration complete. Saving sanitized alerts.")
        save_alerts(cached_alerts)
    else:
        print("DEBUG: No migration needed.")

# Global State
cached_alerts = [a for a in load_alerts() if a.get("probability", 0) >= 50]
processed_links = load_processed()
registered_devices = load_devices()
last_search_end = load_last_run_time()
analysis_lock = asyncio.Lock()

async def run_analysis(source="AUTOMATED"):
    global cached_alerts
    global processed_links
    global last_search_end
    async with analysis_lock:
        start_new_cycle()
        # Regime Update
        await regime_service.update_regime()
        current_regime = regime_service.get_regime()
        
        print("\n" + "="*50)
        print(f"STARTING {source} ALPHA IMPACT ANALYSIS")
        print(f"WINDOW START: {last_search_end} | REGIME: {current_regime}")
        print("="*50)
        try:
            start_time = datetime.datetime.now()
            today = start_time.date()
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
            
            # --- GAPLESS FILTERING ---
            # Filter headlines by timestamp (Only keep news since last_search_end)
            try:
                window_start = datetime.datetime.fromisoformat(last_search_end)
                fresh_headlines = []
                for h in headlines:
                    h_date = parse_published_date(h.get("published"))
                    # If date parsing fails or it's newer than window_start, keep it
                    if not h_date or h_date > window_start:
                        fresh_headlines.append(h)
                
                print(f"Gapless Filter: Kept {len(fresh_headlines)} / {len(headlines)} headlines (Window Start: {last_search_end})")
                headlines = fresh_headlines
            except Exception as e:
                print(f"Warning: Gapless filtering failed: {e}")
            
            # Remove duplicates by link
            unique_headlines = []
            seen_links = set()
            for h in headlines:
                if h['link'] not in seen_links:
                    unique_headlines.append(h)
                    seen_links.add(h['link'])
            headlines = unique_headlines
            print(f"DEBUG: {len(headlines)} unique headlines after deduplication.")

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
                print(f"DEBUG: Auto-Scanner activated at {datetime.datetime.now().time()} but found 0 new headlines.")
                print("DEBUG: All articles already processed. Skipping AI run.")
                print("="*50 + "\n")
                return # Keep the return here to prevent unnecessary AI calls

            # IMMEDIATELY mark as processed to prevent race conditions during long AI runs
            print(f"DEBUG: Pre-emptively marking {len(new_headlines)} headlines as processed.")
            for h in new_headlines:
                processed_links.add(h['link'])
            save_processed(processed_links)

            # PHASE 1: INDIVIDUAL STREAMING FOR HIGH-IMPACT ALERTS
            # To reduce latency, we process each headline and notify IMMEDIATELY if high confidence
            print(f"DEBUG: Starting real-time analysis loop for {len(new_headlines)} items.")
            
            final_alerts = []
            
            for i, h in enumerate(new_headlines):
                try:
                    print(f"  [{i+1}/{len(new_headlines)}] Analyzing: {h['title'][:60]}...")
                    
                    # Pass 1: Quick AI check
                    analysis = await analyze_headline(h['title'], regime=current_regime)
                    if analysis.get('impact', '').lower() == "no impact":
                        continue
                    
                    # Tag metadata
                    analysis['id'] = h['link']
                    analysis['link'] = h['link']
                    analysis['published'] = h['published']
                    
                    # Ensure event title exists
                    if not analysis.get('event') or analysis.get('event') == "None":
                        analysis['event'] = analysis.get('article_summary', h['title'][:60])
                    
                    # Probability >= 50% threshold for deep dive
                    prob = analysis.get("probability", 0)
                    if prob < 50:
                        continue
                        
                    print(f"    --> Candidate found (Prob: {prob}%). Performing DEEP DIVE...")
                    
                    # Pass 2: Deep Dive with Live Prices
                    current_prices = {}
                    for symbol in analysis.get('stocks', []):
                        price = await price_service.get_live_price(symbol)
                        if price:
                            current_prices[symbol] = price
                    
                    full_text = await fetch_article_content(h['link'])
                    deep_report = await perform_deep_analysis(full_text, analysis['event'], regime=current_regime, current_prices=current_prices)
                    
                    if deep_report:
                        analysis.update(deep_report)
                    
                    # Ensure live price / currency is set
                    if not analysis.get('live_price') and current_prices:
                        first_symbol = analysis.get('stocks', [None])[0]
                        if first_symbol and first_symbol in current_prices:
                            analysis['live_price'] = current_prices[first_symbol]
                            analysis['currency'] = price_service.get_currency_for_symbol(first_symbol)
                    
                    # Logic: Robust price fallback for missed stock or impact prices
                    if analysis.get('live_price') and not analysis.get('predicted_price'):
                        try:
                            lp = float(analysis['live_price'])
                            p = float(analysis.get('probability', 60))
                            direction = analysis.get('impact_direction', 'NEUTRAL').lower()
                            move_factor = (p / 1000.0) 
                            if direction == 'up':
                                analysis['predicted_price'] = round(lp * (1 + move_factor), 2)
                            elif direction == 'down':
                                analysis['predicted_price'] = round(lp * (1 - move_factor), 2)
                            if analysis.get('predicted_price'):
                                print(f"      [FALLBACK] Predicted Price: {analysis['predicted_price']}")
                        except: pass

                    # Standardize timestamp
                    raw_time = analysis.get('published', get_ist_now().isoformat())
                    parsed_dt = parse_published_date(raw_time)
                    analysis['timestamp'] = parsed_dt.isoformat() if parsed_dt else get_ist_now().isoformat()
                    analysis['article_summary'] = analysis.get('article_summary', analysis.get('reason', ''))
                    
                    # LOGGING & SAVING
                    tracker.save_prediction(analysis)
                    final_alerts.append(analysis)
                    
                    # STREAMING LOGIC: If prob >= 70, NOTIFY IMMEDIATELY
                    if analysis.get('probability', 0) >= 70:
                        print(f"      >>> [STREAMING] High confidence alert ({analysis['probability']}%). Notifying users NOW!")
                        
                        # Add to global cache immediately so it's visible on next /alerts call
                        combined = [analysis] + cached_alerts
                        cached_alerts = [a for a in combined if a.get("probability", 0) >= 50]
                        cached_alerts = cached_alerts[:100]
                        save_alerts(cached_alerts)
                        
                        # Trigger OneSignal for this single alert
                        send_onesignal_notification([analysis], registered_devices)
                        
                except Exception as e:
                    print(f"  ERROR processing '{h.get('title')[:30]}': {e}")
                    continue

            # FINAL BATCH UPDATE (For lower priority items or cleanup)
            if final_alerts:
                final_alerts.sort(key=lambda x: x.get("probability", 0), reverse=True)
                combined = final_alerts + cached_alerts
                # Remove duplicates by ID (link)
                seen_ids = set()
                deduped = []
                for a in combined:
                    if a.get('id') not in seen_ids:
                        deduped.append(a)
                        seen_ids.add(a.get('id'))
                
                cached_alerts = [a for a in deduped if a.get("probability", 0) >= 50]
                cached_alerts = cached_alerts[:100]
                save_alerts(cached_alerts)
                
                # If we had a cluster of 50-69% alerts and no 70+ was sent, optionally notify here
                # (Optional: Only notify batch if no streamed notification was sent to avoid spam)
            else:
                print("DEBUG: Cycle complete. No new alerts detected.")
            
            save_last_run_time(last_search_end)
                
        except Exception as e:
            import traceback
            print(f"ERROR: {e}")
            traceback.print_exc()
        print("="*50 + "\n")

async def background_scheduler():
    await asyncio.sleep(5)
    print("DEBUG: background_scheduler initialized and waiting for intervals.")
    while True:
        try:
            print(f"DEBUG: background_scheduler triggering AUTOMATED analysis at {datetime.datetime.now()}")
            await run_analysis(source="AUTOMATED")
            # Also refresh prices for existing alerts periodicly
            await refresh_cached_prices()
        except Exception as e:
            print(f"ERROR: background_scheduler caught exception: {e}")
        print("DEBUG: background_scheduler sleeping for 120 minutes...")
        await asyncio.sleep(7200) # Run every 120 minutes (2 hours) as requested

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
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.get(ping_url)
            print(f"DEBUG: Self-ping successful to {ping_url}")
        except Exception as e:
            print(f"DEBUG: Self-ping failed: {e}")
        await asyncio.sleep(600)  # 10 minutes

# Keep strong references to background tasks to prevent garbage collection
background_tasks_set = set()

@app.on_event("startup")
async def startup_event():
    # 1. Clean up any existing alert timestamps
    migrate_legacy_alerts()
    
    # 2. Ensure all high-impact alerts are in the prediction log for the tracker.
    # This helps recover the dashboard if the stats file was lost but cache exists.
    for alert in cached_alerts:
        tracker.save_prediction(alert, silent=True) # Add silent mode to skip extra saves

    # 3. Trigger an initial price refresh for existing alerts
    asyncio.create_task(refresh_cached_prices())

    task1 = asyncio.create_task(background_scheduler())
    background_tasks_set.add(task1)
    task2 = asyncio.create_task(self_ping())
    background_tasks_set.add(task2)
    task3 = asyncio.create_task(automated_verification_job())
    background_tasks_set.add(task3)

async def automated_verification_job():
    """
    Background job that runs every 6 hours to verify past predictions.
    """
    await asyncio.sleep(60) # Wait 1 minute after startup
    print("DEBUG: automated_verification_job initialized.")
    while True:
        try:
            print(f"DEBUG: automated_verification_job starting check at {datetime.datetime.now()}")
            await tracker.run_cleanup_and_verification()
        except Exception as e:
            print(f"ERROR: automated_verification_job caught exception: {e}")
        
        # Run every 6 hours
        await asyncio.sleep(21600)

@app.get("/")
async def root():
    return {"message": "ALPHA IMPACT API is running"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/status")
async def get_status():
    return {
        "is_analyzing": analysis_lock.locked(),
        "last_run_time": last_search_end
    }

@app.get("/alerts")
async def get_alerts():
    print(f"DEBUG: Returning {len(cached_alerts)} alerts")
    return cached_alerts

@app.get("/stats")
async def get_prediction_stats():
    return tracker.get_stats()

class DeviceRequest(BaseModel):
    player_id: str

@app.get("/app/version")
async def get_app_version():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                return config
        except:
            pass
    return {"latest_version": "1.0.0", "download_url": "", "release_notes": ""}

@app.get("/app/download")
async def download_apk():
    apk_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "app-release.apk")
    if os.path.exists(apk_path):
        return FileResponse(apk_path, media_type='application/vnd.android.package-archive', filename="market-impact-v1.2.1.apk")
    return {"error": "APK file not found on server. Please ensure data/app-release.apk exists."}

@app.post("/register_device")
async def register_device(req: DeviceRequest):
    global registered_devices
    if req.player_id and req.player_id not in registered_devices:
        registered_devices.add(req.player_id)
        save_devices(registered_devices)
        print(f"DEBUG: Registered new device. Total devices: {len(registered_devices)}")
    return {"status": "ok"}

@app.post("/verify")
async def trigger_verification(background_tasks: BackgroundTasks):
    print("\nRECEIVED MANUAL VERIFICATION REQUEST")
    
    # Check if analysis is already running
    if analysis_lock.locked():
        print("DEBUG: Analysis already running in background.")
        return {"status": "Analysis already running. Please wait."}
        
    background_tasks.add_task(tracker.run_cleanup_and_verification, source="manual")
    return {"status": "Manual verification analysis started."}

@app.post("/broadcast_update")
async def trigger_update_broadcast():
    """
    Manually triggers a OneSignal notification to all users about the new app update.
    Uses the server's ONESIGNAL_REST_API_KEY.
    """
    app_id = "7087a2bc-e285-49a9-a404-15be244a893f"
    api_key = os.environ.get("ONESIGNAL_REST_API_KEY", "").strip()
    if not api_key:
        print("ERROR: ONESIGNAL_REST_API_KEY not set on server")
        return {"error": "ONESIGNAL_REST_API_KEY not set on server"}
        
    headers = {
        "Authorization": f"Basic {api_key}",
        "Content-Type": "application/json; charset=utf-8"
    }
    
    payload = {
        "app_id": app_id,
        "included_segments": ["Total Subscriptions"],
        "headings": {"en": "💎 Premium Upgrade Ready"},
        "contents": {"en": "Experience the all-new Alpha Impact with real-time speed and premium UI. Tap to update!"},
        "data": {"type": "update", "version": "1.2.14+20"}
    }
    
    try:
        response = requests.post("https://onesignal.com/api/v1/notifications", headers=headers, json=payload, timeout=10)
        print(f"DEBUG: Broadcast update response: {response.status_code} - {response.text}")
        return {"status": "broadcast notification sent", "onesignal_status": response.status_code}
    except Exception as e:
        print(f"ERROR: Failed to broadcast update: {e}")
        return {"error": str(e)}

@app.post("/refresh")
async def refresh_alerts(background_tasks: BackgroundTasks):
    print("\nRECEIVED REFRESH REQUEST")
    
    # Instead of wiping the cache entirely (which forces a 5-minute re-analysis of old news),
    # we just trigger run_analysis. It will already filter out processed links.
    # ONLY clear cache if the user specifies a full wipe, but standard refresh shouldn't.
    print("DEBUG: Standard refresh requested. Reusing processed_links. Only fetching new items.")
    
    if analysis_lock.locked():
        print("DEBUG: Analysis already running in background.")
        return {"status": "Analysis already running."}
        
    background_tasks.add_task(run_analysis, source="USER REQUESTED")
    # Also refresh existing alert prices immediately for the user
    background_tasks.add_task(refresh_cached_prices)
    return {"status": "Analysis started. Checking for new events and refreshing old prices."}

async def refresh_cached_prices():
    """
    Iterates through cached_alerts and fetches the latest Finnhub price for each.
    Tries multiple symbols if the first one fails.
    """
    print(f"DEBUG: Refreshing prices for {len(cached_alerts)} cached alerts...")
    updated_any = False
    # Refresh all cached alerts to be thorough
    for alert in cached_alerts:
        symbols = alert.get('stocks', [])
        if not symbols: continue
        
        current_p = alert.get('live_price')
        new_p = None
        
        # Try each symbol until one works
        for symbol in symbols:
            try:
                price = await price_service.get_live_price(symbol)
                if price:
                    new_p = price
                    break
            except:
                continue
        
        if new_p:
            # Update if it was missing or has changed
            if current_p is None or abs(new_p - float(current_p)) > 0.001:
                alert['live_price'] = new_p
                # Always update currency when price is refreshed
                alert['currency'] = price_service.get_currency_for_symbol(symbol)
                
                # Re-calculate upside OR calculate fallback predicted_price if missing
                if alert.get('predicted_price'):
                    try:
                        pred = float(alert['predicted_price'])
                        upside = ((pred / new_p) - 1) * 100
                        alert['upside_pct'] = f"{upside:+.2f}%"
                    except: pass
                else:
                    # FALLBACK Logic: If no predicted price, calculate one based on probability
                    try:
                        lp = float(new_p)
                        prob = float(alert.get('probability', 60))
                        direction = alert.get('impact_direction', 'NEUTRAL').lower()
                        move_factor = (prob / 1000.0)
                        if direction == 'up':
                            alert['predicted_price'] = round(lp * (1 + move_factor), 2)
                        elif direction == 'down':
                            alert['predicted_price'] = round(lp * (1 - move_factor), 2)
                        
                        if alert.get('predicted_price'):
                            pred = float(alert['predicted_price'])
                            upside = ((pred / new_p) - 1) * 100
                            alert['upside_pct'] = f"{upside:+.2f}%"
                    except: pass
                updated_any = True
            
    if updated_any:
        save_alerts(cached_alerts)
        print("DEBUG: Cached alert prices updated and saved.")
    else:
        print("DEBUG: No price updates needed or all fetches failed.")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

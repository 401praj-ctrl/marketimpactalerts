import sys
# Deploy Trigger: Angel One Hardening and Bytez Fallback v1.0.1
import os
import json
import asyncio
import datetime
import re
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
from services.ai_service import identify_high_impact_events, perform_deep_analysis, start_new_cycle, analyze_headline
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
    
    # Pre-processing: Translate foreign date parts to English
    # This handles errors like "ven., 27 févr. 2026" or "Cum, 27 Şub 2026"
    import re
    foreign_to_english = {
        # French
        'janv': 'Jan', 'févr': 'Feb', 'mars': 'Mar', 'avr': 'Apr',
        'mai': 'May', 'juin': 'Jun', 'juill': 'Jul', 'août': 'Aug',
        'sept': 'Sep', 'oct': 'Oct', 'nov': 'Nov', 'déc': 'Dec',
        'janvier': 'Jan', 'février': 'Feb', 'avril': 'Apr',
        'juillet': 'Jul', 'septembre': 'Sep', 'octobre': 'Oct',
        'novembre': 'Nov', 'décembre': 'Dec',
        'lun': 'Mon', 'mar': 'Tue', 'mer': 'Wed', 'jeu': 'Thu',
        'ven': 'Fri', 'sam': 'Sat', 'dim': 'Sun',
        'lundi': 'Mon', 'mardi': 'Tue', 'mercredi': 'Wed',
        'jeudi': 'Thu', 'vendredi': 'Fri', 'samedi': 'Sat',
        'dimanche': 'Sun',
        
        # Turkish
        'oca': 'Jan', 'şub': 'Feb', 'mar': 'Mar', 'nis': 'Apr',
        'may': 'May', 'haz': 'Jun', 'tem': 'Jul', 'ağu': 'Aug',
        'eyl': 'Sep', 'eki': 'Oct', 'kas': 'Nov', 'ara': 'Dec',
        'ocak': 'Jan', 'şubat': 'Feb', 'mart': 'Mar', 'nisan': 'Apr',
        'mayıs': 'May', 'haziran': 'Jun', 'temmuz': 'Jul', 'ağustos': 'Aug',
        'eylül': 'Sep', 'ekim': 'Oct', 'kasım': 'Nov', 'aralık': 'Dec',
        'pzt': 'Mon', 'sal': 'Tue', 'çar': 'Wed', 'per': 'Thu',
        'cum': 'Fri', 'cmt': 'Sat', 'paz': 'Sun',
        'pazartesi': 'Mon', 'salı': 'Tue', 'çarşamba': 'Wed',
        'perşembe': 'Thu', 'cuma': 'Fri', 'cumartesi': 'Sat', 'pazar': 'Sun'
    }
    
    clean_date_str = date_str
    if any(foreign in date_str.lower() for foreign in foreign_to_english.keys()):
        for foreign, en in foreign_to_english.items():
            pattern = re.compile(rf'\b{foreign}\b\.?', re.IGNORECASE)
            clean_date_str = pattern.sub(en, clean_date_str)

    try:
        # First attempt basic ISO parsing if it's strictly formatted
        if "T" in clean_date_str:
            try:
                # Handle cases like 2026-02-21T12:34:56.123Z
                iso_clean = clean_date_str.replace("Z", "+00:00")
                return datetime.datetime.fromisoformat(iso_clean).replace(tzinfo=None)
            except: pass

        # Use dateutil.parser for maximum robustness (handles "Tue, 21 Feb 2026 ...")
        from dateutil import parser as d_parser
        dt = d_parser.parse(clean_date_str)
        
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

def convert_relative_to_actual_date(relative_str, base_date_str, force_single=False):
    """
    Converts 'T+0 to T+2', 'today', 'tomorrow', or '03/03' style strings into actual YYYY-MM-DD dates 
    based on the provided base_date_str (ISO format).
    If force_single is True, collapses date ranges to their start date.
    """
    if not relative_str or not isinstance(relative_str, str):
        return relative_str
        
    try:
        base_dt = datetime.datetime.fromisoformat(base_date_str)
    except:
        base_dt = get_ist_now()

    # 1. Handle "Today" and "Tomorrow"
    low_s = relative_str.lower()
    if "today" in low_s:
        return base_dt.strftime("%Y-%m-%d")
    if "tomorrow" in low_s:
        return (base_dt + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    # 2. Handle "MM/DD" or "DD/MM" (heuristic: if it's 2026-X-Y in the future)
    date_match = re.search(r'(\d{1,2})[/\-](\d{1,2})', relative_str)
    if date_match:
        try:
            d1, d2 = int(date_match.group(1)), int(date_match.group(2))
            # Assume 2026 as per user screenshots
            current_year = 2026 
            # Try MM/DD first (standard for many AI models)
            test_dt = datetime.datetime(current_year, d1, d2)
            if test_dt.date() >= base_dt.date():
                return test_dt.strftime("%Y-%m-%d")
            # Try DD/MM if MM/DD failed or was in the past
            test_dt = datetime.datetime(current_year, d2, d1)
            return test_dt.strftime("%Y-%m-%d")
        except: pass

    def replace_tn(match):
        try:
            days = int(match.group(1))
            target_date = base_dt + datetime.timedelta(days=days)
            return target_date.strftime("%Y-%m-%d")
        except: return match.group(0)

    # 3. Handle T+N (case-insensitive match)
    if "t+" in low_s:
        result = re.sub(r'T\+(\d+)', replace_tn, relative_str, flags=re.IGNORECASE)
        # GLOBAL EXACT DATE POLICY FOR DIRECT: If result is a range (e.g. "2026-03-02 to 2026-03-04"), 
        # collapse it ONLY if force_single is True (Tier-1/Direct). Otherwise leave the range intact.
        if force_single and " to " in result:
            result = result.split(" to ")[0]
        return result
        
    return relative_str

def migrate_legacy_alerts():
    """Converts any non-ISO timestamps or old price formats in cached_alerts.json."""
    global cached_alerts
    changed = False
    print(f"DEBUG: Starting legacy alert migration for {len(cached_alerts)} items...")
    
    for alert in cached_alerts:
        # 1. Timestamp Migration
        ts = alert.get('timestamp', '')
        if not (isinstance(ts, str) and len(ts) >= 19 and ts[4] == '-' and ts[7] == '-' and 'T' in ts):
            print(f"  --> Migrating timestamp: {ts}")
            parsed = parse_published_date(ts)
            if parsed:
                alert['timestamp'] = parsed.isoformat()
                changed = True
            else:
                alert['timestamp'] = get_ist_now().isoformat()
                changed = True

        # 2. Impact Date Migration (T+N to Actual)
        impact_date = alert.get('impact_date_est', '')
        if impact_date:
            impact_date_str = str(impact_date)
            
            # Case A: T+N formatting
            if "T+" in impact_date_str.upper():
                print(f"  --> Migrating relative impact date: {impact_date}")
                alert['impact_date_est'] = convert_relative_to_actual_date(impact_date_str, alert.get('timestamp'))
                changed = True

        # 3. Price Schema Migration (Flat to Map)
        if 'live_price' in alert and 'stock_prices' not in alert:
            print(f"  --> Migrating price schema for: {alert.get('event')}")
            stocks = alert.get('stocks', [])
            stock_prices = {}
            for s in stocks:
                stock_prices[s] = {
                    "live": alert.get('live_price'),
                    "predicted": alert.get('predicted_price'),
                    "upside": alert.get('upside_pct')
                }
            alert['stock_prices'] = stock_prices
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
verification_lock = asyncio.Lock()

def is_financial_news(title: str) -> bool:
    """Fast keyword filter to skip obviously irrelevant news."""
    keywords = [
        "stock", "market", "ipo", "profit", "loss", "revenue", "earnings",
        "dividend", "acquisition", "merger", "shares", "fed", "rbi",
        "inflation", "economy", "growth", "bank", "tech", "ai", "layoff",
        "hiring", "deal", "contract", "price", "quarter", "fiscal",
        "trade", "tariff", "rate", "index", "nifty", "sensex", "nasdaq"
    ]
    title_lower = title.lower()
    return any(k in title_lower for k in keywords)

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
            start_time = get_ist_now()
            today = start_time.date()
            print(f"DEBUG: Today's date: {today}")
            
            # --- DAILY CACHE RESET ---
            # Check if the day has changed since the last run
            last_run_date_str = last_search_end.split('T')[0] if 'T' in last_search_end else ""
            if last_run_date_str and last_run_date_str != today.isoformat():
                print(f"DEBUG: [DAILY RESET] New day detected ({today}). Clearing processed links cache.")
                processed_links = set()
                # Also reset the search window to start of today IST
                last_search_end = today.isoformat() + "T00:00:00"
                save_processed(processed_links)
                save_last_run_time(last_search_end)
            
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

            # --- TODAY ONLY FILTER ---
            # Strictly only process news from the current day (IST)
            live_headlines = []
            for h in headlines:
                try:
                    pub_dt = parse_published_date(h.get('published'))
                    if pub_dt and pub_dt.date() == today:
                        live_headlines.append(h)
                    else:
                        # Skip yesterday's news as requested
                        pass
                except:
                    # If date is unparseable but we're in a fresh cycle, might be brand new
                    live_headlines.append(h)

            print(f"DEBUG: Filtered {len(live_headlines)} headlines from today's date ({today}).")
            new_headlines = [h for h in live_headlines if h['link'] not in processed_links]
            
            # Backup for empty cache
            if not new_headlines and source == "USER REQUESTED" and not cached_alerts:
                print("DEBUG: Empty cache. Forcing re-analysis of top 5 items.")
                new_headlines = live_headlines[:5]

            print(f"DEBUG: {len(new_headlines)} fresh items for analysis.")
            
            if not new_headlines:
                print(f"DEBUG: [NEWS] Auto-Scanner at {get_ist_now().strftime('%H:%M:%S')} found 0 new headlines.")
                print("DEBUG: [NEWS] All articles already processed. Skipping AI run.")
                print("="*50 + "\n")
                return 

            # IMMEDIATELY mark as processed to prevent race conditions during long AI runs
            print(f"DEBUG: Pre-emptively marking {len(new_headlines)} headlines as processed.")
            for h in new_headlines:
                processed_links.add(h['link'])
            save_processed(processed_links)

            # PHASE 1: INDIVIDUAL STREAMING FOR HIGH-IMPACT ALERTS
            # To reduce latency, we process each headline and notify IMMEDIATELY if high confidence
            print(f"DEBUG: Starting real-time analysis loop for {len(new_headlines)} items.")
            
            registered_devices = load_devices()
            final_alerts = []
            
            for i, h in enumerate(new_headlines):
                try:
                    await asyncio.sleep(0.1) # Yield to event loop to keep server alive
                    print(f"  [{i+1}/{len(new_headlines)}] Analyzing: {h['title'][:60]}...")
                    
                    # Pass 0: Fast keyword filter
                    if not is_financial_news(h['title']):
                        print(f"    --> [SKIP] Non-financial headline.")
                        continue

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
                    full_text = await fetch_article_content(h['link'])
                    deep_report = await perform_deep_analysis(full_text, analysis['event'], regime=current_regime)
                    if deep_report:
                        analysis.update(deep_report)

                    # --- MULTI-STOCK PRICING LOGIC ---
                    stocks = analysis.get('stocks', [])
                    stock_prices = {}
                    
                    for symbol in stocks:
                        try:
                            lp = await price_service.get_live_price(symbol)
                            if not lp:
                                stock_prices[symbol] = {"live": None, "predicted": None, "upside": None}
                                continue

                            # Calculate individual predicted price for this stock
                            p = float(analysis.get('probability', 60))
                            raw_dir = str(analysis.get('impact_direction', analysis.get('direction', analysis.get('impact', 'NEUTRAL')))).lower()
                            is_up = any(x in raw_dir for x in ['up', 'positive', 'bullish', 'high', 'increase'])
                            is_down = any(x in raw_dir for x in ['down', 'negative', 'bearish', 'low', 'decrease'])
                            
                            tier = analysis.get('tier', 'Tier-3')
                            base_move = 0.01 if tier == 'Tier-1' else (0.005 if tier == 'Tier-2' else 0.002)
                            move_factor = base_move * (p / 50.0)
                            
                            pred = lp # Default to live price
                            upside = "0% (Neutral)"
                            if is_up:
                                pred = round(lp * (1 + move_factor), 2)
                                upside = f"+{(move_factor * 100):.2f}%"
                            elif is_down:
                                pred = round(lp * (1 - move_factor), 2)
                                upside = f"-{(move_factor * 100):.2f}%"
                            else:
                                # Neutral or unknown impact (Force same price to avoid empty)
                                pred = lp
                                upside = "0%"
                            
                            stock_prices[symbol] = {
                                "live": lp,
                                "predicted": pred,
                                "upside": upside
                            }
                        except Exception as pe:
                            print(f"      [ERROR] Pricing failed for {symbol}: {pe}")
                            stock_prices[symbol] = {"live": None, "predicted": None, "upside": None}

                    analysis['stock_prices'] = stock_prices
                    
                    # Legacy support for frontend fields (using the first stock's data)
                    if stocks and stocks[0] in stock_prices:
                        first = stock_prices[stocks[0]]
                        analysis['live_price'] = first['live']
                        analysis['predicted_price'] = first['predicted']
                        analysis['upside_pct'] = first['upside']

                    # Ensure currency is set based on the first stock symbol
                    if not analysis.get('currency') and stocks:
                        analysis['currency'] = price_service.get_currency_for_symbol(stocks[0])

                    # Standardize timestamp
                    raw_time = analysis.get('published', get_ist_now().isoformat())
                    parsed_dt = parse_published_date(raw_time)
                    analysis['timestamp'] = parsed_dt.isoformat() if parsed_dt else get_ist_now().isoformat()
                    # Event date should be the actual publish date, not an AI hallucinated future date.
                    analysis['event_date'] = analysis['timestamp'][:10]
                    
                    # Impact Type Mapping (Prioritize Explicit Classification from AI)
                    impact_class = str(analysis.get('impact_classification', '')).lower()
                    if 'direct' in impact_class and 'indirect' not in impact_class:
                        analysis['impact_type'] = 'Direct'
                    elif 'indirect' in impact_class:
                        analysis['impact_type'] = 'Indirect'
                    else:
                        # Fallback to Tier logic if impact_classification isn't provided correctly
                        tier = str(analysis.get('tier', 'Tier-3')).lower()
                        if 'tier-1' in tier or ('direct' in tier and 'indirect' not in tier):
                            analysis['impact_type'] = 'Direct'
                        else:
                            analysis['impact_type'] = 'Indirect'
                    
                    # Convert relative impact date (T+0 to T+2) to actual date strings
                    # We rely completely on the AI's judgment for date formats (single or range)
                    impact_date = analysis.get('impact_date_est', '')
                    analysis['impact_date_est'] = convert_relative_to_actual_date(impact_date, analysis['timestamp'])
                    
                    # Impact Description and Reasoning (UI separation)
                    if not analysis.get('impact_description'):
                        # Use reason as fallback if description is missing
                        analysis['impact_description'] = analysis.get('reason', 'Analysis pending deep-dive.')
                    
                    # Merge reasoning and summary to avoid field fragmentation
                    analysis['reason'] = analysis.get('reason', analysis.get('article_summary', ''))
                    analysis['article_summary'] = analysis['reason'] # For legacy support
                    
                    # Sanitize upside_pct if it's a dict representing multiple stocks
                    upside_val = analysis.get('upside_pct')
                    if isinstance(upside_val, dict):
                        # Extract the first available value, e.g { "NSE:TCS": "-2.63%" } -> "-2.63%"
                        if upside_val:
                            first_val = list(upside_val.values())[0]
                            analysis['upside_pct'] = str(first_val)
                        else:
                            analysis['upside_pct'] = ""
                    elif upside_val is not None:
                        analysis['upside_pct'] = str(upside_val)
                    
                    # LOGGING & SAVING
                    tracker.save_prediction(analysis)
                    final_alerts.append(analysis)
                    
                    # STREAMING LOGIC: If prob >= 50, NOTIFY IMMEDIATELY
                    if analysis.get('probability', 0) >= 50:
                        print(f"      >>> [STREAMING] New alert detected ({analysis['probability']}%). Notifying users NOW!")
                        
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
            print(f"DEBUG: background_scheduler triggering AUTOMATED analysis at {get_ist_now()}")
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
    tracker.sync_from_log()
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
    Background job that runs precisely once daily at midnight (12:00 AM) to verify past predictions.
    """
    print("DEBUG: automated_verification_job standby.")
    while True:
        try:
            # 1. Calculate time until next midnight
            now = get_ist_now()
            next_midnight = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            seconds_until_midnight = (next_midnight - now).total_seconds()
            
            print(f"DEBUG: automated_verification_job sleeping for {seconds_until_midnight:.0f}s until {next_midnight} IST")
            await asyncio.sleep(seconds_until_midnight)
            
            # 2. Run verification
            print(f"DEBUG: [VERIFY] automated_verification_job starting daily cycle at {get_ist_now()} IST")
            async with verification_lock:
                await tracker.run_cleanup_and_verification(source="auto")
            
        except Exception as e:
            print(f"ERROR: automated_verification_job caught exception: {e}")
            await asyncio.sleep(3600) # Wait an hour before retrying on error

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

@app.get("/trigger-demo")
async def trigger_demo_endpoint():
    """
    Temporary endpoint to trigger a demo high-impact alert for testing notifications.
    """
    demo_alert = {
        "id": f"demo_{int(datetime.datetime.now().timestamp())}",
        "event": "Reliance-NVIDIA AI partnership",
        "company": "Reliance Industries",
        "sector": "Technology / AI",
        "stocks": ["NSE:RELIANCE"],
        "impact": "high",
        "impact_direction": "UP",
        "impact_description": "A strategic partnership with NVIDIA positions Reliance as a leader in India's sovereign AI cloud. This move is expected to drive long-term value through cloud infrastructure and AI service subscriptions. The market sees this as a major positive catalyst.",
        "event_date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "impact_date_est": (datetime.datetime.now() + datetime.timedelta(days=2)).strftime("%Y-%m-%d"),
        "probability": 75,
        "stock_prices": {
            "NSE:RELIANCE": {
                "live": 1393.9,
                "predicted": 1414.81,
                "upside": "+1.50%"
            }
        },
        "live_price": 1393.9,
        "predicted_price": 1414.81,
        "upside_pct": "+1.50%",
        "currency": "INR",
        "tier": "Tier-1",
        "timestamp": datetime.datetime.now().isoformat(),
        "published": datetime.datetime.now().isoformat(),
        "article_summary": "Major deal between RIL and NVIDIA for India-wide AI cloud deployment.",
        "link": "https://example.com/demo-news"
    }
    
    # 1. Save to cache
    global cached_alerts
    cached_alerts = [demo_alert] + [a for a in cached_alerts if a.get('id') != demo_alert['id']]
    save_alerts(cached_alerts[:100])
    tracker.save_prediction(demo_alert)
    
    # 2. Send notification
    send_onesignal_notification([demo_alert], registered_devices)
    
    return {"status": "success", "message": "Demo alert triggered on server.", "alert": demo_alert}

@app.get("/alerts")
async def get_alerts():
    print(f"DEBUG: Returning {len(cached_alerts)} alerts")
    return cached_alerts

@app.get("/stats")
async def get_prediction_stats():
    return tracker.get_stats()

@app.get("/predictions")
async def get_prediction_history(status: str = None):
    """
    Returns history of predictions.
    status: optional filter ('correct', 'wrong', or 'all')
    """
    return tracker.get_predictions(status=status)

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
async def download_apk(v: str = None):
    # Try multiple common locations for the APK
    base_path = os.path.dirname(os.path.abspath(__file__))
    locations = [
        os.path.join(base_path, "data", "app-release.apk"),
        os.path.join(base_path, "static", "app-release.apk"),
        os.path.join(os.path.dirname(base_path), "build", "app", "outputs", "flutter-apk", "app-release.apk"),
    ]
    
    apk_path = None
    for loc in locations:
        if os.path.exists(loc):
            apk_path = loc
            break
            
    if apk_path:
        # Return a version-aware filename to prevent OS/Browser caching issues
        safe_v = str(v).replace('+', '-').replace(' ', '_') if v else "latest"
        fname = f"alpha-impact-v{safe_v}.apk"
        print(f"DEBUG: Serving APK from {apk_path} as {fname}")
        return FileResponse(apk_path, media_type='application/vnd.android.package-archive', filename=fname)
        
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
    
    # Check if verification is already running
    if verification_lock.locked():
        print("DEBUG: [VERIFY] Verification already running.")
        return {"status": "Verification already running."}
        
    async def run_verify_with_lock():
        async with verification_lock:
            await tracker.run_cleanup_and_verification(source="manual")

    background_tasks.add_task(run_verify_with_lock)
    return {"status": "Manual verification analysis started."}

async def broadcast_verification_result(event_name, is_correct, move):
    """
    Sends a push notification to all users when a prediction is verified.
    """
    app_id = "7087a2bc-e285-49a9-a404-15be244a893f"
    api_key = os.environ.get("ONESIGNAL_REST_API_KEY", "").strip()
    if not api_key:
        return
        
    headers = {
        "Authorization": f"Basic {api_key}",
        "Content-Type": "application/json; charset=utf-8"
    }
    
    status_emoji = "🎯 CORRECT" if is_correct else "❌ WRONG"
    move_str = f"{move:+.2%}"
    
    payload = {
        "app_id": app_id,
        "included_segments": ["Total Subscriptions"],
        "headings": {"en": f"{status_emoji}: Alpha Impact Match"},
        "contents": {"en": f"Prediction verified for: {event_name[:50]}... Actual Move: {move_str}. View Dashboard!"},
        "data": {"type": "verification", "event": event_name, "is_correct": is_correct}
    }
    
    try:
        requests.post("https://onesignal.com/api/v1/notifications", headers=headers, json=payload, timeout=10)
    except:
        pass

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
        "data": {"type": "update", "version": "1.2.14+35"}
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
    try:
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
                # Ensure we handle non-floatable current_p correctly
                should_update = False
                if current_p is None:
                    should_update = True
                else:
                    try:
                        if abs(new_p - float(current_p)) > 0.001:
                            should_update = True
                    except (ValueError, TypeError):
                        should_update = True
                        
                if should_update:
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
    except Exception as e:
        import traceback
        print(f"ERROR in refresh_cached_prices: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

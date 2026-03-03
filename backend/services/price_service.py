import os
import json
import asyncio
import requests
import pyotp
import math
import logging
from datetime import datetime, timedelta
from SmartApi import SmartConnect
from services.search_service import search_price_online

# Suppress the extremely noisy internal SmartConnect logger for expired tokens
logging.getLogger("smartConnect").setLevel(logging.CRITICAL)
logging.getLogger("smartapi").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.WARNING)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_FILE = os.path.join(BASE_DIR, "data", "price_cache.json")
TOKEN_LIST_FILE = os.path.join(BASE_DIR, "data", "angel_tokens.json")

# Standardized to UPPERCASE to ensure reliable matching
TICKER_CORRECTIONS = {
    "BAJAJAUTO": "BAJAJ-AUTO",
    "HDFCCBANK": "HDFCBANK",
    "M&M": "M&M",
    "APL APOLLO": "APLAPOLLO",
    "ICICIBC": "ICICIBANK",
    "ADANI": "ADANIENT",
    "RELIANCEIND": "RELIANCE",
    "MARUTISUZUKI": "MARUTI",
    "TATA-STEEL": "TATASTEEL",
    "GODREJ AGROVET": "GODREJAGRO",
    "VENKEYS": "VENKYS",
    "RELIG": "RELIGARE",
    "SBI-LIFE": "SBILIFE",
    "HDFC": "HDFCBANK",
    "ICICI": "ICICIBANK",
    "ANGLONE": "ANGELONE",
    "BNAGROCHEM": "BHARATAGRI",
    "KALYANKJ": "KALYANKJIL",
    "INFOSYS": "INFY",
    "ZEEL": "ZEEL",
    "RELIANCE": "RELIANCE",
    "EXPORTS": "RELIGARE",
    # India Indices: Map to exact Angel One token names first. 
    # The YFinance/Finnhub fallbacks will convert these back to ^ prefixed symbols.
    "NIFTY 50": "NIFTY",
    "NIFTY50": "NIFTY",
    "NIFTY": "NIFTY",
    "SENSEX": "SENSEX",
    "NIFTY BANK": "BANKNIFTY",
    "BANKNIFTY": "BANKNIFTY",
    "NIFTYBANK": "BANKNIFTY",
    "MIDCPNIFTY": "MIDCPNIFTY"
}

class PriceService:
    def __init__(self):
        self.api_key = os.environ.get("ANGEL_API_KEY")
        self.user_id = os.environ.get("ANGEL_USER_ID")
        self.password = os.environ.get("ANGEL_PASSWORD")
        self.totp_key = os.environ.get("ANGEL_TOTP_KEY")
        
        self.smart_api = None
        self.token_map = {} # symbol -> token
        self.last_auth_time = None
        self.cache = self.load_price_cache()
        self.finnhub_key = os.environ.get("FINNHUB_API_KEY")
        
    def load_price_cache(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r") as f:
                    return json.load(f)
            except: pass
        return {}

    def save_price_cache(self):
        try:
            os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
            with open(CACHE_FILE, "w") as f:
                json.dump(self.cache, f)
        except: pass

    async def _ensure_token_list(self):
        if os.path.exists(TOKEN_LIST_FILE):
            file_time = datetime.fromtimestamp(os.path.getmtime(TOKEN_LIST_FILE))
            if datetime.now() - file_time < timedelta(hours=24):
                if not self.token_map:
                    with open(TOKEN_LIST_FILE, "r") as f:
                        self.token_map = json.load(f)
                return

        print("DEBUG: Downloading fresh Angel One instrument list...")
        try:
            url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
            loop = asyncio.get_event_loop()
            
            def fetch_and_parse():
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    full_list = response.json()
                    new_map = {}
                    for item in full_list:
                        exch = item.get('exch_seg')
                        if exch in ['NSE', 'BSE']:
                            symbol = item.get('symbol')
                            if symbol:
                                new_map[symbol] = {
                                    "token": item.get('token'),
                                    "exch": exch,
                                    "name": item.get('name')
                                }
                    os.makedirs(os.path.dirname(TOKEN_LIST_FILE), exist_ok=True)
                    with open(TOKEN_LIST_FILE, "w") as f:
                        json.dump(new_map, f)
                    return new_map
                else:
                    print(f"ERROR: Failed to download token list: {response.status_code}")
                    return None

            new_map = await loop.run_in_executor(None, fetch_and_parse)
            if new_map:
                self.token_map = new_map
                print(f"DEBUG: Successfully cached {len(self.token_map)} Indian tokens.")
        except Exception as e:
            print(f"ERROR: Token list download exception: {e}")

    async def authenticate(self, force=False):
        if not force and self.smart_api and self.last_auth_time:
            if datetime.now() - self.last_auth_time < timedelta(hours=10):
                return True

        # Throttle auth attempts to prevent TOTP duplicate token rate-limits
        if hasattr(self, 'last_auth_attempt') and self.last_auth_attempt:
            time_since = datetime.now() - self.last_auth_attempt
            if time_since < timedelta(seconds=35):
                wait_seconds = 35 - time_since.total_seconds()
                print(f"DEBUG: Angel auth throttled to prevent spam. Waiting {wait_seconds:.1f}s for next TOTP window.")
                await asyncio.sleep(wait_seconds)

        if not all([self.api_key, self.user_id, self.password, self.totp_key]):
            print("ERROR: Missing Angel One credentials.")
            return False

        print(f"DEBUG: Authenticating with Angel One for User: {self.user_id}...")
        self.last_auth_attempt = datetime.now()
        try:
            self.smart_api = SmartConnect(api_key=self.api_key)
            totp = pyotp.TOTP(self.totp_key.replace(" ", "")).now()
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: self.smart_api.generateSession(self.user_id, self.password, totp))
            
            if data and isinstance(data, dict) and data.get('status'):
                self.last_auth_time = datetime.now()
                print("DEBUG: Angel One authentication successful.")
                return True
            else:
                msg = data.get('message') if isinstance(data, dict) else "Unknown response format"
                print(f"ERROR: Angel One login failed: {msg}")
        except Exception as e:
            print(f"ERROR: Angel One authentication exception: {e}")
        return False

    async def get_live_price(self, symbol):
        if not symbol: return None
        is_indian = ".NS" in symbol or ".BO" in symbol or "NSE:" in symbol or "BSE:" in symbol
        if is_indian:
            return await self._get_angel_price(symbol)
        return await self._get_international_price(symbol)

    async def _get_angel_price(self, symbol):
        # 1. Standardize and Correct
        clean_symbol = symbol.replace("NSE:", "").replace("BSE:", "").replace(".NS", "").replace(".BO", "").strip().upper()
        if clean_symbol in TICKER_CORRECTIONS:
            clean_symbol = TICKER_CORRECTIONS[clean_symbol]

        index_symbols = ["NIFTY", "BANKNIFTY", "SENSEX", "MIDCPNIFTY", "NIFTYBANK"]
        if clean_symbol in index_symbols:
            angel_symbol = clean_symbol
        elif "NSE:" in symbol or ".NS" in symbol or not "BSE:" in symbol:
            angel_symbol = f"{clean_symbol}-EQ"
        else:
            angel_symbol = f"{clean_symbol}-EQ"

        # 2. Check Cache
        now = datetime.now()
        cache_key = f"ANGEL:{angel_symbol}"
        if cache_key in self.cache:
            c = self.cache[cache_key]
            if now - datetime.fromisoformat(c['timestamp']) < timedelta(minutes=15):
                return c['price']

        # 3. Validation
        await self._ensure_token_list()
        token_info = self.token_map.get(angel_symbol) or self.token_map.get(clean_symbol)
        if not token_info or not token_info.get('token'):
            print(f"WARNING: No token found for {angel_symbol}. Skipping API call.")
            return await self._get_international_price(symbol)

        # 4. Fetch
        for attempt in range(2):
            if not await self.authenticate(force=(attempt > 0)):
                return await self._get_international_price(symbol)

            try:
                token = token_info['token']
                exch_seg = token_info['exch']
                loop = asyncio.get_event_loop()
                print(f"DEBUG: Fetching LTP from Angel One for {angel_symbol} ({token})...")
                data = await loop.run_in_executor(None, lambda: self.smart_api.ltpData(exch_seg, angel_symbol, token))
                
                if not isinstance(data, dict):
                    if attempt == 0: continue
                    else: break

                if data.get('status') and data.get('data'):
                    price = float(data['data'].get('ltp', 0))
                    if price > 0:
                        self.cache[cache_key] = {"price": price, "timestamp": now.isoformat()}
                        self.save_price_cache()
                        return price
                elif data.get('errorCode') in ['AG8001', 'AB1010'] or 'Invalid Token' in str(data.get('message', '')):
                    if attempt == 0:
                        print(f"DEBUG: Session issue detected. Forcing re-authentication...")
                        continue
                if not data.get('status'):
                    print(f"WARNING: Angel LTP failed: {data.get('message')}")
            except Exception as e:
                print(f"ERROR: Angel LTP exception for {angel_symbol}: {e}")
                if attempt == 0: continue

        return await self._get_international_price(symbol)

    async def _get_finnhub_price(self, clean_symbol):
        if not self.finnhub_key: return None
        try:
            import finnhub
            finnhub_client = finnhub.Client(api_key=self.finnhub_key)
            if clean_symbol in ["^NSEI", "^BSESN", "^NSEBANK"]: return None
            
            print(f"DEBUG: Finnhub fallback for {clean_symbol}...")
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: finnhub_client.quote(clean_symbol))
            if res and res.get('c') and float(res['c']) > 0:
                print(f"DEBUG: Finnhub successfully fetched price for {clean_symbol}: {res['c']}")
                return float(res['c'])
        except Exception as e:
            print(f"DEBUG: Finnhub attempt failed for {clean_symbol}: {e}")
        return None

    async def _get_international_price(self, symbol):
        # 2a. First Fallback: Finnhub (if key present)
        clean_raw = symbol.replace("NSE:", "").replace("BSE:", "").replace(".NS", "").replace(".BO", "").replace("-EQ", "").strip().upper()
        
        # Try finnhub with the raw symbol first
        fh_price = await self._get_finnhub_price(clean_raw)
        if fh_price: return fh_price

        # 2b. International / Crypto Fallback (YFinance)
        # For short symbols (e.g. "BP"), try multiple regional suffixes if the first attempt fails
        candidates = [symbol]
        
        if len(clean_raw) <= 3:
            # Add common regional suffixes for ambiguous symbols
            for suffix in [".L", ".NS", ".BO"]:
                if not symbol.endswith(suffix):
                    candidates.append(f"{clean_raw}{suffix}")

        for cand in candidates:
            try:
                import yfinance as yf
                # Strip prefixes and common Angel One suffixes for YFinance
                clean = cand.replace("NSE:", "").replace("BSE:", "").replace(".NS", "").replace(".BO", "")
                clean = clean.replace("-EQ", "").replace("-BE", "").replace("-SM", "").strip()
                
                # Reverse the index mapping for YFinance (Angel One literal -> Yahoo Finance ^ prefix)
                yf_index_map = {
                    "NIFTY": "^NSEI",
                    "BANKNIFTY": "^NSEBANK",
                    "SENSEX": "^BSESN"
                }
                if clean in yf_index_map:
                    clean = yf_index_map[clean]
                else:
                    ticker_stem = clean.split('.')[0].split('-')[0].upper()
                    if ticker_stem in TICKER_CORRECTIONS:
                        clean = clean.replace(ticker_stem, TICKER_CORRECTIONS[ticker_stem])
                
                # Special handling for already formatted pairs like BTC-USD
                if "-USD" in clean or "-" in clean and len(clean) > 7:
                    pass 
                else:
                    suffix = ".NS" if ("NSE:" in cand or ".NS" in cand) else (".BO" if ("BSE:" in cand or ".BO" in cand) else "")
                    if clean in ["^NSEI", "^BSESN", "^NSEBANK"]:
                        pass # Don't add suffix to indices
                    else:
                        if "." not in clean: # Only add preferred suffix if no regional suffix was provided in cand
                            clean = f"{clean}{suffix}"
                
                ticker_stem = clean.split('.')[0].split('-')[0].upper()
                if ticker_stem in TICKER_CORRECTIONS:
                    clean = clean.replace(ticker_stem, TICKER_CORRECTIONS[ticker_stem])
                
                print(f"DEBUG: YFinance fallback for {clean}...")
                ticker = yf.Ticker(clean)
                # Use history(period="1d") instead of fast_info as it's more reliable for some assets
                hist = ticker.history(period="1d")
                if not hist.empty:
                    return round(float(hist['Close'].iloc[-1]), 2)
                
                # Second attempt with fast_info
                price = ticker.fast_info.get('lastPrice')
                if price and price > 0 and not math.isnan(price):
                    return round(float(price), 2)
            except Exception as e:
                print(f"DEBUG: YFinance attempt failed for {cand} ({clean}): {e}")
            
        # 3. FINAL FALLBACK: Search Online (Scraping)
        return await search_price_online(symbol)

    def get_currency_for_symbol(self, symbol):
        if ".NS" in symbol or ".BO" in symbol or "NSE:" in symbol or "BSE:" in symbol:
            return "INR"
        return "USD"

    async def get_historical_price(self, symbol, date_str):
        if not symbol or not date_str: return None
        is_indian = ".NS" in symbol or ".BO" in symbol or "NSE:" in symbol or "BSE:" in symbol
        try:
            target_dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        except: return None
            
        for d in range(5):
            eval_date_str = (target_dt - timedelta(days=d)).strftime("%Y-%m-%d")
            if is_indian:
                price = await self._get_angel_historical(symbol, eval_date_str)
                if price: return price
            price = await self._get_international_historical(symbol, eval_date_str)
            if price: return price
        return None

    async def _get_angel_historical(self, symbol, date_str):
        clean_symbol = symbol.replace("NSE:", "").replace("BSE:", "").replace(".NS", "").replace(".BO", "").strip().upper()
        if clean_symbol in TICKER_CORRECTIONS:
            clean_symbol = TICKER_CORRECTIONS[clean_symbol]

        index_symbols = ["NIFTY", "BANKNIFTY", "SENSEX", "MIDCPNIFTY", "NIFTYBANK"]
        if clean_symbol in index_symbols:
            angel_symbol = clean_symbol
        elif "NSE:" in symbol or ".NS" in symbol or not "BSE:" in symbol:
            angel_symbol = f"{clean_symbol}-EQ"
        else:
            angel_symbol = f"{clean_symbol}-EQ"

        await self._ensure_token_list()
        token_info = self.token_map.get(angel_symbol) or self.token_map.get(clean_symbol)
        if not token_info or not token_info.get('token'):
            print(f"WARNING: [VERIFY] No token found for {angel_symbol}. Skipping history API call.")
            return None
        
        try:
            target_dt = datetime.fromisoformat(date_str) if "T" in date_str else datetime.strptime(date_str, "%Y-%m-%d")
        except Exception:
            try: 
                target_dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
            except Exception: 
                return None
                
        start_time_str = target_dt.strftime("%Y-%m-%d 09:00")
        end_time_str = target_dt.strftime("%Y-%m-%d 15:30")
        
        historicParam = {
            "exchange": token_info['exch'],
            "symboltoken": token_info['token'],
            "interval": "ONE_DAY",
            "fromdate": start_time_str,
            "todate": end_time_str
        }

        for attempt in range(2):
            if not await self.authenticate(force=(attempt > 0)):
                return None
            try:
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(None, lambda: self.smart_api.getCandleData(historicParam))
                if not isinstance(data, dict):
                    if attempt == 0: continue
                    else: break

                if data.get('status') and data.get('data'):
                    candles = data['data']
                    if candles and len(candles) > 0:
                        c_data = candles[-1]
                        return {
                            'open': float(c_data[1]),
                            'high': float(c_data[2]),
                            'low': float(c_data[3]),
                            'close': float(c_data[4])
                        }
                elif data.get('errorCode') in ['AG8001', 'AB1010'] or 'Invalid Token' in str(data.get('message', '')):
                    if attempt == 0:
                        print(f"DEBUG: [VERIFY] Session issue. Forcing re-authentication...")
                        continue
                
                if not data.get('status'):
                    print(f"DEBUG: [VERIFY] Angel History failure: {data.get('message')} for {angel_symbol}")
            except Exception as e:
                print(f"DEBUG: Angel History failed: {e}")
                if attempt == 0: 
                    continue
        return None

    async def _get_international_historical(self, symbol, date_str):
        try:
            import yfinance as yf
            clean = symbol.replace("NSE:", "").replace(".NS", ".NS").replace("BSE:", "").replace(".BO", ".BO")
            if "NSE:" in symbol and not clean.endswith(".NS"): clean += ".NS"
            if "BSE:" in symbol and not clean.endswith(".BO"): clean += ".BO"
            ticker = yf.Ticker(clean)
            target_dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
            hist = ticker.history(start=target_dt.strftime("%Y-%m-%d"), end=(target_dt + timedelta(days=1)).strftime("%Y-%m-%d"))
            if not hist.empty:
                return {
                    'open': float(hist['Open'].iloc[0]),
                    'high': float(hist['High'].iloc[0]),
                    'low': float(hist['Low'].iloc[0]),
                    'close': float(hist['Close'].iloc[0])
                }
        except: pass
        return None

price_service = PriceService()

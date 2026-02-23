import os
import json
import asyncio
import yfinance as yf
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_FILE = os.path.join(BASE_DIR, "data", "price_cache.json")

class PriceService:
    def __init__(self):
        self.cache = self.load_cache()

    def load_cache(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r") as f:
                    return json.load(f)
            except: pass
        return {}

    def save_cache(self):
        try:
            os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
            with open(CACHE_FILE, "w") as f:
                json.dump(self.cache, f)
        except: pass

    async def get_live_price(self, symbol):
        """
        Fetches live stock price from Yahoo Finance via yfinance.
        Handles caching to avoid excessive network calls.
        """
        if not symbol: return None
        
        # Normalize symbol for Yahoo Finance (e.g., NSE:KALYANKJIL -> KALYANKJIL.NS)
        clean_symbol = symbol.replace("NSE:", "").replace("BSE:", "")
        if "NSE:" in symbol or ":NS" in symbol or not "BSE:" in symbol:
            yf_symbol = f"{clean_symbol}.NS"
        else:
            yf_symbol = f"{clean_symbol}.BO"

        # Check cache (15 min TTL)
        now = datetime.now()
        if yf_symbol in self.cache:
            cached_data = self.cache[yf_symbol]
            cache_time = datetime.fromisoformat(cached_data['timestamp'])
            if now - cache_time < timedelta(minutes=15):
                print(f"DEBUG: Price for {yf_symbol} fetched from cache.")
                return cached_data['price']

        print(f"DEBUG: Fetching live price for {yf_symbol} from Yahoo Finance...")
        
        try:
            # yfinance is synchronous, so we run it in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            ticker = yf.Ticker(yf_symbol)
            
            # fast_info is better for just getting the latest price
            info = await loop.run_in_executor(None, lambda: ticker.fast_info)
            price = info.get('last_price') or info.get('lastPrice')
            
            if not price:
                # Fallback to history if fast_info fails
                hist = await loop.run_in_executor(None, lambda: ticker.history(period="1d"))
                if not hist.empty:
                    price = float(hist['Close'].iloc[-1])

            if price and not math.isnan(price):
                price_val = round(float(price), 2)
                self.cache[yf_symbol] = {
                    "price": price_val,
                    "timestamp": now.isoformat()
                }
                self.save_cache()
                print(f"DEBUG: Successfully fetched price for {yf_symbol}: {price_val}")
                return price_val
            else:
                print(f"WARNING: Fetch failed for {yf_symbol} - No valid price data found (NaN or empty).")
        except Exception as e:
            print(f"ERROR: Price Fetch Exception for {yf_symbol}: {e}")
        
        return None

price_service = PriceService()

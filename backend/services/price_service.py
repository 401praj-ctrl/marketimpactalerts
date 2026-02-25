import os
import json
import asyncio
import finnhub
from datetime import datetime, timedelta
import math

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_FILE = os.path.join(BASE_DIR, "data", "price_cache.json")

class PriceService:
    def __init__(self):
        self.api_key = os.environ.get("FINNHUB_API_KEY")
        if not self.api_key:
            print("WARNING: FINNHUB_API_KEY not set in environment.")
        self.finnhub_client = finnhub.Client(api_key=self.api_key)
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
        Fetches live stock price from Finnhub.
        Handles caching to avoid excessive network calls.
        """
        if not symbol: return None
        if not self.api_key:
            print("ERROR: FINNHUB_API_KEY not set. Cannot fetch price.")
            return None
        
        # Normalize symbol for Finnhub
        # Finnhub uses ticker.NS for NSE and ticker.BO for BSE typically, 
        # similar to Yahoo Finance, but verify against their documentation if needed.
        # For Indian stocks, Finnhub might require specific exchanges or symbols.
        # Standard format: RELIANCE.NS
        clean_symbol = symbol.replace("NSE:", "").replace("BSE:", "")
        if "NSE:" in symbol or ":NS" in symbol or not "BSE:" in symbol:
            fh_symbol = f"{clean_symbol}.NS"
        else:
            fh_symbol = f"{clean_symbol}.BO"

        # Check cache (15 min TTL)
        now = datetime.now()
        if fh_symbol in self.cache:
            cached_data = self.cache[fh_symbol]
            cache_time = datetime.fromisoformat(cached_data['timestamp'])
            if now - cache_time < timedelta(minutes=15):
                print(f"DEBUG: Price for {fh_symbol} fetched from cache.")
                return cached_data['price']

        print(f"DEBUG: Fetching live price for {fh_symbol} from Finnhub...")
        
        try:
            # Finnhub client is typically synchronous
            loop = asyncio.get_event_loop()
            quote = await loop.run_in_executor(None, lambda: self.finnhub_client.quote(fh_symbol))
            
            # Finnhub quote response: {'c': 261.2, 'd': 0.5, 'dp': 0.19, 'h': 261.6, 'l': 260.3, 'o': 261.2, 'pc': 260.7, 't': 1582660200}
            # 'c' is the current price
            price = quote.get('c')

            if price is not None and price > 0:
                price_val = round(float(price), 2)
                self.cache[fh_symbol] = {
                    "price": price_val,
                    "timestamp": now.isoformat()
                }
                self.save_cache()
                print(f"DEBUG: Successfully fetched price for {fh_symbol}: {price_val}")
                return price_val
            else:
                print(f"WARNING: Fetch failed for {fh_symbol} - No valid price data found in Finnhub response.")
        except Exception as e:
            print(f"ERROR: Finnhub Price Fetch Exception for {fh_symbol}: {e}")
        
        return None

price_service = PriceService()

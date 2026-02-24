import os
import json
import asyncio
import yfinance as yf
from datetime import datetime, timedelta
import math

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
            
            # The history() method is much more reliable for Indian symbols than fast_info
            # We fetch 1 day of data and take the latest close
            # Strategy 1: Ticker.info['currentPrice'] - Often the most accurate for nominal price
            try:
                info = await loop.run_in_executor(None, lambda: ticker.info)
                if info and 'currentPrice' in info:
                    price = info['currentPrice']
                    print(f"DEBUG: Fetched price for {yf_symbol} via info['currentPrice']: {price}")
                elif info and 'regularMarketPrice' in info:
                    price = info['regularMarketPrice']
                    print(f"DEBUG: Fetched price for {yf_symbol} via info['regularMarketPrice']: {price}")
            except:
                pass

            # Strategy 2: history(period="1d") - Fallback if info fails
            if price is None:
                hist = await loop.run_in_executor(None, lambda: ticker.history(period="1d", auto_adjust=False))
                if not hist.empty:
                    price = float(hist['Close'].iloc[-1])
                    print(f"DEBUG: Fetched price for {yf_symbol} via history(): {price}")

            # Strategy 3: fast_info (Last Resort)
            if price is None:
                try:
                    f_info = await loop.run_in_executor(None, lambda: ticker.fast_info)
                    if hasattr(f_info, 'last_price'):
                        price = f_info.last_price
                    print(f"DEBUG: Fallback to fast_info for {yf_symbol}: {price}")
                except:
                    pass

            if price is not None and not math.isnan(price) and price > 0:
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

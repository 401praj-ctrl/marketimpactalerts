import os
import json
import asyncio
import finnhub
from datetime import datetime, timedelta
import math

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_FILE = os.path.join(BASE_DIR, "data", "price_cache.json")

TICKER_CORRECTIONS = {
    "BAJAJAUTO": "BAJAJ-AUTO",
    "HDFCCBANK": "HDFCBANK",
    "M&M": "M&M",
    "APL Apollo": "APLAPOLLO",
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
    "KALYANKJ": "KALYANKJIL"
}

class PriceService:
    def __init__(self):
        self.api_key = os.environ.get("FINNHUB_API_KEY")
        if not self.api_key:
            print("WARNING: FINNHUB_API_KEY not set in environment.")
        self.finnhub_client = finnhub.Client(api_key=self.api_key)
        self.cache = self.load_cache()

    def get_currency_for_symbol(self, symbol):
        """
        Detects currency based on symbol.
        .NS or .BO -> INR
        Otherwise -> USD
        """
        if ".NS" in symbol or ".BO" in symbol or "NSE:" in symbol or "BSE:" in symbol:
            return "INR"
        return "USD"

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
        Fetches live stock price from Finnhub, with yfinance as fallback for restricted symbols.
        Handles caching to avoid excessive network calls.
        """
        if not symbol: return None
        
        # Normalize symbol
        clean_symbol = symbol.replace("NSE:", "").replace("BSE:", "").strip()
        if clean_symbol in TICKER_CORRECTIONS:
            clean_symbol = TICKER_CORRECTIONS[clean_symbol]

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
                return cached_data['price']

        # 1. Try Finnhub (Preferred for US and supported International)
        if self.api_key:
            try:
                print(f"DEBUG: Fetching live price for {fh_symbol} from Finnhub...")
                loop = asyncio.get_event_loop()
                quote = await loop.run_in_executor(None, lambda: self.finnhub_client.quote(fh_symbol))
                price = quote.get('c')

                if price and price > 0:
                    price_val = round(float(price), 2)
                    self._update_cache(fh_symbol, price_val, now)
                    print(f"DEBUG: Successfully fetched Finnhub price for {fh_symbol}: {price_val}")
                    return price_val
                else:
                    print(f"DEBUG: Finnhub returned no price for {fh_symbol}")
            except Exception as e:
                # Catch 403 or other Finnhub-specific errors
                error_msg = str(e)
                if "403" in error_msg:
                    print(f"DEBUG: Finnhub access restricted for {fh_symbol} (403). Trying fallback...")
                else:
                    print(f"DEBUG: Finnhub error for {fh_symbol}: {e}")

        # 2. Fallback to yfinance (Reliable for Indian stocks even on free tier)
        try:
            import yfinance as yf
            print(f"DEBUG: Attempting yfinance fallback for {fh_symbol}...")
            ticker = yf.Ticker(fh_symbol)
            
            # fast_info is often quicker and avoids some overhead
            info = ticker.fast_info
            price = info.get('lastPrice')
            
            # Fallback to history if fast_info fails
            if not price:
                hist = ticker.history(period="1d")
                if not hist.empty:
                    price = hist['Close'].iloc[-1]

            if price and price > 0 and not math.isnan(price):
                price_val = round(float(price), 2)
                self._update_cache(fh_symbol, price_val, now)
                print(f"DEBUG: Successfully fetched fallback price for {fh_symbol}: {price_val}")
                return price_val
        except Exception as ey:
            print(f"DEBUG: Fallback yfinance failed for {fh_symbol}: {ey}")

        return None

    def _update_cache(self, symbol, price, timestamp):
        self.cache[symbol] = {
            "price": price,
            "timestamp": timestamp.isoformat()
        }
        self.save_cache()

price_service = PriceService()

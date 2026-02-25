import finnhub
import json
import os
import datetime
import asyncio

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGIME_FILE = os.path.join(BASE_DIR, "data", "market_regime.json")

class RegimeService:
    def __init__(self):
        self.api_key = os.environ.get("FINNHUB_API_KEY")
        self.finnhub_client = finnhub.Client(api_key=self.api_key)
        self.current_regime = "NORMAL"
        self.vix_threshold = 20.0
        self.load_regime()

    def load_regime(self):
        if os.path.exists(REGIME_FILE):
            try:
                with open(REGIME_FILE, "r") as f:
                    data = json.load(f)
                    self.current_regime = data.get("regime", "NORMAL")
            except: pass

    async def update_regime(self):
        """
        Detects if we are in a High Volatility (Panic) or Low Volatility (Greed) regime.
        Also simulates FII flow trend check.
        """
        if not self.api_key:
            return False

        try:
            # Finnhub doesn't always have ^VIX for free, but we can try basic index or quote
            loop = asyncio.get_event_loop()
            # Try to get quote for VIX
            quote = await loop.run_in_executor(None, lambda: self.finnhub_client.quote("^VIX"))
            vix = quote.get('c', 20.0) # Default to 20 if failed
            
            if vix == 0: # Finnhub returns 0 if ticker not found
                 vix = 20.0
            
            new_regime = "NORMAL"
            if vix > 25.0:
                new_regime = "HIGH_VOLATILITY"
            elif vix < 15.0:
                new_regime = "LOW_VOLATILITY"
            
            # Simulated FII trend logic 
            # In a real app, this would fetch NSE/BSE FII data
            fii_trend = "POSITIVE" 
            
            change_detected = new_regime != self.current_regime
            self.current_regime = new_regime
            
            with open(REGIME_FILE, "w") as f:
                json.dump({
                    "regime": self.current_regime,
                    "vix": float(vix),
                    "fii_trend": fii_trend,
                    "last_update": datetime.datetime.now().isoformat()
                }, f, indent=2)
            
            return change_detected
        except Exception as e:
            print(f"Error updating regime: {e}")
            return False

    def get_regime(self):
        return self.current_regime

regime_service = RegimeService()

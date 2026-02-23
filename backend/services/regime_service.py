import yfinance as yf
import json
import os
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGIME_FILE = os.path.join(BASE_DIR, "data", "market_regime.json")

class RegimeService:
    def __init__(self):
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
        try:
            # India VIX proxy or US VIX (highly correlated with global regimes)
            vix = yf.Ticker("^VIX").history(period="5d")['Close'].iloc[-1]
            
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

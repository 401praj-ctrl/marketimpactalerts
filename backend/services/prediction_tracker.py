import json
import os
import time
import httpx
from datetime import datetime, timedelta
# Replaced price source with Finnhub

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
PREDICTIONS_FILE = os.path.join(DATA_DIR, "predictions_log.jsonl")
STATS_FILE = os.path.join(DATA_DIR, "prediction_stats.json")

import finnhub

class PredictionTracker:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.api_key = os.environ.get("FINNHUB_API_KEY")
        if not self.api_key:
            print("WARNING: FINNHUB_API_KEY not set in environment.")
        self.finnhub_client = finnhub.Client(api_key=self.api_key)
        self.stats = self.load_stats()
        # Ensure the file exists immediately so the frontend can fetch initial zero stats
        if not os.path.exists(STATS_FILE):
            self.save_stats()

    def load_stats(self):
        default_stats = {
            "total_predictions": 0,
            "correct_predictions": 0,
            "false_signals": 0,
            "avg_accuracy": 0.0,
            "profit_simulation_pct": 0.0,
            "brier_score": 1.0,
            "tier_accuracy": {"Tier-1": 0, "Tier-2": 0, "Tier-3": 0},
            "recent_performance": [],
            "last_auto_verification": None,
            "last_manual_verification": None
        }
        if os.path.exists(STATS_FILE):
            try:
                with open(STATS_FILE, "r") as f:
                    loaded = json.load(f)
                    # Merge loaded into default to ensure missing keys are added
                    default_stats.update(loaded)
                    return default_stats
            except:
                pass
        return default_stats

    def save_prediction(self, alert_data, silent=False):
        # Prevent duplicates by checking if the event is already logged
        event_name = alert_data.get("event")
        if os.path.exists(PREDICTIONS_FILE):
            try:
                with open(PREDICTIONS_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        if event_name in line:
                            return None # Already exists
            except: pass

        prediction = {
            "timestamp": datetime.now().isoformat(),
            "event": event_name,
            "company": alert_data.get("company"),
            "stocks": alert_data.get("stocks", []),
            "direction": alert_data.get("impact_direction"),
            "probability": float(alert_data.get("probability", 50)) / 100.0, 
            "tier": alert_data.get("tier", "Tier-3"),
            "impact_score": alert_data.get("impact_score", 50),
            "live_price": alert_data.get("live_price"),
            "predicted_price": alert_data.get("predicted_price"),
            "verified": False,
            "actual_move": None,
            "z_move": None
        }
        with open(PREDICTIONS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(prediction) + "\n")
        
        self.stats["total_predictions"] += 1
        if not silent:
            self.save_stats()
        return prediction

    async def verify_prediction(self, symbol, actual_move_pct):
        """
        Calculates Z-Move and Brier Score to validate prediction quality.
        """
        # Fetch 20-day volatility (using Finnhub or default)
        volatility = 0.02 # Default 2% daily vol if unknown
        
        # Professional Threshold: Only count if |Z| > 0.7 (significant move)
        z_move = actual_move_pct / volatility if volatility > 0 else 0
        is_significant = abs(z_move) > 0.7
        
        return z_move, is_significant

    async def _get_historical_price(self, symbol, target_date_str):
        """
        Fetches historical price for a given date using Finnhub.
        """
        if not self.api_key:
            print("WARNING: FINNHUB_API_KEY not set for verification.")
            return None

        clean_symbol = symbol.replace("NSE:", "").replace("BSE:", "")
        if "NSE:" in symbol or ".NS" not in symbol:
            fh_symbol = f"{clean_symbol}.NS"
        else:
            fh_symbol = f"{clean_symbol}.BO"

        try:
            # Convert date to timestamp
            target_dt = datetime.strptime(target_date_str, "%Y-%m-%d")
            # Set to end of day to get the daily close
            start_ts = int(target_dt.replace(hour=0, minute=0, second=0).timestamp())
            end_ts = int(target_dt.replace(hour=23, minute=59, second=59).timestamp())

            loop = asyncio.get_event_loop()
            # Finnhub stock_candles: symbol, resolution, from, to
            # Resolution 'D' for daily
            res = await loop.run_in_executor(None, lambda: self.finnhub_client.stock_candles(fh_symbol, 'D', start_ts - 86400*3, end_ts))
            
            if res.get('s') == 'ok':
                # 'c' list contains closing prices
                closes = res.get('c', [])
                if closes:
                    return float(closes[-1])
            
            print(f"Finnhub: No historical data for {fh_symbol} on {target_date_str}")
        except Exception as e:
            print(f"Historical Fetch Error for {fh_symbol}: {e}")
            
        return None

    def update_calibration(self, predicted_prob, met_outcome):
        """
        Updates the Brier Score: mean((Prob - Outcome)^2)
        Outcome is 1.0 if direction was correct, 0.0 otherwise.
        """
        error_sq = (predicted_prob - met_outcome)**2
        # Online mean update
        n = self.stats["total_predictions"]
        old_brier = self.stats.get("brier_score", 1.0)
        self.stats["brier_score"] = old_brier + (error_sq - old_brier) / n
        self.save_stats()

    def save_stats(self):
        with open(STATS_FILE, "w") as f:
            json.dump(self.stats, f, indent=2)

    async def run_cleanup_and_verification(self, source="auto"):
        """
        Scans predictions_log.jsonl for highlights where impact_date_est has passed.
        Verifies against actual market data and updates stats.
        """
        now_ts = datetime.now().isoformat()
        if source == "manual":
            self.stats["last_manual_verification"] = now_ts
        else:
            self.stats["last_auto_verification"] = now_ts
            
        if not os.path.exists(PREDICTIONS_FILE):
            return

        print(f"DEBUG: Starting {source} verification of past predictions...")
        updated_predictions = []
        changes_made = False
        
        try:
            with open(PREDICTIONS_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            for line in lines:
                if not line.strip(): continue
                pred = json.loads(line)
                
                # If already verified, keep as is
                if pred.get("verified"):
                    updated_predictions.append(pred)
                    continue
                
                # Check if impact date has passed
                impact_date_str = pred.get("impact_date_est")
                if not impact_date_str:
                    updated_predictions.append(pred)
                    continue
                
                try:
                    impact_date = datetime.strptime(impact_date_str, "%Y-%m-%d").date()
                    today = datetime.now().date()
                    
                    if impact_date < today:
                        # Time to verify!
                        symbol = pred.get("stocks", [None])[0]
                        if symbol:
                            print(f"  [VERIFYING] {pred.get('event')} for {symbol}...")
                            
                            # Get price on event date and impact date via Finnhub
                            event_date_str = pred.get("timestamp")[:10]
                            
                            start_price = pred.get("live_price")
                            if not start_price:
                                start_price = await self._get_historical_price(symbol, event_date_str)
                            
                            end_price = await self._get_historical_price(symbol, impact_date_str)
                            
                            if start_price and end_price:
                                try:
                                    actual_move = (end_price / start_price) - 1
                                    direction = pred.get("direction", "").upper()
                                    
                                    # Match result
                                    is_correct = False
                                    if direction == "UP" and actual_move > 0.01: # >1% move
                                        is_correct = True
                                    elif direction == "DOWN" and actual_move < -0.01: # <-1% move
                                        is_correct = True
                                    elif direction == "NEUTRAL" and abs(actual_move) < 0.01:
                                        is_correct = True
                                    
                                    # Calculate Z-Move and Brier
                                    z_move, is_sig = await self.verify_prediction(symbol, actual_move)
                                    
                                    # Update prediction object
                                    pred["verified"] = True
                                    pred["actual_move"] = actual_move
                                    pred["z_move"] = z_move
                                    pred["is_correct"] = is_correct
                                    
                                    # Update global stats
                                    if is_correct:
                                        self.stats["correct_predictions"] += 1
                                    else:
                                        self.stats["false_signals"] += 1
                                    
                                    # Update Brier
                                    outcome = 1.0 if is_correct else 0.0
                                    self.update_calibration(pred.get("probability", 0.5), outcome)
                                    
                                    # Update Tier Accuracy
                                    tier = pred.get("tier", "Tier-3")
                                    if tier in self.stats["tier_accuracy"]:
                                        total_key = "total_" + tier.lower().replace("-", "")
                                        correct_key = "correct_" + tier.lower().replace("-", "")
                                        
                                        if total_key not in self.stats:
                                            self.stats[total_key] = 0
                                            self.stats[correct_key] = 0
                                            
                                        self.stats[total_key] += 1
                                        if is_correct:
                                            self.stats[correct_key] += 1
                                            
                                        # Calculate percentage
                                        self.stats["tier_accuracy"][tier] = int((self.stats[correct_key] / self.stats[total_key]) * 100)
                                        
                                    # Update Profit Simulation
                                    # We simulate taking a trade in the predicted direction
                                    # if UP and move is +5%, we gain 5%
                                    # if UP and move is -5%, we lose 5%
                                    move_capture = actual_move if direction == "UP" else (-actual_move if direction == "DOWN" else 0)
                                    
                                    self.stats["profit_simulation_pct"] += move_capture * 100
                                    self.stats["profit_simulation_pct"] = round(self.stats["profit_simulation_pct"], 2)
                                    
                                    # Calculate average accuracy
                                    total_verified = self.stats["correct_predictions"] + self.stats["false_signals"]
                                    if total_verified > 0:
                                        self.stats["avg_accuracy"] = (self.stats["correct_predictions"] / total_verified) * 100
                                    
                                    # Add to recent performance
                                    self.stats["recent_performance"].insert(0, {
                                        "event": pred.get("event"),
                                        "is_correct": is_correct,
                                        "move": actual_move
                                    })
                                    self.stats["recent_performance"] = self.stats["recent_performance"][:10]
                                    
                                    changes_made = True
                                    print(f"    --> Result: {'CORRECT' if is_correct else 'FALSE'} (Move: {actual_move:.2%})")
                                except Exception as ve:
                                    print(f"    --> Error verifying {symbol}: {ve}")
                        
                        updated_predictions.append(pred)
                    else:
                        # Impact date not yet reached
                        updated_predictions.append(pred)
                except Exception as de:
                    print(f"  [ERROR] Date parsing failed for {pred.get('event')}: {de}")
                    updated_predictions.append(pred)

            if changes_made:
                with open(PREDICTIONS_FILE, "w", encoding="utf-8") as f:
                    for p in updated_predictions:
                        f.write(json.dumps(p) + "\n")
                self.save_stats()
                print(f"DEBUG: Automated verification complete. Stats updated.")
            else:
                print(f"DEBUG: No predictions needed verification.")
                
        except Exception as e:
            print(f"ERROR in run_cleanup_and_verification: {e}")

    def get_stats(self):
        return self.stats

# Global instance
tracker = PredictionTracker()

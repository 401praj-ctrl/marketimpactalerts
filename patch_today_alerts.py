import json
import os
import sys
import asyncio
from datetime import datetime

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from services.price_service import price_service
from services.prediction_tracker import tracker

def get_ist_now():
    # Simple manual offset for testing if needed, but we'll try to be consistent
    return datetime.utcnow()

async def patch_alerts():
    today_str = "2026-02-27"
    cache_path = os.path.join('backend', 'data', 'cached_alerts.json')
    log_path = os.path.join('backend', 'data', 'predictions_log.jsonl')
    
    print(f"Starting patch for {today_str}...")
    
    # 1. Patch cached_alerts.json
    if os.path.exists(cache_path):
        with open(cache_path, 'r') as f:
            alerts = json.load(f)
        
        updated_count = 0
        for alert in alerts:
            # Check if it's today's alert (in timestamp or event_date)
            is_today = today_str in alert.get('timestamp', '') or today_str in alert.get('event_date', '')
            
            # Or if it's missing prices and we want to be helpful
            needs_patch = is_today and (not alert.get('live_price') or not alert.get('predicted_price'))
            
            if needs_patch:
                symbol = alert.get('stocks', [None])[0]
                if symbol:
                    print(f"  Patching alert: {alert.get('event')[:50]}...")
                    try:
                        # Fetch Live Price
                        if not alert.get('live_price'):
                            lp = await price_service.get_live_price(symbol)
                            if lp:
                                alert['live_price'] = lp
                                print(f"    - Found Live Price: {lp}")
                        
                        # Calculate Predicted Price (Fallback Logic)
                        if alert.get('live_price') and not alert.get('predicted_price'):
                            lp = float(alert['live_price'])
                            p = float(alert.get('probability', 60))
                            direction = alert.get('impact_direction', 'NEUTRAL').lower()
                            tier = alert.get('tier', 'Tier-3')
                            
                            # Standard logic we just implemented in main.py
                            base_move = 0.01 if tier == 'Tier-1' else (0.005 if tier == 'Tier-2' else 0.002)
                            move_factor = base_move * (p / 50.0) 
                            
                            if direction == 'up':
                                alert['predicted_price'] = round(lp * (1 + move_factor), 2)
                            elif direction == 'down':
                                alert['predicted_price'] = round(lp * (1 - move_factor), 2)
                            
                            if alert.get('predicted_price'):
                                print(f"    - Calculated Impact Price: {alert['predicted_price']}")
                                updated_count += 1
                    except Exception as e:
                        print(f"    - Error patching: {e}")
        
        if updated_count > 0:
            with open(cache_path, 'w') as f:
                json.dump(alerts, f, indent=2)
            print(f"Successfully updated {updated_count} alerts in {cache_path}")
        else:
            print("No alerts needed patching in cached_alerts.json")

    # 2. Patch predictions_log.jsonl
    if os.path.exists(log_path):
        new_lines = []
        updated_log_count = 0
        with open(log_path, 'r') as f:
            for line in f:
                try:
                    alert = json.loads(line)
                    is_today = today_str in alert.get('timestamp', '')
                    needs_patch = is_today and (not alert.get('live_price') or not alert.get('predicted_price'))
                    
                    if needs_patch:
                        symbol = alert.get('stocks', [None])[0]
                        if symbol:
                            lp = alert.get('live_price')
                            if not lp:
                                lp = await price_service.get_live_price(symbol)
                                if lp: alert['live_price'] = lp
                            
                            if alert.get('live_price') and not alert.get('predicted_price'):
                                lp = float(alert['live_price'])
                                p = float(alert.get('probability', 0.6)) * 100 # In log it's 0-1
                                direction = alert.get('direction', alert.get('impact_direction', 'NEUTRAL')).lower()
                                tier = alert.get('tier', 'Tier-3')
                                
                                base_move = 0.01 if tier == 'Tier-1' else (0.005 if tier == 'Tier-2' else 0.002)
                                move_factor = base_move * (p / 50.0) 
                                if direction == 'up':
                                    alert['predicted_price'] = round(lp * (1 + move_factor), 2)
                                elif direction == 'down':
                                    alert['predicted_price'] = round(lp * (1 - move_factor), 2)
                                updated_log_count += 1
                    
                    new_lines.append(json.dumps(alert))
                except:
                    new_lines.append(line.strip())
        
        if updated_log_count > 0:
            with open(log_path, 'w') as f:
                for line in new_lines:
                    f.write(line + '\n')
            print(f"Successfully updated {updated_log_count} alerts in {log_path}")

if __name__ == "__main__":
    asyncio.run(patch_alerts())

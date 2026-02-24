import requests
import os
from dotenv import load_dotenv

# Load env from backend dir
backend_dir = os.path.join(os.getcwd(), 'backend')
load_dotenv(os.path.join(backend_dir, '.env'))

def broadcast_update():
    app_id = "7087a2bc-e285-49a9-a404-15be244a893f"
    api_key = os.environ.get("ONESIGNAL_REST_API_KEY", "").strip()
    
    if not api_key:
        print("ERROR: ONESIGNAL_REST_API_KEY not found in environment.")
        return

    headers = {
        "Authorization": f"Basic {api_key}",
        "Content-Type": "application/json; charset=utf-8"
    }
    
    payload = {
        "app_id": app_id,
        "included_segments": ["Total Subscriptions"],
        "headings": {"en": "🚀 New Update Available (v1.2.0)"},
        "contents": {"en": "We've fixed stock prices, added timestamps, and more! Tap to update now."},
        "data": {"type": "update", "version": "1.2.0"}
    }
    
    try:
        response = requests.post("https://onesignal.com/api/v1/notifications", headers=headers, json=payload, timeout=10)
        print(f"OneSignal Response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Failed to send notification: {e}")

if __name__ == "__main__":
    broadcast_update()

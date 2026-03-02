import os
import requests
from dotenv import load_dotenv

# Load from backend/.env if it exists
dotenv_path = os.path.join("backend", ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

def send_update_notification():
    app_id = os.environ.get("ONESIGNAL_APP_ID")
    api_key = os.environ.get("ONESIGNAL_REST_API_KEY")

    if not app_id or not api_key:
        print("ERROR: Missing OneSignal configuration. Set ONESIGNAL_APP_ID and ONESIGNAL_REST_API_KEY.")
        return

    headers = {
        "Authorization": f"Basic {api_key}",
        "Content-Type": "application/json; charset=utf-8"
    }

    payload = {
        "app_id": app_id,
        "included_segments": ["Total Subscriptions"],
        "headings": {"en": "🚀 New Update Available: v1.2.14+44"},
        "contents": {"en": "Smarter AI date inferences and rebuilt online search engine for guaranteed price fetching on obscure symbols! Download now."},
        "buttons": [
            {"id": "download", "text": "Download Now", "icon": "ic_menu_download"}
        ]
    }

    try:
        response = requests.post(
            "https://onesignal.com/api/v1/notifications",
            headers=headers,
            json=payload,
            timeout=10
        )
        if response.status_code == 200:
            print(f"SUCCESS: Update notification sent to all users. Response: {response.text}")
        else:
            print(f"FAILED: Status {response.status_code}, Response: {response.text}")
    except Exception as e:
        print(f"ERROR: Exception while sending notification: {e}")

if __name__ == "__main__":
    send_update_notification()

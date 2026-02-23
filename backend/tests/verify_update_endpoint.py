import requests
import json
import os

def test_update_endpoint():
    # Use localhost as it's the safest way to test internal backend state
    port = 8000
    url = f"http://localhost:{port}/app/version"
    
    print(f"Testing endpoint: {url}")
    try:
        response = requests.get(url)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("Response JSON:")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Connection failed (is the server running?): {e}")

if __name__ == "__main__":
    test_update_endpoint()

import httpx
import asyncio
import os

async def test_key(api_key):
    print(f"Testing Key: {api_key[:10]}...")
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "Key Test Script",
    }
    payload = {
        "model": "google/gemini-2.0-flash-exp:free",
        "messages": [{"role": "user", "content": "Say hello"}]
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                print("✅ SUCCESS! Key is valid.")
                print(f"Response: {response.json()['choices'][0]['message']['content']}")
            else:
                print(f"❌ FAILED! Status: {response.status_code}")
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"❗ ERROR: {e}")

import sys

if __name__ == "__main__":
    if len(sys.argv) > 1:
        key = sys.argv[1]
    else:
        key = input("Enter your OpenRouter API Key to test: ")
    asyncio.run(test_key(key))

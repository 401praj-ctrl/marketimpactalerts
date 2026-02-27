import asyncio
import os
import sys
import httpx

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

MODELS = [
    "google/gemma-3-12b-it:free",
    "openai/gpt-oss-20b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
]

api_key = os.environ.get("OPENROUTER_API_KEY_1")

async def test_models():
    print(f"Testing with key: {api_key[:6]}...")
    async with httpx.AsyncClient() as client:
        for model in MODELS:
            print(f"Testing model: {model}")
            try:
                response = await client.post(
                    url="https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": "Hello"}]
                    },
                    timeout=10
                )
                print(f"Status: {response.status_code}")
                if response.status_code != 200:
                    print(response.text)
                else:
                    print("Success.")
            except Exception as e:
                print(e)
            print("-" * 20)

if __name__ == "__main__":
    asyncio.run(test_models())

import os
import asyncio
from google import genai
from google.genai import types

async def test_search():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not found.")
        return

    client = genai.Client(api_key=api_key)
    
    # Try using Google Search tool
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash', # Or gemini-1.5-flash
            contents="What is the current stock ticker and price for Clean Max Enviro Energy Solutions?",
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearchRetrieval())]
            )
        )
        print("Search Response:")
        print(response.text)
        if response.candidates and response.candidates[0].grounding_metadata:
             print("\nGrounding Metadata found!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_search())

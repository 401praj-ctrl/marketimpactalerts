import httpx
import os
import asyncio
from dotenv import load_dotenv

# load_dotenv() is handled globally in main.py


NEWS_DATA_API_KEY = os.getenv("NEWS_DATA_API_KEY", "pub_a326b4cc284847d8bac2e42e7ad95d61")

async def fetch_news_data_headlines():
    url = f'https://newsdata.io/api/1/latest?apikey={NEWS_DATA_API_KEY}'
    print("Fetching NewsData.io feeds...")
    try:
        # User provided link with space, fixing it
        url = url.replace(" ", "")
        async with httpx.AsyncClient() as client:
            print(f"  DEBUG: Querying NewsData.io for 'Indian Economy'...")
            response = await client.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                print(f"    -> NewsData returned {len(results)} results.")
                
                headlines = []
                for result in results:
                    if result.get('title') and result.get('link'):
                        headlines.append({
                            "title": result['title'],
                            "link": result['link'],
                            "category": "GLOBAL LATEST (NEWSDATA)",
                            "published": result.get('pubDate', '')
                        })
                print(f"Fetched {len(headlines)} headlines from NewsData.io.")
                return headlines
            else:
                print(f"Error fetching NewsData.io: {response.status_code}")
                print(f"Response: {response.text}")
                return []
    except Exception as e:
        print(f"Exception fetching NewsData.io: {e}")
        return []

if __name__ == "__main__":
    # Test fetch
    async def test():
        news = await fetch_news_data_headlines()
        for n in news[:5]:
            print(f"- {n['title']}")
    asyncio.run(test())

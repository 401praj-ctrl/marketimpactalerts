import httpx
import os
import asyncio
from dotenv import load_dotenv

# load_dotenv() is handled globally in main.py


NEWS_API_KEY = os.getenv("NEWS_API_KEY", "d8e2bf7094024f01a73bccc87cee4c8e")

async def fetch_news_api_headlines():
    url = f'https://newsapi.org/v2/top-headlines?country=us&apiKey={NEWS_API_KEY}'
    print("Fetching NewsAPI feeds...")
    try:
        async with httpx.AsyncClient() as client:
            print(f"  DEBUG: Querying NewsAPI for top US headlines...") # Modified print statement
            response = await client.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                articles = data.get('articles', [])
                print(f"    -> NewsAPI returned {len(articles)} articles.") # Added print statement
                headlines = []
                for article in articles:
                    if article.get('title') and article.get('url'):
                        headlines.append({
                            "title": article['title'],
                            "link": article['url'],
                            "category": "US TOP HEADLINES",
                            "published": article.get('publishedAt', '')
                        })
                print(f"Fetched {len(headlines)} headlines from NewsAPI.")
                return headlines
            else:
                print(f"    -> NewsAPI Error: {response.status_code} - {response.text}") # Modified print statement
                return []
    except Exception as e:
        print(f"Exception fetching NewsAPI: {e}")
        return []

if __name__ == "__main__":
    # Test fetch
    async def test():
        news = await fetch_news_api_headlines()
        for n in news[:5]:
            print(f"- {n['title']}")
    asyncio.run(test())

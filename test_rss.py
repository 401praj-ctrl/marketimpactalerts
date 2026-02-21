import asyncio, sys
sys.path.append('.')
from backend.services.rss_service import fetch_all_rss_news
from backend.services.news_api_service import fetch_all_api_news

async def main():
    rss = await fetch_all_rss_news()
    print("RSS:", [(r.get('published', 'N/A')[:10], r.get('title', '')[:30]) for r in rss[:10]])
    api = await fetch_all_api_news()
    print("API:", [(r.get('published', 'N/A')[:10], r.get('title', '')[:30]) for r in api[:10]])

asyncio.run(main())

import httpx
import asyncio
import datetime

async def fetch_hacker_news_headlines():
    print("Fetching Hacker News top stories...")
    headlines = []
    try:
        async with httpx.AsyncClient() as client:
            print("  DEBUG: Fetching Top Stories from Hacker News...")
            # Get top stories IDs
            top_ids_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
            response = await client.get(top_ids_url, timeout=10)
            
            if response.status_code == 200:
                story_ids = response.json()[:20] 
                print(f"    -> Found {len(story_ids)} top stories. Fetching details...")
                
                tasks = []
                for story_id in story_ids:
                    story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                    tasks.append(client.get(story_url, timeout=10))
                
                story_responses = await asyncio.gather(*tasks, return_exceptions=True)
                
                for res in story_responses:
                    if isinstance(res, httpx.Response) and res.status_code == 200:
                        story = res.json()
                        if story and 'title' in story and 'url' in story:
                            headlines.append({
                                "title": story['title'],
                                "link": story['url'],
                                "category": "TECH & STARTUP (HN)",
                                "published": datetime.datetime.now().isoformat() 
                            })
                
                print(f"    -> Successfully fetched {len(headlines)} HN stories.")
                return headlines
            else:
                print(f"    -> HN Error: {response.status_code}")
                return []
    except Exception as e:
        print(f"    -> HN Exception: {e}")
        return []

if __name__ == "__main__":
    # Test fetch
    async def test():
        news = await fetch_hacker_news_headlines()
        for n in news[:5]:
            print(f"- {n['title']}")
    asyncio.run(test())

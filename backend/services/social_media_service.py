import httpx
import asyncio
import feedparser
import random

# Subreddits with high signal for market/social trends
SUBREDDITS = [
    "stocks",
    "WallStreetBets",
    "technology",
    "business",
    "worldnews",
    "economics"
]

# High-impact Twitter accounts (via Nitter)
# Using multiple Nitter instances to avoid rate limits
NITTER_INSTANCES = [
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
    "https://nitter.lucabased.xyz"
]

TWITTER_ACCOUNTS = [
    "Deltaone",       # Walter Bloomberg (Breaking financial news)
    "unusual_whales", # Unusual option activity
    "FinancialJuice", # Real-time news
    "BreakingNews",   # Global breaking news
    "CNBCnow"         # CNBC Headlines
]

async def fetch_twitter_headlines():
    headlines = []
    print("Fetching X (Twitter) feeds via Nitter...")
    
    # Pick a random instance to distribute load
    instance = random.choice(NITTER_INSTANCES)
    print(f"  DEBUG: Using Nitter instance: {instance}")
    
    for account in TWITTER_ACCOUNTS:
        url = f"{instance}/{account}/rss"
        try:
            # Run feedparser in executor to avoid blocking
            loop = asyncio.get_event_loop()
            feed = await loop.run_in_executor(None, feedparser.parse, url)
            
            if feed.entries:
                print(f"    -> Found {len(feed.entries)} tweets from @{account}")
                for entry in feed.entries[:5]: # Top 5 tweets
                    headlines.append({
                        "title": f"@{account}: {entry.title}",
                        "link": entry.link,
                        "category": "SOCIAL: X/Twitter",
                        "published": entry.published if 'published' in entry else ""
                    })
            else:
                print(f"    -> No tweets found for @{account} (or instance blocked)")
                
        except Exception as e:
            print(f"    -> Error fetching @{account}: {e}")
            
    print(f"Fetched {len(headlines)} headlines from X/Twitter.")
    return headlines

async def fetch_social_media_headlines():
    headlines = []
    print("Fetching Reddit feeds...")
    
    # 1. Fetch Reddit
    headers = {'User-Agent': 'MarketImpactAlertsApp/1.0 by User'}
    async with httpx.AsyncClient() as client:
        for sub in SUBREDDITS:
            url = f"https://www.reddit.com/r/{sub}/hot.json?limit=10"
            try:
                await asyncio.sleep(0.5)
                response = await client.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    posts = data.get('data', {}).get('children', [])
                    for post in posts:
                        pdata = post.get('data', {})
                        if pdata.get('title') and pdata.get('url'):
                            headlines.append({
                                "title": f"r/{sub}: {pdata['title']}",
                                "link": pdata['url'],
                                "category": f"SOCIAL: Reddit",
                                "published": "" 
                            })
            except Exception as e:
                print(f"  Exception fetching r/{sub}: {e}")
                
    # 2. Fetch Twitter
    twitter_news = await fetch_twitter_headlines()
    headlines.extend(twitter_news)
            
    return headlines

if __name__ == "__main__":
    asyncio.run(fetch_social_media_headlines())

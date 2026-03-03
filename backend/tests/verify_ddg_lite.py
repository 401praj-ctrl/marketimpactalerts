import httpx
import asyncio
from bs4 import BeautifulSoup
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
]

def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive"
    }

async def search_lite(query: str):
    url = f"https://lite.duckduckgo.com/lite/"
    print(f"\n--- Testing DDG Lite POST for: {query} ---")
    data = {"q": query}
    
    try:
        async with httpx.AsyncClient(headers=get_headers(), timeout=15) as client:
            response = await client.post(url, data=data)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                snippets = soup.find_all('td', class_='result-snippet')
                
                if snippets:
                    print("Found snippets:")
                    full_text = " ".join([s.get_text() for s in snippets])
                    print(full_text[:500])
                else:
                    print("No snippet tags found in HTML. Check structure:")
                    print(soup.get_text()[:300].replace('\n', ' '))
                         
            else:
                print(f"DDG block/failure. HTTP {response.status_code}")
    except Exception as e:
         print(f"Exception: {e}")

async def main():
    await search_lite("TSLA share price live")
    await search_lite("Clean Max Enviro Energy share price ticker NSE BSE")

if __name__ == "__main__":
    asyncio.run(main())

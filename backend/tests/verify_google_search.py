import httpx
import asyncio
import re
from bs4 import BeautifulSoup
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0"
]

def get_random_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

async def search_google(query: str):
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    print(f"Testing Google Search for: {query}")
    
    try:
        async with httpx.AsyncClient(headers=get_random_headers(), timeout=10) as client:
            response = await client.get(url)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                text = soup.get_text()
                
                # Try to print a small snippet to see if it's a captcha page or real results
                if "Our systems have detected unusual traffic" in text or "solving the above CAPTCHA" in text:
                    print("Google BLOCK: CAPTCHA Page Detected!")
                else:
                    print("Success! Page looks valid. Snippet:")
                    print(text[:300].replace('\n', ' '))
                    
                    # Test Price regexes
                    text_upper = text.upper()
                    price_matches = re.findall(r'(?:₹|\$|RS\.?|INR)\s?(\d+(?:,\d+)?(?:\.\d+)?)', text_upper)
                    if not price_matches:
                        price_matches = re.findall(r'(?:PRICE|LTP|CLOSE|LAST|TRADING AT)[:\s]+(\d+(?:,\d+)?(?:\.\d+)?)', text_upper)
                    
                    if price_matches:
                         print(f"-> Mined Potential Prices: {price_matches}")
                    else:
                         print("-> No prices found in text.")
                         
                    # Test Ticker regexes
                    nse_matches = re.findall(r'NSE[:\s]([A-Z0-9&\-]+)', text_upper)
                    if nse_matches:
                         print(f"-> Mined Potential NSE Tickers: {nse_matches[:3]}")
                         
            else:
                print(f"Google block/failure. HTTP {response.status_code}")
    except Exception as e:
         print(f"Exception: {e}")

async def main():
    await search_google("Clean Max Enviro Energy share price ticker NSE BSE")
    print("-" * 40)
    await search_google("NSE:RELIANCE share price live")
    print("-" * 40)
    await search_google("BP share price live")

if __name__ == "__main__":
    asyncio.run(main())

import httpx
import asyncio
import re
import json
from bs4 import BeautifulSoup
from typing import Optional, List

# Basic headers to avoid immediate blocking
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

async def search_ticker_online(company_name: str) -> Optional[List[str]]:
    """
    Searches DuckDuckGo for the NSE/BSE ticker of a company.
    Returns a list of symbols if found.
    """
    if not company_name or company_name.lower() == "n/a":
        return None

    query = f"{company_name} share price ticker NSE BSE"
    url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
    
    print(f"  [SEARCH] Looking for ticker: {company_name}...")
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=10) as client:
            response = await client.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                text = soup.get_text()
                
                # Regex for NSE/BSE symbols (e.g., NSE:RELIANCE, BSE:500325, CLEAN-EQ)
                # Look for patterns like (NSE: SYMBOL) or "Trading on NSE as SYMBOL"
                nse_matches = re.findall(r'NSE[:\s]([A-Z0-9&\-]+)', text.upper())
                bse_matches = re.findall(r'BSE[:\s]([A-Z0-9&\-]+)', text.upper())
                
                found = []
                for m in nse_matches:
                    if len(m) >= 2 and len(m) <= 15:
                        found.append(f"NSE:{m}")
                for m in bse_matches:
                    if len(m) >= 2 and len(m) <= 15:
                        found.append(f"BSE:{m}")
                
                # Deduplicate and limit
                if found:
                    result = list(set(found))[:3]
                    print(f"  [SEARCH] Found tickers: {result}")
                    return result
                    
    except Exception as e:
        print(f"  [SEARCH] Ticker search failed: {e}")
    
    return None

async def search_price_online(symbol: str) -> Optional[float]:
    """
    Searches DuckDuckGo for the live price of a ticker.
    Returns float price if found.
    """
    if not symbol:
        return None

    query = f"{symbol} share price live"
    url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
    
    print(f"  [SEARCH] Looking for price: {symbol}...")
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=10) as client:
            response = await client.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Look for price patterns in the snippets
                snippets = soup.find_all('a', class_='result__snippet')
                text_blob = " ".join([s.get_text() for s in snippets])
                
                # Try to find a currency amount (₹ or $ followed by numbers)
                # Or just a number near "Price" or "LTP"
                price_matches = re.findall(r'(?:₹|\$|RS\.?|INR)\s?(\d+(?:,\d+)?(?:\.\d+)?)', text_blob.upper())
                if price_matches:
                    # Pick the first one that looks like a valid price
                    for p_str in price_matches:
                        try:
                            price = float(p_str.replace(',', ''))
                            if price > 0:
                                print(f"  [SEARCH] Found price for {symbol}: {price}")
                                return price
                        except: continue

    except Exception as e:
        print(f"  [SEARCH] Price search failed: {e}")
    
    return None

if __name__ == "__main__":
    # Quick test
    async def test():
        t = await search_ticker_online("Clean Max Enviro Energy")
        print(f"Result Ticker: {t}")
        if t:
            p = await search_price_online(t[0])
            print(f"Result Price: {p}")
    
    asyncio.run(test())

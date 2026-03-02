import httpx
import asyncio
import re
import json
from bs4 import BeautifulSoup
from typing import Optional, List

import random

# Rotate User-Agents to reduce probability of blocking
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0"
]

def get_random_headers():
    return {"User-Agent": random.choice(USER_AGENTS)}

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
        async with httpx.AsyncClient(headers=get_random_headers(), timeout=10) as client:
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
            else:
                print(f"  [SEARCH] Ticker search failed with status code: {response.status_code}")
                    
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
        async with httpx.AsyncClient(headers=get_random_headers(), timeout=10) as client:
            response = await client.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Look for price patterns in the snippets
                snippets = soup.find_all('a', class_='result__snippet')
                text_blob = " ".join([s.get_text() for s in snippets])
                text_blob_upper = text_blob.upper()
                
                # 1. Primary Regex: Look for currency symbols (the most reliable)
                # Matches: $38.86, ₹1,234.50, RS 500, etc.
                price_matches = re.findall(r'(?:₹|\$|RS\.?|INR)\s?(\d+(?:,\d+)?(?:\.\d+)?)', text_blob_upper)
                
                # 2. Secondary Regex (BROADER): Look for numbers near keywords if no currency is found
                # Matches: "Price: 38.86", "LTP 124.5", "Close 50.2"
                if not price_matches:
                    keyword_matches = re.findall(r'(?:PRICE|LTP|CLOSE|LAST|TRADING AT)[:\s]+(\d+(?:,\d+)?(?:\.\d+)?)', text_blob_upper)
                    price_matches.extend(keyword_matches)

                if price_matches:
                    # Pick the first one that looks like a valid price (> 0.1 to avoid random numbers)
                    for p_str in price_matches:
                        try:
                            # Strip commas and convert
                            price = float(p_str.replace(',', ''))
                            if price > 0.1:
                                # Final sanity check: if the symbol is very short (BP), 
                                # ensure the snippet actually contains "STOCK" or "SHARE"
                                if len(symbol) <= 3 and not any(k in text_blob_upper for k in ["STOCK", "SHARE", "PLC", "INC", "LTD"]):
                                    print(f"  [SEARCH] Found number {price} for {symbol} but skipping due to low context confidence.")
                                    continue
                                    
                                print(f"  [SEARCH] Successfully found price for {symbol}: {price}")
                                return price
                        except: continue
            else:
                print(f"  [SEARCH] Price search failed with status code: {response.status_code}")

    except Exception as e:
        print(f"  [SEARCH] Price search failed for {symbol}: {e}")
    
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

import httpx
import asyncio
import re
import json
from bs4 import BeautifulSoup
from typing import Optional, List

import random

# Rotate User-Agents to reduce probability of blocking
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
]

def get_random_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

async def search_ticker_online(company_name: str) -> Optional[List[str]]:
    """
    Searches DuckDuckGo for the NSE/BSE ticker of a company.
    Returns a list of symbols if found.
    """
    if not company_name or company_name.lower() == "n/a":
        return None

    query = f"{company_name} share price ticker NSE BSE"
    url = "https://lite.duckduckgo.com/lite/"
    data = {"q": query}
    
    print(f"  [SEARCH] Looking for ticker: {company_name}...")
    
    # Pass 1: Yahoo Finance Auto-complete API
    try:
        yf_url = f"https://query2.finance.yahoo.com/v1/finance/search?q={company_name}"
        async with httpx.AsyncClient(headers=get_random_headers(), timeout=10) as client:
            res = await client.get(yf_url)
            if res.status_code == 200:
                data = res.json()
                quotes = data.get("quotes", [])
                found_yf = []
                for q in quotes:
                    sym = q.get("symbol", "")
                    if sym.endswith(".NS"):
                        found_yf.append(f"NSE:{sym.replace('.NS', '')}")
                    elif sym.endswith(".BO"):
                        found_yf.append(f"BSE:{sym.replace('.BO', '')}")
                if found_yf:
                    print(f"  [SEARCH] Found tickers via Yahoo: {found_yf}")
                    return found_yf[:3]
    except Exception as e:
        print(f"  [SEARCH] Yahoo Finance logic failed: {e}")
        
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(headers=get_random_headers(), timeout=15) as client:
                response = await client.post(url, data=data)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    text = soup.get_text()
                    
                    # Check for rate limit
                    if "rate limit" in text.lower() or "bot" in text.lower():
                         print(f"  [SEARCH] TICKER SEARCH BLOCKED BY DDG RATE LIMIT. Sleeping and retrying (Attempt {attempt+1})...")
                         await asyncio.sleep(3)
                         continue

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
                    return None
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
    url = "https://lite.duckduckgo.com/lite/"
    data = {"q": query}
    
    print(f"  [SEARCH] Looking for price: {symbol}...")
    
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(headers=get_random_headers(), timeout=15) as client:
                response = await client.post(url, data=data)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Check for rate limit
                    if "rate limit" in soup.get_text().lower() or "bot" in soup.get_text().lower():
                         print(f"  [SEARCH] PRICE SEARCH FOR {symbol} BLOCKED BY DDG LITE RATE LIMIT (Attempt {attempt+1}).")
                         await asyncio.sleep(3)
                         continue

                    # Prices are often in the title instead of just the snippet, so we scan the full body text
                    text_blob_upper = soup.get_text(separator=' ').upper()
                    
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
                        return None # found prices but none valid
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

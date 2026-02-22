import asyncio
import json
import os
import sys
import time
import feedparser
import yfinance as yf
from datetime import datetime, timedelta

# Add parent directory to path to import services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration
RSS_FEEDS = [
    "https://news.google.com/rss/search?q=stock+market+news&hl=en-US&gl=US&ceid=US:en",
    "https://feeds.content.dowjones.com/public/rss/mw_top_stories",
    "https://search.yahoo.com/mrss/finance",
    # Indian market specific
    "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",
    "https://www.moneycontrol.com/rss/marketreports.xml",
    # Advanced High-Impact Feeds
    "https://news.google.com/rss/search?q=Short+Seller+Report+Hindenburg",
    "https://news.google.com/rss/search?q=Fed+Chair+Powell+Speech",
    "https://news.google.com/rss/search?q=RBI+Governor+Speech",
    "https://news.google.com/rss/search?q=Earnings+Guidance+Warning",
    "https://news.google.com/rss/search?q=Institutional+Block+Deal+India",
    "https://news.google.com/rss/search?q=Corporate+Bond+Default",
    "https://news.google.com/rss/search?q=Significant+Insider+Trading"
]

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
PENDING_FILE = os.path.join(DATA_DIR, "pending_checks.json")
DATASET_FILE = os.path.join(DATA_DIR, "real_impact_dataset.jsonl")

# Ensure data dir exists
os.makedirs(DATA_DIR, exist_ok=True)

class RealImpactCollector:
    def __init__(self):
        self.pending_checks = self.load_pending()
        self.known_tickers = self.load_ticker_map()
        
    def load_pending(self):
        if os.path.exists(PENDING_FILE):
            try:
                with open(PENDING_FILE, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_pending(self):
        with open(PENDING_FILE, "w") as f:
            json.dump(self.pending_checks, f, indent=2)

    def load_ticker_map(self):
        # Load local map if exists, otherwise basic map
        map_file = os.path.join(DATA_DIR, "company_symbols.json")
        if os.path.exists(map_file):
            with open(map_file, "r") as f:
                return json.load(f)
        return {}

    def extract_company_ticker(self, title):
        """
        Simple heuristic to find company/ticker in title.
        Returns (Company, Ticker) or (None, None).
        """
        title_upper = title.upper()
        
        # Check known map first
        for name, data in self.known_tickers.items():
            if name.upper() in title_upper:
                # Handle different formats if needed
                symbol = data if isinstance(data, str) else data.get('symbol')
                return name, symbol
                
        # Heuristics for common US stocks
        common_stocks = {
            "TESLA": "TSLA", "APPLE": "AAPL", "MICROSOFT": "MSFT", "NVIDIA": "NVDA",
            "AMAZON": "AMZN", "META": "META", "GOOGLE": "GOOGL", "NETFLIX": "NFLX",
            "RELIANCE": "RELIANCE.NS", "TATA MOTORS": "TATAMOTORS.NS", "HDFC": "HDFCBANK.NS",
            "INFOSYS": "INFY.NS", "TCS": "TCS.NS"
        }
        
        for name, ticker in common_stocks.items():
            if name in title_upper:
                return name, ticker
                
        return None, None

    def fetch_price(self, ticker):
        try:
            stock = yf.Ticker(ticker)
            # Fast fetch
            data = stock.history(period="1d")
            if not data.empty:
                return data['Close'].iloc[-1]
        except Exception as e:
            print(f"  [!] Error fetching price for {ticker}: {e}")
        return None

    def save_impact_example(self, example):
        with open(DATASET_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(example) + "\n")
        print(f"  [***] SAVED CONFIRMED IMPACT: {example['company']} ({example['percent_move']}%)")

    async def process_feed(self):
        print("\n[RSS] Fetching feeds...")
        new_items = []
        
        for url in RSS_FEEDS:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries: 
                    # Check duplication
                    if entry.link in self.pending_checks:
                        continue
                        
                    company, ticker = self.extract_company_ticker(entry.title)
                    if ticker:
                        price = self.fetch_price(ticker)
                        if price:
                            print(f"  [+] Tracking: {company} ({ticker}) @ {price}")
                            self.pending_checks[entry.link] = {
                                "news": entry.title,
                                "company": company,
                                "ticker": ticker,
                                "price_start": price,
                                "start_time": time.time(),
                                "sector": "Unknown", # Could identify sector here
                                "date": datetime.now().isoformat()
                            }
                            new_items.append(entry.title)
            except Exception as e:
                print(f"  [!] Feed error {url}: {e}")
        
        if new_items:
            self.save_pending()
        else:
            print("  [.] No new trackable items found.")

    async def verify_impacts(self):
        print("\n[Verify] Checking pending impacts...")
        to_remove = []
        
        for link, data in self.pending_checks.items():
            # Check after 1 hour (3600s)
            elapsed = time.time() - data['start_time']
            
            # For testing/demo purposes, we check sooner (e.g. 5 mins) or actual 1hr
            # The user asked for "1 hour later". 
            if elapsed > 3600: 
                current_price = self.fetch_price(data['ticker'])
                if current_price:
                    move_pct = ((current_price - data['price_start']) / data['price_start']) * 100
                    
                    print(f"  [?] Checking {data['ticker']}: Start {data['price_start']} -> Now {current_price} ({move_pct:.2f}%)")
                    
                    if abs(move_pct) >= 3.0:
                        # Confirmed Impact!
                        impact_type = "positive" if move_pct > 0 else "negative"
                        
                        record = {
                            "news": data['news'],
                            "company": data['company'],
                            "ticker": data['ticker'],
                            "price_before": data['price_start'],
                            "price_after": current_price,
                            "percent_move": round(move_pct, 2),
                            "impact": impact_type,
                            "sector": data['sector'],
                            "date": data['date'],
                            "verified": True
                        }
                        self.save_impact_example(record)
                    else:
                        print(f"  [-] No significant impact ({move_pct:.2f}%)")
                        
                    to_remove.append(link) 
            
            # Clean up old checks (>24h)
            elif elapsed > 86400:
                to_remove.append(link)
                
        # Remove processed
        for link in to_remove:
            del self.pending_checks[link]
            
        if to_remove:
            self.save_pending()

    async def run_loop(self):
        print("--- Real Impact Collector Started ---")
        print(f"Tracking {len(self.pending_checks)} pending items.")
        
        while True:
            await self.process_feed()
            await self.verify_impacts()
            
            print("\n[zZZ] Sleeping 60 minutes...")
            await asyncio.sleep(3600) # 60 mins

if __name__ == "__main__":
    collector = RealImpactCollector()
    asyncio.run(collector.run_loop())

import feedparser

RSS_SOURCES = {
    # ------------------
    # TIER 1: DIRECT INDIAN FINANCIAL WIRES (Fastest, Primary Source)
    # ------------------
    "INDIAN MARKETS (BROAD)": [
        "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",  # ET Markets
        "https://www.moneycontrol.com/rss/MCtopnews.xml", # Moneycontrol Top News
        "https://www.moneycontrol.com/rss/marketreports.xml", # Moneycontrol Market Reports
        "https://www.livemint.com/rss/markets", # Livemint Markets
        "https://www.business-standard.com/rss/markets-106.rss", # Business Standard
        "https://www.thehindubusinessline.com/markets/feeder/default.rss" # Hindu Business Line
    ],
    "INDIAN ECONOMY & POLICY": [
        "https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms", # ET Economy
        "https://www.moneycontrol.com/rss/economy.xml", # MC Economy
        "https://www.livemint.com/rss/economy" # Mint Economy
    ],
    "INDIAN STOCKS (SPECIFIC)": [
        "https://economictimes.indiatimes.com/markets/stocks/news/rssfeeds/2146842.cms", # ET Stock News
        "https://economictimes.indiatimes.com/markets/stocks/earnings/rssfeeds/14605963.cms", # ET Earnings
        "https://www.moneycontrol.com/rss/latestnews.xml" # MC Latest
    ],
    "GLOBAL WIRES (PREMIUM)": [
        "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml", # WSJ Business
        "https://feeds.a.dj.com/rss/RSSMarketsMain.xml", # WSJ Markets
        "http://feeds.bloomberg.com/markets/news.rss", # Bloomberg Markets
        "http://feeds.bloomberg.com/technology/news.rss", # Bloomberg Tech
        "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml", # NYT Business
        "https://www.ft.com/?format=rss" # Financial Times
    ],
    
    # ------------------
    # TIER 2: DIRECT GLOBAL FINANCIAL WIRES
    # ------------------
    "GLOBAL MARKETS": [
        "https://www.reutersagency.com/feed/?best-topics=business&format=xml", # Reuters Business
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664", # CNBC Finance
        "https://finance.yahoo.com/news/rss", # Yahoo Finance Global
        "http://feeds.marketwatch.com/marketwatch/marketalerts", # MarketWatch
        "https://www.investing.com/rss/news_25.rss" # Investing.com Equities
    ],
    "GLOBAL MACRO & FOREX": [
        "https://www.investing.com/rss/news_1.rss", # Investing.com Forex
        "https://www.investing.com/rss/news_14.rss" # Investing.com Economic Indicators
    ],
    "US CORPORATE FILINGS": [
        "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=&company=&dateb=&owner=include&start=0&count=40&output=atom" # SEC Live Filings
    ],

    # ------------------
    # TIER 3: SPECIFIC SECTORS (Direct Feeds where available)
    # ------------------
    "COMMODITIES & METALS": [
        "https://economictimes.indiatimes.com/markets/commodities/news/rssfeeds/11830408.cms", # ET Commodities
        "https://www.investing.com/rss/news_11.rss" # Investing.com Commodities
    ],
    "TECHNOLOGY & AI": [
        "https://economictimes.indiatimes.com/tech/rssfeeds/13357270.cms", # ET IT
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=19854910" # CNBC Tech
    ],
    "BANKING & FINANCE": [
        "https://economictimes.indiatimes.com/industry/banking/finance/rssfeeds/13358259.cms", # ET Banking
        "https://www.moneycontrol.com/rss/business.xml" # Moneycontrol Business Core
    ],
    "ENERGY & OIL": [
        "https://economictimes.indiatimes.com/industry/energy/rssfeeds/13358352.cms", # ET Energy
        "https://www.investing.com/rss/commodities_energy.rss" # Investiging.com Energy
    ],
    "PHARMA & HEALTHCARE": [
        "https://economictimes.indiatimes.com/industry/healthcare/biotech/rssfeeds/13359074.cms" # ET Healthcare
    ],
    "AUTO & EV": [
        "https://economictimes.indiatimes.com/industry/auto/rssfeeds/13357555.cms" # ET Auto
    ],
    "REAL ESTATE & INFRA": [
        "https://economictimes.indiatimes.com/industry/services/property-/-cstruction/rssfeeds/13358998.cms" # ET Property
    ],
    
    # ------------------
    # TIER 4: RAPID KEYWORD SCANNERS (Google News Fallbacks for extreme niches & unlisted anomalies)
    # ------------------
    "EXTREME ANOMALIES": [
        "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListingRss=yes", # SEBI Official Press
        "https://www.investing.com/rss/news_short_selling.rss", # Short Seller Reports
        "https://news.google.com/rss/search?q=Accounting+Fraud+SEBI+Investigation+BSE", # Targeted Fraud Search
        "https://news.google.com/rss/search?q=Trading+Halt+Circuit+Breaker+Hit+NSE" # Targeted Halt Search
    ]
}

def fetch_latest_headlines():
    headlines = []
    seen_titles = set()
    
    print("Fetching RSS feeds...")
    for category, urls in RSS_SOURCES.items():
        print(f"  Category: {category}")
        for url in urls:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]: 
                if entry.title not in seen_titles:
                    headlines.append({
                        "title": entry.title,
                        "link": entry.link,
                        "category": category,
                        "published": entry.published
                    })
                    seen_titles.add(entry.title)
    
    print(f"Fetched {len(headlines)} total headlines.")
    return headlines

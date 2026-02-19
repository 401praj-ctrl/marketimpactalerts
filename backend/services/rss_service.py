import feedparser

RSS_SOURCES = {
    "FINANCIAL MARKETS": [
        "https://news.google.com/rss/search?q=Earnings+Reports+Stock+Market",
        "https://news.google.com/rss/search?q=IPO+News+Market",
        "https://news.google.com/rss/search?q=Mergers+and+Acquisitions+News",
        "https://news.google.com/rss/search?q=Analyst+Ratings+Upgrades+Downgrades",
        "https://news.google.com/rss/search?q=Insider+Trading+Reports"
    ],
    "ECONOMY & MACRO": [
        "https://news.google.com/rss/search?q=Inflation+Interest+Rates+GDP",
        "https://news.google.com/rss/search?q=Recession+Risk+Employment+Data",
        "https://news.google.com/rss/search?q=Currency+Exchange+Rates+Macroeconomics"
    ],
    "GOVERNMENT & POLICY": [
        "https://news.google.com/rss/search?q=Government+Budget+Tax+Changes",
        "https://news.google.com/rss/search?q=Trade+Policy+Sanctions+Regulations",
        "https://news.google.com/rss/search?q=Subsidies+Industry+Bans"
    ],
    "COMMODITIES": [
        "https://news.google.com/rss/search?q=Crude+Oil+Price+Natural+Gas",
        "https://news.google.com/rss/search?q=Gold+and+Precious+Metals+Price",
        "https://news.google.com/rss/search?q=Agriculture+Commodities+Market"
    ],
    "COMPANY EVENTS": [
        "https://news.google.com/rss/search?q=CEO+Resignation+Leadership+Change",
        "https://news.google.com/rss/search?q=Product+Launch+Product+Recall",
        "https://news.google.com/rss/search?q=Corporate+Scandal+Lawsuit+Bankruptcy"
    ],
    "TECHNOLOGY": [
        "https://news.google.com/rss/search?q=Artificial+Intelligence+AI+News",
        "https://news.google.com/rss/search?q=Semiconductor+Chip+Shortage",
        "https://news.google.com/rss/search?q=Cybersecurity+Breach+Software+Update",
        "https://news.google.com/rss/search?q=Big+Tech+Regulation"
    ],
    "GLOBAL EVENTS": [
        "https://news.google.com/rss/search?q=War+Conflict+Geopolitics",
        "https://news.google.com/rss/search?q=International+Sanctions+Trade+Tensions",
        "https://news.google.com/rss/search?q=Political+Instability+Crisis"
    ],
    "ENERGY": [
        "https://news.google.com/rss/search?q=Oil+Production+Power+Shortage",
        "https://news.google.com/rss/search?q=Renewable+Energy+Nuclear+Power"
    ],
    "INDUSTRY SECTOR": [
        "https://news.google.com/rss/search?q=Banking+and+Finance+Sector",
        "https://news.google.com/rss/search?q=Auto+and+Electric+Vehicle+Sector",
        "https://news.google.com/rss/search?q=Real+Estate+Housing+Market",
        "https://news.google.com/rss/search?q=Telecom+and+Infrastructure"
    ],
    "CONSUMER & BRAND": [
        "https://news.google.com/rss/search?q=Brand+Controversy+Boycott",
        "https://news.google.com/rss/search?q=Viral+Campaign+Celebrity+Endorsement"
    ],
    "SOCIAL & VIRAL": [
        "https://news.google.com/rss/search?q=Viral+Video+Social+Media+Trends",
        "https://news.google.com/rss/search?q=Public+Backlash+Trending+News"
    ],
    "SPORTS": [
        "https://news.google.com/rss/search?q=Sports+Sponsorship+Major+Events",
        "https://news.google.com/rss/search?q=Athlete+Endorsement+Deals"
    ],
    "HEALTHCARE": [
        "https://news.google.com/rss/search?q=FDA+Drug+Approval+Vaccine+News",
        "https://news.google.com/rss/search?q=Healthcare+Regulation+Hospital+Policy"
    ],
    "NATURAL DISASTERS": [
        "https://news.google.com/rss/search?q=Flood+Earthquake+Natural+Disaster",
        "https://news.google.com/rss/search?q=Pandemic+Public+Health+Emergency"
    ],
    "LOGISTICS": [
        "https://news.google.com/rss/search?q=Shipping+Issues+Port+Closure",
        "https://news.google.com/rss/search?q=Supply+Chain+Disruption+Shortage"
    ],
    "ESG": [
        "https://news.google.com/rss/search?q=ESG+Sustainability+Climate+Policy",
        "https://news.google.com/rss/search?q=Carbon+Tax+Green+Investment"
    ],
    "CRYPTO": [
        "https://news.google.com/rss/search?q=Bitcoin+Cryptocurrency+Regulation",
        "https://news.google.com/rss/search?q=Web3+Blockchain+DeFi"
    ],
    "DEFENSE": [
        "https://news.google.com/rss/search?q=Defense+Contract+Military+Spending",
        "https://news.google.com/rss/search?q=Defense+Industry+Security+Contract"
    ],
    "INDIAN SECTORS": [
        "https://news.google.com/rss/search?q=Nifty+Bank+News+Stocks",
        "https://news.google.com/rss/search?q=Nifty+IT+Sector+TCS+Infosys",
        "https://news.google.com/rss/search?q=Nifty+Pharma+Sector+Sun+Pharma",
        "https://news.google.com/rss/search?q=Nifty+Auto+Sector+Tata+Motors",
        "https://news.google.com/rss/search?q=Nifty+FMCG+Sector+ITC+HUL",
        "https://news.google.com/rss/search?q=Nifty+Metal+Sector+Tata+Steel",
        "https://news.google.com/rss/search?q=Nifty+Realty+Sector+Real+Estate+India",
        "https://news.google.com/rss/search?q=Nifty+Energy+Reliance+ONGC",
        "https://news.google.com/rss/search?q=Nifty+PSU+Bank+SBI+PNB",
        "https://news.google.com/rss/search?q=Nifty+Media+Sector+Entertainment",
        "https://news.google.com/rss/search?q=Indian+Chemical+Sector+Stocks",
        "https://news.google.com/rss/search?q=Indian+Infrastructure+Construction+Stocks",
        "https://news.google.com/rss/search?q=Nifty+Oil+and+Gas+Sector"
    ],
    "INDIAN TEXTILES": [
        "https://news.google.com/rss/search?q=Indian+Textile+Industry+News",
        "https://news.google.com/rss/search?q=Cotton+Prices+India+Yarn+Exports"
    ],
    "INDIAN SUGAR & ETHANOL": [
        "https://news.google.com/rss/search?q=Sugar+Stocks+India+Ethanol+Policy",
        "https://news.google.com/rss/search?q=Sugar+Production+India+News"
    ],
    "INDIAN RAILWAYS & DEFENSE": [
        "https://news.google.com/rss/search?q=Railway+Stocks+India+Orders",
        "https://news.google.com/rss/search?q=Defense+Sector+India+Contracts"
    ],
    "INDIAN CEMENT & INFRA": [
        "https://news.google.com/rss/search?q=Cement+Prices+India+Construction",
        "https://news.google.com/rss/search?q=Housing+Sales+India+News"
    ],
    "INDIAN GEMS & JEWELLERY": [
        "https://news.google.com/rss/search?q=Gold+Imports+India+Jewellery+Demand",
        "https://news.google.com/rss/search?q=Titan+Kalyan+Jewellers+News"
    ],
    "INDIAN HOSPITALITY & HOTELS": [
        "https://news.google.com/rss/search?q=Indian+Hotel+Industry+News",
        "https://news.google.com/rss/search?q=Hotel+Stocks+India+Occupancy+Rates"
    ],
    "INDIAN NBFC & FINTECH": [
        "https://news.google.com/rss/search?q=NBFC+Sector+India+News",
        "https://news.google.com/rss/search?q=Fintech+India+Regulations+RBI"
    ],
    "PAPER & PACKAGING": [
        "https://news.google.com/rss/search?q=Paper+Industry+India+Prices"
    ],
    "PREMIUM NEWS": [
        "https://www.reutersagency.com/feed/?best-topics=business&format=xml",
        "http://feeds.marketwatch.com/marketwatch/marketalerts",
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664",
        "https://seekingalpha.com/market_currents.xml",
        "https://www.investing.com/rss/news_25.rss",
        "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=&company=&dateb=&owner=include&start=0&count=40&output=atom"
    ],
    "SHORT_SELLER_REPORTS": [
        "https://news.google.com/rss/search?q=Short+Seller+Report+Hindenburg+Muddy+Waters+Citron",
        "https://news.google.com/rss/search?q=Accounting+Fraud+Stock+Manipulation+Allegations"
    ],
    "CENTRAL_BANK_SPEECH": [
        "https://news.google.com/rss/search?q=Powell+Speech+Fed+Chair+Comments",
        "https://news.google.com/rss/search?q=RBI+Governor+Das+Speech+Monetary+Policy",
        "https://news.google.com/rss/search?q=ECB+Lagarde+Speech+Central+Bank"
    ],
    "EARNINGS_EXPECTATION": [
        "https://news.google.com/rss/search?q=Earnings+Guidance+Raised+Lowered",
        "https://news.google.com/rss/search?q=Profit+Warning+Revenue+Forecast+Miss"
    ],
    "INSTITUTIONAL_FLOW": [
        "https://news.google.com/rss/search?q=FII+DII+Data+India+Stock+Market",
        "https://news.google.com/rss/search?q=Block+Deal+Bulk+Deal+NSE+BSE",
        "https://news.google.com/rss/search?q=Institutional+Investor+Selling+Buying"
    ],
    "MARKET_STRUCTURE": [
        "https://news.google.com/rss/search?q=Market+Liquidity+Crisis+Flash+Crash",
        "https://news.google.com/rss/search?q=Trading+Halt+Circuit+Breaker+Hit"
    ],
    "DEMAND_SHOCK": [
        "https://news.google.com/rss/search?q=Demand+Slump+Consumer+Spending+Drop",
        "https://news.google.com/rss/search?q=Supply+Glut+Inventory+Pileup"
    ],
    "CREDIT_EVENTS": [
        "https://news.google.com/rss/search?q=Bond+Default+company+bankruptcy",
        "https://news.google.com/rss/search?q=Credit+Rating+Downgrade+Moodys+S%26P",
        "https://news.google.com/rss/search?q=Debt+Restructuring+Loan+Default"
    ],
    "INSIDER_TRADING": [
        "https://news.google.com/rss/search?q=Significant+Insider+Selling+CEO+CFO",
        "https://news.google.com/rss/search?q=Promoter+Pledge+Revoked+Sold"
    ],
    "SENTIMENT_INDICATORS": [
        "https://news.google.com/rss/search?q=Market+Fear+Greed+Index",
        "https://news.google.com/rss/search?q=VIX+Volatility+Index+Spike",
        "https://news.google.com/rss/search?q=Consumer+Confidence+Index+Drop"
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

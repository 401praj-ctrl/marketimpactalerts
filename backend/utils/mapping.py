
SECTORS = {
    "Banking": ["HDFC Bank", "ICICI Bank", "SBI"],
    "IT": ["TCS", "Infosys", "Wipro"],
    "Auto": ["Tata Motors", "Maruti"],
    "EV": ["Tata Motors", "Olectra"],
    "FMCG": ["HUL", "ITC", "Nestle"],
    "Beverages": ["Coca-Cola", "PepsiCo"],
    "Oil & Gas": ["Reliance", "ONGC", "BPCL"],
    "Pharma": ["Sun Pharma", "Dr Reddy"],
    "Telecom": ["Airtel", "Jio"],
    "Metals": ["Tata Steel", "JSW Steel"],
    "Aviation": ["InterGlobe Aviation", "SpiceJet"],
    "Retail": ["Reliance Retail", "Aditya Birla Fashion"],
    "Infrastructure": ["L&T", "Adani Ports"],
    "Defense": ["HAL", "Bharat Electronics"],
    "Real Estate": ["DLF", "Godrej Properties"],
    "Consumer Durables": ["Titan", "Havells"],
    "E-commerce": ["Amazon", "Flipkart", "Zomato"],
    "Energy": ["Tata Power", "Adani Green"],
    "AI": ["Nvidia", "Microsoft", "Google"],
    "Semiconductor": ["Nvidia", "AMD"],
    "Luxury Brands": ["LVMH", "Hermes"],
    "Sports Sponsorship": ["Nike", "Adidas", "Puma"]
}

STOCKS = {
    "HDFC Bank": "Banking",
    "ICICI Bank": "Banking",
    "SBI": "Banking",
    "TCS": "IT",
    "Infosys": "IT",
    "Wipro": "IT",
    "Tata Motors": "Auto",
    "Maruti": "Auto",
    "Olectra": "EV",
    "HUL": "FMCG",
    "ITC": "FMCG",
    "Nestle": "FMCG",
    "Coca-Cola": "Beverages",
    "PepsiCo": "Beverages",
    "Reliance": "Oil & Gas",
    "ONGC": "Oil & Gas",
    "BPCL": "Oil & Gas",
    "Sun Pharma": "Pharma",
    "Dr Reddy": "Pharma",
    "Airtel": "Telecom",
    "Jio": "Telecom",
    "Apple": "Global Tech",
    "Microsoft": "Global Tech",
    "Google": "Global Tech",
    "Nvidia": "Global Tech",
    "Tesla": "Global Tech",
    "Amazon": "Global Tech"
}

def get_stocks_for_sector(sector):
    return SECTORS.get(sector, [])

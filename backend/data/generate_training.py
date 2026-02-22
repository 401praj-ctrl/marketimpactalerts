import json
import random
import os

companies_and_sectors = [
    # Technology & AI
    ('Apple', 'Technology', 'AAPL', 'positive', 'high'), 
    ('Tesla', 'Automobile', 'TSLA', 'negative', 'high'),
    ('Nvidia', 'Semiconductors', 'NVDA', 'positive', 'high'),
    ('Microsoft', 'Technology', 'MSFT', 'positive', 'high'),
    ('Alphabet', 'Technology', 'GOOGL', 'positive', 'high'),
    ('Meta', 'Social Media', 'META', 'positive', 'high'),
    ('AMD', 'Semiconductors', 'AMD', 'positive', 'high'),
    ('Intel', 'Semiconductors', 'INTC', 'negative', 'medium'),
    
    # E-commerce & Retail
    ('Amazon', 'Retail', 'AMZN', 'positive', 'high'),
    ('Walmart', 'Retail', 'WMT', 'positive', 'medium'),
    ('Target', 'Retail', 'TGT', 'negative', 'medium'),
    ('Alibaba', 'E-commerce', 'BABA', 'neutral', 'low'),
    
    # Finance & Banking
    ('HDFC Bank', 'Banking', 'HDFCBANK', 'neutral', 'low'),
    ('ICICI Bank', 'Banking', 'ICICIBANK', 'positive', 'medium'),
    ('JPMorgan Chase', 'Banking', 'JPM', 'positive', 'medium'),
    ('Goldman Sachs', 'Banking', 'GS', 'positive', 'high'),
    ('Visa', 'Financial Services', 'V', 'positive', 'low'),
    
    # Conglomerates & Heavy Industries
    ('Reliance Industries', 'Conglomerate', 'RELIANCE', 'positive', 'medium'),
    ('Adani Enterprises', 'Conglomerate', 'ADANIENT', 'negative', 'high'),
    ('Tata Motors', 'Automobile', 'TATAMOTORS', 'positive', 'medium'),
    ('Ford', 'Automobile', 'F', 'negative', 'medium'),
    ('Boeing', 'Aerospace', 'BA', 'negative', 'high'),
    ('Lockheed Martin', 'Defense', 'LMT', 'positive', 'medium'),
    
    # Energy
    ('ExxonMobil', 'Energy', 'XOM', 'positive', 'medium'),
    ('Chevron', 'Energy', 'CVX', 'negative', 'medium'),
    ('ONGC', 'Energy', 'ONGC', 'neutral', 'low'),
    
    # Travel & Hospitality
    ('Delta Airlines', 'Aviation', 'DAL', 'negative', 'high'),
    ('United Airlines', 'Aviation', 'UAL', 'positive', 'medium'),
    ('IndiGo', 'Aviation', 'INDIGO', 'positive', 'medium'),
    ('Airbnb', 'Hospitality', 'ABNB', 'positive', 'medium'),
    
    # Pharma & Healthcare
    ('Pfizer', 'Pharmaceuticals', 'PFE', 'positive', 'high'),
    ('Moderna', 'Pharmaceuticals', 'MRNA', 'negative', 'medium'),
    ('Johnson & Johnson', 'Pharmaceuticals', 'JNJ', 'neutral', 'low'),
    ('Sun Pharma', 'Pharmaceuticals', 'SUNPHARMA', 'positive', 'medium'),
    
    # IT Services
    ('Infosys', 'IT Services', 'INFY', 'positive', 'medium'),
    ('TCS', 'IT Services', 'TCS', 'neutral', 'low'),
    ('Wipro', 'IT Services', 'WIPRO', 'negative', 'medium'),
    
    # Entertainment & Media
    ('Netflix', 'Entertainment', 'NFLX', 'positive', 'medium'),
    ('Disney', 'Entertainment', 'DIS', 'negative', 'medium'),
    ('Warner Bros', 'Entertainment', 'WBD', 'negative', 'high')
]

event_templates = [
    # Earnings
    ('{company} reports record Q3 earnings, smashing analyst estimates by 20%', 'Earnings beat expectations', 'positive', 'high'),
    ('{company} misses revenue targets for the second consecutive quarter', 'Earnings miss and weak guidance', 'negative', 'high'),
    ('{company} Q4 results in line with street expectations, maintains full year guidance', 'In-line earnings results', 'neutral', 'low'),
    ('{company} raises annual profit forecast after strong holiday sales', 'Guidance upgrade based on strong performance', 'positive', 'high'),
    ('{company} slashes dividend payout citing cash flow concerns', 'Dividend cut signaling financial distress', 'negative', 'high'),
    ('{company} posts steep unexpected loss in Q1, shares plunge', 'Unexpected earnings net loss', 'negative', 'high'),
    
    # Policy / Regulatory
    ('New government regulations crack down on {sector} monopolies, {company} faces scrutiny', 'Antitrust regulatory pressure', 'negative', 'medium'),
    ('Tax subsidies announced for the {sector} industry, boosting {company} outlook', 'Favorable government policy', 'positive', 'medium'),
    ('{company} hit with massive $2 Billion antitrust fine by European regulators', 'Regulatory penalty and legal risk', 'negative', 'high'),
    ('Supreme Court rules in favor of {company} in landmark patent dispute', 'Positive legal resolution and protective moat', 'positive', 'medium'),
    ('Lawmakers propose strict export bans affecting {company} supply chain', 'Political and regulatory trade restrictions', 'negative', 'high'),
    
    # Geopolitics / Macro
    ('Escalating conflict disrupts {company} supply chains in eastern Europe', 'Geopolitical supply chain disruption', 'negative', 'high'),
    ('Defense contractors see surge in orders, {company} stock rallies', 'Increased defense spending amid conflict', 'positive', 'high'),
    ('Global oil prices surge past $100 a barrel, pressuring {sector} margins like {company}', 'Rising input costs due to oil prices', 'negative', 'high'),
    ('Federal Reserve unexpectedly hikes interest rates by 50 bps, rocking {sector} stocks', 'Macroeconomic tightening', 'negative', 'high'),
    ('Inflation data cools faster than expected, sparking rally in {company} shares', 'Favorable macroeconomic data', 'positive', 'high'),
    ('New tariffs imposed on critical imported materials, hurting {company} manufacturing', 'Tariff and trade war impact', 'negative', 'medium'),
    
    # Mergers / Splitting
    ('{company} announces blockbuster $40 Billion acquisition of rival startup', 'Strategic M&A expansion', 'positive', 'high'),
    ('Regulators block {company} proposed merger, citing antitrust concerns', 'Failed acquisition attempt', 'negative', 'medium'),
    ('{company} announces plan to spin off its struggling division into a new public entity', 'Corporate restructuring and value unlocking', 'positive', 'medium'),
    ('Activist investor pushes for {company} board seats to force immediate sale', 'Activist investor pressure for M&A', 'positive', 'medium'),
    
    # Layoffs / Management
    ('{company} announces 10,000 job cuts in global restructuring effort to boost margins', 'Cost-cutting measures via layoffs', 'positive', 'medium'),
    ('Mass exodus of executives at {company} following internal disputes', 'Leadership instability and talent drain', 'negative', 'high'),
    ('Beloved visionary CEO of {company} announces sudden retirement', 'Leadership transition uncertainty', 'negative', 'medium'),
    ('Former rival executive tapped as new CEO for {company}, turnaround expected', 'Positive leadership change signaling turnaround', 'positive', 'medium'),
    
    # Scandals / Crises
    ('Massive data breach at {company} exposes millions of customer records', 'Cybersecurity failure and reputation damage', 'negative', 'high'),
    ('CEO of {company} resigns amidst accounting fraud investigation', 'Executive scandal and legal risk', 'negative', 'high'),
    ('{company} factories shut down indefinitely after massive labor strike', 'Labor dispute and production halt', 'negative', 'high'),
    ('Whistleblower reveals dangerous cost-cutting at {company}', 'Whistleblower allegations and liability', 'negative', 'high'),
    
    # Products & Operations
    ('{company} unveils revolutionary new AI product, pre-orders sell out instantly', 'Successful product launch driving revenue growth', 'positive', 'high'),
    ('Major safety recall issued for {company}\'s flagship product due to defect', 'Product failure and liability risk', 'negative', 'medium'),
    ('{company} secures landmark 10-year exclusive cloud contract with government', 'Massive revenue contract secured', 'positive', 'high'),
    ('{company} delays highly anticipated product launch to next year', 'Product delay resulting in missed revenue cycles', 'negative', 'medium'),
    
    # Sentiment & Celebrity
    ('Global superstar publicly boycotts {company} products on social media', 'Negative brand sentiment from celebrity influencer', 'negative', 'low'),
    ('Famous athlete signs lifetime endorsement deal with {company}', 'Positive brand association and marketing win', 'positive', 'low'),
    ('Viral TikTok trend causes {company} product to sell out nationwide', 'Unexpected viral marketing success', 'positive', 'medium')
]

modifiers = [
    '', 'unexpectedly', 'surprisingly', 'suddenly', 'finally', 
    'in a shocking move', 'quietly', 'aggressively', 'reluctantly',
    'officially', 'dramatically', 'heavily', 'swiftly', 'cautiously',
    'boldly', 'secretly', 'predictably', 'narrowly', 'massively'
]

# Modifiers for the end of the sentence to increase uniqueness
end_modifiers = [
    'despite market warnings', 'shocking Wall Street', 'according to insiders',
    'in latest press release', 'as analysts predicted', 'causing shares to halt',
    'in a widely expected move', 'sending shockwaves through the market',
    'amidst growing concerns', 'following months of speculation'
]

dataset = []
seen_headlines = set()

TARGET_COUNT = 5000
print(f'Generating {TARGET_COUNT} dataset examples...')

while len(dataset) < TARGET_COUNT:
    comp, sector, symbol, base_impact, base_strength = random.choice(companies_and_sectors)
    headline_template, reason, t_impact, t_strength = random.choice(event_templates)
    
    modifier = random.choice(modifiers)
    modified_comp = f"{comp} {modifier}".strip() if modifier else comp
    
    headline = headline_template.replace('{company}', modified_comp).replace('{sector}', sector)
    
    # Sometimes add an end modifier for even more variety
    if random.random() > 0.5:
        headline = headline + f", {random.choice(end_modifiers)}."
    else:
        headline = headline + "."
    
    # Slight text variation to guarantee uniqueness
    headline = headline + f" [Alert ID: {random.randint(10000, 99999)}]"
    
    if headline in seen_headlines:
        continue
        
    seen_headlines.add(headline)
    
    if t_strength == 'high':
        conf = random.randint(80, 98)
    elif t_strength == 'medium':
        conf = random.randint(60, 80)
    else:
        conf = random.randint(40, 60)
        
    example = {
        "news": headline,
        "event": headline.split(',')[0][:65].strip(),
        "company": comp if '{company}' in headline_template else "",
        "sector": sector if '{sector}' in headline_template or '{company}' in headline_template else "Macro Economy",
        "stocks": [symbol] if '{company}' in headline_template else [],
        "impact": t_impact,
        "strength": t_strength,
        "reason": reason,
        "confidence": conf
    }
    
    dataset.append(example)

output_file = 'training_data.jsonl'
with open(output_file, 'w', encoding='utf-8') as f:
    for item in dataset:
        f.write(json.dumps(item) + '\n')

print(f'Done! Successfully generated and saved {len(dataset)} unique examples to {output_file}')

import json
import random
import os

companies_and_sectors = [
    ('Apple', 'Technology', 'AAPL', 'positive', 'high'), 
    ('Tesla', 'Automobile', 'TSLA', 'negative', 'high'),
    ('Nvidia', 'Semiconductors', 'NVDA', 'positive', 'high'),
    ('Reliance Industries', 'Conglomerate', 'RELIANCE', 'positive', 'medium'),
    ('Tata Motors', 'Automobile', 'TATAMOTORS', 'positive', 'medium'),
    ('HDFC Bank', 'Banking', 'HDFCBANK', 'neutral', 'low'),
    ('Amazon', 'Retail', 'AMZN', 'positive', 'high'),
    ('Microsoft', 'Technology', 'MSFT', 'positive', 'high'),
    ('ExxonMobil', 'Energy', 'XOM', 'positive', 'medium'),
    ('Chevron', 'Energy', 'CVX', 'negative', 'medium'),
    ('Delta Airlines', 'Aviation', 'DAL', 'negative', 'high'),
    ('United Airlines', 'Aviation', 'UAL', 'positive', 'medium'),
    ('Pfizer', 'Pharmaceuticals', 'PFE', 'positive', 'high'),
    ('Moderna', 'Pharmaceuticals', 'MRNA', 'negative', 'medium'),
    ('Infosys', 'IT Services', 'INFY', 'positive', 'medium'),
    ('TCS', 'IT Services', 'TCS', 'neutral', 'low'),
    ('Boeing', 'Aerospace', 'BA', 'negative', 'high'),
    ('Netflix', 'Entertainment', 'NFLX', 'positive', 'medium'),
    ('Disney', 'Entertainment', 'DIS', 'negative', 'medium'),
    ('Meta', 'Social Media', 'META', 'positive', 'high')
]

event_templates = [
    # Earnings
    ('{company} reports record Q3 earnings, smashing analyst estimates by 20%', 'Earnings beat expectations', 'positive', 'high'),
    ('{company} misses revenue targets for the second consecutive quarter', 'Earnings miss and weak guidance', 'negative', 'high'),
    ('{company} Q4 results in line with street expectations, maintains full year guidance', 'In-line earnings results', 'neutral', 'low'),
    # Policy
    ('New government regulations crack down on {sector} monopolies, {company} faces scrutiny', 'Antitrust regulatory pressure', 'negative', 'medium'),
    ('Tax subsidies announced for the {sector} industry, boosting {company} outlook', 'Favorable government policy', 'positive', 'medium'),
    # War/Geopolitics
    ('Escalating conflict disrupts {company} supply chains in eastern Europe', 'Geopolitical supply chain disruption', 'negative', 'high'),
    ('Defense contractors see surge in orders, {company} stock rallies', 'Increased defense spending amid conflict', 'positive', 'high'),
    # Oil/Macro
    ('Global oil prices surge past $100 a barrel, pressuring {sector} margins like {company}', 'Rising input costs due to oil prices', 'negative', 'high'),
    ('Federal Reserve unexpectedly hikes interest rates by 50 bps, rocking {sector} stocks', 'Macroeconomic tightening', 'negative', 'high'),
    ('Inflation data cools faster than expected, sparking rally in {company} shares', 'Favorable macroeconomic data', 'positive', 'high'),
    # Mergers
    ('{company} announces blockbuster $40 Billion acquisition of rival startup', 'Strategic M&A expansion', 'positive', 'high'),
    ('Regulators block {company} proposed merger, citing antitrust concerns', 'Failed acquisition attempt', 'negative', 'medium'),
    # Layoffs/Restructuring
    ('{company} announces 10,000 job cuts in global restructuring effort to boost margins', 'Cost-cutting measures via layoffs', 'positive', 'medium'),
    ('Mass exodus of executives at {company} following internal disputes', 'Leadership instability and talent drain', 'negative', 'high'),
    # Scandals/Crises
    ('Massive data breach at {company} exposes millions of customer records', 'Cybersecurity failure and reputation damage', 'negative', 'high'),
    ('CEO of {company} resigns amidst accounting fraud investigation', 'Executive scandal and legal risk', 'negative', 'high'),
    # Products
    ('{company} unveils revolutionary new AI product, pre-orders sell out instantly', 'Successful product launch driving revenue growth', 'positive', 'high'),
    ('Major safety recall issued for {company}\'s flagship product due to defect', 'Product failure and liability risk', 'negative', 'medium'),
    # Celebrity
    ('Global superstar publicly boycotts {company} products on social media', 'Negative brand sentiment from celebrity influencer', 'negative', 'low'),
    ('Famous athlete signs lifetime endorsement deal with {company}', 'Positive brand association and marketing win', 'positive', 'low')
]

# Generate multiple combinations to reach 1000 items
modifiers = [
    '', 'unexpectedly', 'surprisingly', 'suddenly', 'finally', 
    'in a shocking move', 'quietly', 'aggressively', 'reluctantly',
    'officially', 'dramatically', 'heavily', 'swiftly'
]

dataset = []
seen_headlines = set()

print('Generating 1000 dataset examples...')

while len(dataset) < 1000:
    comp, sector, symbol, base_impact, base_strength = random.choice(companies_and_sectors)
    headline_template, reason, t_impact, t_strength = random.choice(event_templates)
    
    modifier = random.choice(modifiers)
    modified_comp = f"{comp} {modifier}".strip() if modifier else comp
    
    headline = headline_template.replace('{company}', modified_comp).replace('{sector}', sector)
    
    # Slight text variation to guarantee uniqueness
    headline = headline + f" [Report ID: {random.randint(1000, 9999)}]"
    
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
        "event": headline.split(',')[0][:50],
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

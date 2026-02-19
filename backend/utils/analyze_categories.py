import json
from collections import Counter
import re

json_path = r"C:\Users\401pr\.gemini\antigravity\scratch\market_impact_alerts\backend\data\company_names.json"

def analyze_names():
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            names = json.load(f)
            
        words = []
        for name in names:
            # removing 'Limited', 'India', 'The', 'Company', 'Industries'
            clean_name = re.sub(r'\b(Limited|Ltd|India|The|Company|Industries|Services|Solutions|Enterprises|Corporation)\b', '', name, flags=re.IGNORECASE)
            for word in clean_name.split():
                if len(word) > 3:
                    words.append(word.title())
                    
        counter = Counter(words)
        print("Top 30 frequent words in company names:")
        for word, count in counter.most_common(30):
            print(f"{word}: {count}")
            
    except Exception as e:
        print(e)

if __name__ == "__main__":
    analyze_names()

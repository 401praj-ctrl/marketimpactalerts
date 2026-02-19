import pypdf
import json
import re
import os

pdf_path = r"C:\Users\401pr\Downloads\all_india_stock_companies.pdf"
output_path = r"C:\Users\401pr\.gemini\antigravity\scratch\market_impact_alerts\backend\data\company_names.json"

def extract_names():
    print(f"Extracting companies from {pdf_path}...")
    try:
        reader = pypdf.PdfReader(pdf_path)
        companies = set()
        
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if not text: continue
            
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                # Filtering logic
                if not line: continue
                if len(line) < 3: continue # Skip single letters/headers likely
                if "All India Stock Market Companies" in line: continue
                if "Page" in line: continue
                
                # Basic cleaning
                companies.add(line)
        
        # Sort and save
        sorted_companies = sorted(list(companies))
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(sorted_companies, f, indent=2)
            
        print(f"Successfully extracted {len(sorted_companies)} unique company names to {output_path}")
        
    except Exception as e:
        print(f"Extraction failed: {e}")

if __name__ == "__main__":
    extract_names()

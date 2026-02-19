import csv
import json
import os

csv_path = r"C:\Users\401pr\Downloads\attachments (1)\EQUITY_L.csv"
names_output_path = r"C:\Users\401pr\.gemini\antigravity\scratch\market_impact_alerts\backend\data\company_names.json"
symbols_output_path = r"C:\Users\401pr\.gemini\antigravity\scratch\market_impact_alerts\backend\data\company_symbols.json"

def import_equity_data():
    print(f"Importing equity data from {csv_path}...")
    
    # Load existing names
    existing_names = set()
    if os.path.exists(names_output_path):
        with open(names_output_path, 'r', encoding='utf-8') as f:
            existing_names = set(json.load(f))
    
    new_names = set()
    symbol_map = {}
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            # Normalize headers (strip spaces)
            reader.fieldnames = [name.strip() for name in reader.fieldnames]
            
            for row in reader:
                name = row.get('NAME OF COMPANY', '').strip()
                symbol = row.get('SYMBOL', '').strip()
                
                if name and symbol:
                    new_names.add(name)
                    # Create symbol map: Name -> NSE:Symbol
                    symbol_map[name] = f"NSE:{symbol}"
        
        # Merge names
        all_names = sorted(list(existing_names.union(new_names)))
        
        # Save names
        with open(names_output_path, 'w', encoding='utf-8') as f:
            json.dump(all_names, f, indent=2)
            
        # Save symbols
        with open(symbols_output_path, 'w', encoding='utf-8') as f:
            json.dump(symbol_map, f, indent=2)
            
        print(f"Successfully processed {len(new_names)} companies from CSV.")
        print(f"Total unique companies in DB: {len(all_names)}")
        print(f"Generated symbol map with {len(symbol_map)} entries.")
        
    except Exception as e:
        print(f"Import failed: {e}")

if __name__ == "__main__":
    import_equity_data()

import pandas as pd
import json
import os
import re
import csv

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

# Sources
SOURCES = {
    'NSE_MAIN': 'nse_stocks.csv',
    'NSE_SME': 'nse_sme_stocks.csv',
    'NSE_WARRANTS': 'nse_warrants.csv',
    'NSE_PREF': 'nse_pref.csv',
    'NSE_IDR': 'nse_idr.csv',
    'NSE_MF': 'nse_mf.csv',
    'BSE_ALL': 'bse_stocks.csv'
}

SYMBOLS_OUTPUT = os.path.join(DATA_DIR, 'company_symbols.json')
NAMES_OUTPUT = os.path.join(DATA_DIR, 'company_names.json')

def clean_name(name):
    if not isinstance(name, str): return ""
    name = " ".join(name.split()).upper()
    # Remove corporate suffixes
    suffixes = [
        r'\bLIMITED\b', r'\bLTD\b', r'\bPVT\b', r'\bPRIVATE\b', r'\bPUBLIC\b',
        r'\bCORPORATION\b', r'\bCORP\b', r'\bINCORPORATED\b', r'\bINC\b',
        r'\bPLC\b', r'\bHOLDINGS\b', r'\bHLDG\b', r'\bHLDGS\b', r'\bINDIA\b',
        r'\bGROUP\b', r'\bFUND\b', r'\bMF\b', r'\bMANAGEMENT\b', r'\bSERVICES\b'
    ]
    for suf in suffixes:
        name = re.sub(suf, '', name).strip()
    
    # Remove special characters
    name = re.sub(r'[^\w\s]', '', name)
    return " ".join(name.split()).strip()

def process_tickers():
    company_data = {} # clean_name -> set of symbols
    clean_map = {}    # clean_name -> preferred_original_name

    def add_company(raw_name, symbol, board):
        c_clean = clean_name(raw_name)
        if not c_clean: return
        
        if c_clean not in company_data:
            company_data[c_clean] = set()
            clean_map[c_clean] = raw_name
        
        company_data[c_clean].add(f"{board}:{symbol}")

    # Process all NSE files
    for key, filename in SOURCES.items():
        if key.startswith('NSE'):
            path = os.path.join(DATA_DIR, filename)
            if not os.path.exists(path): continue
            
            print(f"Processing {key}: {filename}")
            try:
                # Handle variants in header naming
                df = pd.read_csv(path)
                # Normalize column names
                df.columns = [c.strip().upper().replace('_', ' ') for c in df.columns]
                
                name_col = None
                for possible in ['NAME OF COMPANY', 'ISSUER NAME', 'SECURITY NAME']:
                    if possible in df.columns:
                        name_col = possible
                        break
                
                if name_col and 'SYMBOL' in df.columns:
                    for _, row in df.iterrows():
                        add_company(str(row[name_col]), str(row['SYMBOL']).strip(), 'NSE')
                else:
                    print(f"  WARNING: Could not find name/symbol columns in {filename}. Columns: {df.columns.tolist()}")
            except Exception as e:
                print(f"  Error processing {filename}: {e}")

    # Process BSE
    bse_path = os.path.join(DATA_DIR, SOURCES['BSE_ALL'])
    if os.path.exists(bse_path):
        print(f"Processing BSE All segments: {SOURCES['BSE_ALL']}")
        try:
            with open(bse_path, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f)
                header = [h.strip() for h in next(reader)]
                
                idx_code = header.index('Security Code')
                idx_name = header.index('Issuer Name')
                idx_symbol = header.index('Security Id')
                idx_status = header.index('Status')

                for row in reader:
                    if len(row) <= max(idx_code, idx_name, idx_symbol, idx_status): continue
                    if row[idx_status].strip().upper() != 'ACTIVE': continue
                    
                    raw_name = row[idx_name].strip()
                    symbol = row[idx_symbol].strip() or row[idx_code].strip()
                    add_company(raw_name, symbol, 'BSE')
        except Exception as e:
            print(f"  Error processing BSE: {e}")

    # Final Assembly
    final_symbols = {}
    for c_clean, symbols in company_data.items():
        original_name = clean_map[c_clean]
        final_symbols[original_name] = sorted(list(symbols))

    # Save outputs
    with open(SYMBOLS_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(final_symbols, f, indent=2, sort_keys=True)
    
    with open(NAMES_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(sorted(list(final_symbols.keys())), f, indent=2)

    print(f"\nCOMPLETION SUMMARY:")
    print(f"Total Unique Entities: {len(final_symbols)}")
    nse_count = sum(1 for s in final_symbols.values() if any(i.startswith('NSE:') for i in s))
    bse_count = sum(1 for s in final_symbols.values() if any(i.startswith('BSE:') for i in s))
    both_count = sum(1 for s in final_symbols.values() if any(i.startswith('NSE:') for i in s) and any(i.startswith('BSE:') for i in s))
    
    print(f"  NSE Coverage: {nse_count} entities")
    print(f"  BSE Coverage: {bse_count} entities")
    print(f"  Dual Presence: {both_count} entities")

if __name__ == "__main__":
    process_tickers()

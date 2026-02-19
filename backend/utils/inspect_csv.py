import csv

csv_path = r"C:\Users\401pr\Downloads\attachments (1)\EQUITY_L.csv"

try:
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)
        print(f"Headers: {headers}")
        
        print("First 5 rows:")
        for i, row in enumerate(reader):
            if i >= 5: break
            print(row)
            
except Exception as e:
    print(f"Error reading CSV: {e}")

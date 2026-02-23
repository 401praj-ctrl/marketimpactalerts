import pandas as pd
import os

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
BSE_FILE = os.path.join(DATA_DIR, 'bse_stocks.csv')

def inspect_bse():
    if os.path.exists(BSE_FILE):
        print(f"Inspecting BSE file: {BSE_FILE}")
        try:
            # Read first few lines raw
            with open(BSE_FILE, 'r') as f:
                for _ in range(5):
                    print(f"RAW LINE: {f.readline()}")
            
            df_bse = pd.read_csv(BSE_FILE)
            print("\nHead(5):")
            print(df_bse.head())
            print("\nColumns:")
            print(df_bse.columns.tolist())
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    inspect_bse()

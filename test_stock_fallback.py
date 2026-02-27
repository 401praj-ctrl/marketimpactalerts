import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from services.ai_service import validate_stocks

def test_stock_fallback():
    print("Testing Stock Symbol Fallback Logic...")
    
    # Case 1: Macro news with empty stocks, but sector identified
    sector1 = "Banking & Finance"
    stocks1 = []
    validated1 = validate_stocks(stocks1, sector=sector1)
    print(f"Sector: {sector1} | Stocks: {stocks1} -> Validated: {validated1}")
    
    # Case 2: IT news with invalid symbols
    sector2 = "IT Services"
    stocks2 = ["Some Unknown IT Company"]
    validated2 = validate_stocks(stocks2, sector=sector2)
    print(f"Sector: {sector2} | Stocks: {stocks2} -> Validated: {validated2}")

    # Case 3: Direct news (No fallback needed if stocks exist)
    sector3 = "Energy"
    stocks3 = ["NSE:RELIANCE"]
    validated3 = validate_stocks(stocks3, sector=sector3)
    print(f"Sector: {sector3} | Stocks: {stocks3} -> Validated: {validated3}")

    assert "NSE:SBIN" in validated1
    assert "NSE:TCS" in validated2
    assert "RELIANCE" in validated3 # RELIANCE is in VALID_SYMBOLS
    print("\nALL STOCK FALLBACK TESTS PASSED!")

if __name__ == "__main__":
    test_stock_fallback()

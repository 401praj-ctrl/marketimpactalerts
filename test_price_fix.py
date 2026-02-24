import asyncio
import os
import sys

# Add backend directory to sys.path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from services.price_service import price_service

async def test_price_fetching():
    symbols = ["NSE:KALYANKJIL", "NSE:HDFCBANK", "BSE:500325", "NSE:TCS"]
    print("Testing Price Service (yfinance)...")
    print("-" * 30)
    
    for symbol in symbols:
        price = await price_service.get_live_price(symbol)
        if price:
            print(f"SUCCESS: {symbol} -> ₹{price}")
        else:
            print(f"FAILED:  {symbol} -> No price found")

if __name__ == "__main__":
    asyncio.run(test_price_fetching())

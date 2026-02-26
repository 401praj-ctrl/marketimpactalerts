import asyncio
import sys

sys.path.append(".")
from services.price_service import price_service

async def main():
    print("Testing NSE:HINDALCO for 2026-02-19:")
    p = await price_service.get_historical_price("NSE:HINDALCO", "2026-02-19")
    print(p)

    print("Testing NSE:HINDALCO for 2026-02-22:")
    p = await price_service.get_historical_price("NSE:HINDALCO", "2026-02-22")
    print(p)
    
    print("Testing HSBC for 2026-02-25:")
    p = await price_service.get_historical_price("HSBC", "2026-02-25")
    print(p)

asyncio.run(main())

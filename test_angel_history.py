import os
import asyncio
from dotenv import load_dotenv

# Load the environment variables from the .env file
load_dotenv(os.path.join(os.path.dirname(__file__), "backend", ".env"))

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from services.price_service import price_service

async def test_historical():
    await price_service._ensure_token_list()
    if not await price_service.authenticate():
        print("Auth failed")
        return
        
    symbol = "NSE:RELIANCE"
    token_info = price_service.token_map.get("RELIANCE-EQ")
    if token_info:
        param = {
            "exchange": token_info['exch'],
            "symboltoken": token_info['token'],
            "interval": "ONE_DAY",
            "fromdate": "2023-10-10 09:00",
            "todate": "2023-10-15 15:30"
        }
        res = price_service.smart_api.getCandleData(param)
        print("Historical Response:", res)

if __name__ == "__main__":
    asyncio.run(test_historical())

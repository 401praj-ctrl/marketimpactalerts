import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from services.ai_service import perform_deep_analysis

async def test():
    prices = {"RELIANCE": 1393.9}
    res = await perform_deep_analysis(
        "Reliance Industries signs major new deal expanding energy sector footprint. Expect huge volume and revenue next year.", 
        "Reliance signs deal", 
        current_prices=prices
    )
    print("DEEP ANALYSIS RESULT:", res)

if __name__ == "__main__":
    asyncio.run(test())

import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from services.price_service import price_service

async def test():
    # Mock AI response missing price
    analysis = {
        'stocks': ['NSE:RELIANCE', 'NSE:HDFCBANK'],
        'impact_direction': 'positive',
        'probability': 85,
        'tier': 'Tier-1'
    }

    current_prices = {}
    for symbol in analysis.get('stocks', []):
        price = await price_service.get_live_price(symbol)
        if price:
            current_prices[symbol] = price

    print("CURRENT PRICES FETCHED:", current_prices)

    if not analysis.get('live_price') and current_prices:
        first_symbol = analysis.get('stocks', [None])[0]
        if first_symbol and first_symbol in current_prices:
            analysis['live_price'] = current_prices[first_symbol]

    print("FINAL LIVE PRICE:", analysis.get('live_price'))

if __name__ == "__main__":
    asyncio.run(test())

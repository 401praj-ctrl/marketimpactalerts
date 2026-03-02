import asyncio
import sys
import os

# Ensure we can import from the backend directory
sys.path.append(os.path.join(os.getcwd(), "backend"))

from services.search_service import search_ticker_online, search_price_online
from services.price_service import PriceService
from services.ai_service import validate_stocks

async def test_online_ticker():
    print("\n--- Testing Online Ticker Search ---")
    company = "Clean Max Enviro Energy Solutions"
    tickers = await search_ticker_online(company)
    print(f"Company: {company} -> Found Tickers: {tickers}")
    return tickers

async def test_online_price():
    print("\n--- Testing Online Price Search ---")
    symbol = "Clean Max Enviro Energy"
    price = await search_price_online(symbol)
    print(f"Symbol: {symbol} -> Found Price: {price}")
    return price

async def test_integrated_validation():
    print("\n--- Testing Integrated validate_stocks Fallback ---")
    # This should trigger the final company name fallback if no ticker found
    stocks = await validate_stocks([], company_name="Tata Play")
    print(f"Validated Stocks for 'Tata Play': {stocks}")
    return stocks

async def run_tests():
    await test_online_ticker()
    await test_online_price()
    await test_integrated_validation()

if __name__ == "__main__":
    asyncio.run(run_tests())

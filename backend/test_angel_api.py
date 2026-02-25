import os
import asyncio
from services.price_service import price_service

async def test_connection():
    print("--- Angel One Connection Test ---")
    
    # Check credentials
    print(f"API KEY: {os.environ.get('ANGEL_API_KEY')[:5]}...")
    print(f"USER ID: {os.environ.get('ANGEL_USER_ID')}")
    
    # Test Login
    success = await price_service.authenticate()
    if success:
        print("SUCCESS: Logged into Angel One.")
        
        # Test Price Fetch (RELIANCE)
        print("\nTesting Price Fetch for RELIANCE.NS...")
        price = await price_service.get_live_price("NSE:RELIANCE")
        if price:
            print(f"SUCCESS: Current Price for RELIANCE: ₹{price}")
        else:
            print("FAILED: Could not fetch price for RELIANCE.")
            
        # Test Price Fetch for Angel One itself
        print("\nTesting Price Fetch for ANGELONE.NS...")
        price = await price_service.get_live_price("NSE:ANGELONE")
        if price:
            print(f"SUCCESS: Current Price for ANGELONE: ₹{price}")
        else:
            print("FAILED: Could not fetch price for ANGELONE.")
    else:
        print("FAILED: Authentication failed. Check your API Key, ID, Password, and TOTP Secret.")

if __name__ == "__main__":
    asyncio.run(test_connection())

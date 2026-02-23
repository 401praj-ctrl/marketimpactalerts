import sys
import os
import asyncio
import json

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ai_service import analyze_headline, perform_deep_analysis

async def test_classification():
    headline = "HDFC Bank reports 20% surge in Q3 profit, beating estimates"
    print(f"Testing headline analysis: {headline}")
    
    # Pass 1
    result1 = await analyze_headline(headline)
    print(f"Pass 1 result: {json.dumps(result1, indent=2)}")
    
    if "impact_type" in result1:
        print(f"SUCCESS: impact_type found in Pass 1: {result1['impact_type']}")
    else:
        print("FAILED: impact_type missing in Pass 1")

    # Pass 2
    full_content = "HDFC Bank, India's largest private sector lender, reported a 20% year-on-year increase in its net profit for the third quarter... Net interest income grew by 15%..."
    result2 = await perform_deep_analysis(full_content, headline)
    print(f"Pass 2 result: {json.dumps(result2, indent=2)}")
    
    if result2 and "impact_type" in result2:
        print(f"SUCCESS: impact_type found in Pass 2: {result2['impact_type']}")
    else:
        print("FAILED: impact_type missing or result null in Pass 2")

if __name__ == "__main__":
    if not os.environ.get("OPENROUTER_API_KEY_1"):
        print("Set OPENROUTER_API_KEY_1 to run this test with live AI.")
        # We can still check the prompt logic manually if needed, 
        # but let's assume we want to see it work.
    asyncio.run(test_classification())

import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from services.ai_service import analyze_headline

async def main():
    headline = "Reliance Industries announces a massive $5 billion deal to acquire a major tech company, stock expected to surge."
    print("Analyzing headline:", headline)
    res = await analyze_headline(headline)
    print("Result:", res)

if __name__ == "__main__":
    asyncio.run(main())

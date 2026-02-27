import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from main import run_analysis, save_processed, processed_links

async def trigger():
    print("Triggering Fresh Analysis for Today's Alerts...")
    
    # Optional: Clear a few specific links to ensure they are re-processed if needed
    # but run_analysis usually handles new ones.
    
    await run_analysis(source="USER_REQUESTED")
    print("Analysis cycle complete. Check cached_alerts.json for results.")

if __name__ == "__main__":
    asyncio.run(trigger())

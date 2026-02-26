import asyncio
import sys

sys.path.append(".")
from services.prediction_tracker import tracker

async def main():
    await tracker.run_cleanup_and_verification(source="manual")

asyncio.run(main())

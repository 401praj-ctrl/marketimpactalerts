import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from bytez import Bytez

bytez_key = os.environ.get("BYTEZ_API_KEY_1")

prompt = """
You are a fast market analyst. 
Read the event: "RBI cuts interest rates unexpectedly".
Return strictly a JSON response with:
- "impact": "high"
- "direction": "up"
- "stocks": ["NSE:SBIN", "NSE:HDFCBANK"]
"""

async def test_qwen():
    if not bytez_key:
        print("No BYTES API key.")
        return

    sdk = Bytez(bytez_key)
    model = sdk.model("Qwen/Qwen2.5-1.5B-Instruct")
    
    print("Testing Qwen on Bytez...")
    try:
        results = model.run([{"role": "user", "content": prompt}])
        raw_output = None
        if results and hasattr(results, 'output') and results.output:
            raw_output = results.output
        elif isinstance(results, dict) and 'output' in results:
            raw_output = results['output']
        elif isinstance(results, str):
            raw_output = results
            
        print("RAW STRING DUMP:")
        print(repr(raw_output))
        print("---")
        print(raw_output)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_qwen())

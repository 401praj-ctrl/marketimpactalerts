import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

from bytez import Bytez

bytez_key = os.environ.get("BYTEZ_API_KEY_1")

models_to_test = [
    "google/gemma-3-4b-it",
    "openai/gpt-3.5-turbo-1106"
]

prompt = """
You are a fast market analyst. 
Read the event: "RBI cuts interest rates unexpectedly".
Return strictly a JSON response with:
- "impact": "high"
- "direction": "up"
- "stocks": ["NSE:SBIN", "NSE:HDFCBANK"]
"""

async def test_bytez_models():
    print(f"Testing Bytez API with Key ending in ...{bytez_key[-4:] if bytez_key else 'None'}")
    if not bytez_key:
        print("No BYTES API key found.")
        return

    sdk = Bytez(bytez_key)
    
    for model_name in models_to_test:
        print(f"\nTesting model: {model_name}")
        try:
            model = sdk.model(model_name)
            loop = asyncio.get_event_loop()
            results = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: model.run([{"role": "user", "content": prompt}])),
                timeout=20.0
            )
            
            raw_output = None
            if results and hasattr(results, 'output') and results.output:
                raw_output = results.output
            elif isinstance(results, dict) and 'output' in results:
                raw_output = results['output']
            elif isinstance(results, str):
                raw_output = results
            
            print("Successfully received response:")
            print("-" * 20)
            print(raw_output)
            print("-" * 20)
            
        except Exception as e:
            print(f"Error testing model {model_name}: {e}")

if __name__ == "__main__":
    asyncio.run(test_bytez_models())

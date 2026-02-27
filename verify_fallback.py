import asyncio
import os
import sys
import json
from unittest.mock import patch, MagicMock

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Inject dummy keys into environment BEFORE importing ai_service
os.environ["OPENROUTER_API_KEY_1"] = "sk-or-test-key-1"
os.environ["BYTEZ_API_KEY_1"] = "bytez-test-key-1"

import services.ai_service as ai_service

async def test_fallback():
    print("STARTING FALLBACK VERIFICATION TEST")
    print("-" * 50)
    
    # Force some keys into the service lists if they were empty
    if not ai_service.API_KEYS:
        ai_service.API_KEYS = ["sk-or-test-key-1"]
    if not ai_service.BYTEZ_API_KEYS:
        ai_service.BYTEZ_API_KEYS = ["bytez-test-key-1"]

    # 1. Mock OpenRouter to always fail with 429
    mock_response = MagicMock()
    mock_response.status_code = 429
    
    # Mock httpx.AsyncClient.post with an async return value
    async def mock_post(*args, **kwargs):
        return mock_response
    
    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        # Also mock Bytez to succeed via its own SDK
        with patch("services.ai_service.Bytez") as mock_bytez_class:
            mock_bytez_instance = MagicMock()
            mock_bytez_class.return_value = mock_bytez_instance
            mock_model = MagicMock()
            mock_bytez_instance.model.return_value = mock_model
            
            # Mock the model output
            mock_result = MagicMock()
            mock_result.output = json.dumps({
                "impact": "high",
                "event": "Fallback Test",
                "company": "Bytez Corp",
                "sector": "Cloud",
                "stocks": ["NSE:RELIANCE"],
                "probability": 80
            })
            mock_model.run.return_value = mock_result

            print("TEST 1: Pass 1 (Headline Analysis) Fallback")
            print("Action: Simulating OpenRouter 429 Failure...")
            result = await ai_service.analyze_headline("Major tech breakthrough in AI infrastructure")
            
            if result and result.get("event") == "Fallback Test":
                print("SUCCESS: Correctly fell back to Bytez after OpenRouter failed.")
            else:
                print(f"FAILURE: Result was {result}")

            print("\nTEST 2: Pass 2 (Deep Analysis) Fallback")
            print("Action: Simulating OpenRouter 429 Failure...")
            # perform_deep_analysis uses deep results
            deep_result = await ai_service.perform_deep_analysis("Full content", "Major tech breakthrough")
            
            if deep_result and deep_result.get("event") == "Fallback Test":
                print("SUCCESS: Correctly fell back to Bytez for Deep Analysis.")
            else:
                print(f"FAILURE: Result was {deep_result}")

if __name__ == "__main__":
    asyncio.run(test_fallback())

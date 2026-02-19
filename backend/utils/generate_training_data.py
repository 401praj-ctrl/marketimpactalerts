import asyncio
import json
import os
import sys
import random
import httpx

# Add parent directory to path to import services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ai_service import analyze_headline, API_KEYS, MODELS

OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "training_examples.json")

SECTORS = [
    "Indian Banking", "Global Tech", "Energy & Oil", "Indian Infrastructure", 
    "Pharma & Healthcare", "Automobile (EV/Traditional)", "Crypto & Fintech", 
    "Retail & FMCG", "Defense & Aerospace", "Commodities (Gold/Silver)"
]

async def generate_synthetic_headlines(batch_size=10):
    """
    Asks AI to hallucinate realistic financial news headlines.
    """
    sector = random.choice(SECTORS)
    prompt = f"""
    Generate {batch_size} realistic, distinct financial news headlines likely to impact stock markets.
    Focus on: {sector}.
    Include a mix of: Earnings, Regulatory Action, Mergers, Macro Data, and Geopolitical events.
    Make them sound like real Bloomberg/Reuters headlines.
    Return ONLY the headlines, one per line. No numbering.
    """
    
    print(f"\n[Generator] Brainstorming {batch_size} headlines for {sector}...")
    
    async with httpx.AsyncClient() as client:
        # Use a random key/model to spread load
        key = random.choice([k for k in API_KEYS if k])
        model = "openai/gpt-3.5-turbo" 
        
        try:
            response = await client.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:8000",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=30
            )
            
            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                headlines = [line.strip() for line in content.split('\n') if line.strip() and not line[0].isdigit()]
                return headlines
            else:
                print(f"[!] Gen Error: {response.status_code}")
                return []
        except Exception as e:
            print(f"[!] Gen Exception: {e}")
            return []

async def generate_examples(target_count=1000):
    print(f"--- Starting Infinite Data Generator ---")
    print(f"Subject: Global & Indian Markets")
    print(f"Target Database Size: {target_count}")
    
    while True:
        # Load existing count
        existing_data = []
        if os.path.exists(OUTPUT_FILE):
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        
        current_count = len(existing_data)
        if current_count >= target_count:
            print(f"\n[!!!] Target Reached! Total Database Size: {current_count}")
            break
            
        print(f"\n[Status] Current Examples: {current_count}")
        
        # 1. Generate Headlines
        headlines = await generate_synthetic_headlines(batch_size=5)
        
        new_batch = []
        
        # 2. Analyze & Label
        for news in headlines:
            # Skip duplicates
            if any(d.get("news") == news for d in existing_data):
                continue
                
            print(f"  > Analyzing: {news[:60]}...")
            try:
                # Use the AI service (which now uses RAG-lite itself!) to label the new data
                # This creates a flywheel effect: AI gets smarter -> creates better data -> AI gets smarter
                result = await analyze_headline(news)
                
                if result and result.get("impact") != "no impact":
                    result["news"] = news
                    new_batch.append(result)
                    print(f"    [+] Created Example: {result['event']} (Conf: {result.get('confidence')}%)")
                else:
                    print(f"    [-] Skipped (No Impact/Low Conf)")
                    
            except Exception as e:
                print(f"    [!] Error analyzing: {e}")
                
            await asyncio.sleep(1) # Rate limit
            
        # 3. Save Batch
        if new_batch:
            existing_data.extend(new_batch)
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(existing_data, f, indent=2)
            print(f"[Save] Saved {len(new_batch)} new examples.")
        
        await asyncio.sleep(2)

if __name__ == "__main__":
    # Default to 100 for this run, user can edit to 1000
    asyncio.run(generate_examples(target_count=1000))

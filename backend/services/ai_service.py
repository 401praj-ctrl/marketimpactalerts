import httpx
import json
import re
import os
import asyncio
import datetime
import math
from dotenv import load_dotenv
from thefuzz import process
from bytez import Bytez

# Environment variables are managed by main.py
# Only load here if running standalone
if not os.environ.get("OPENROUTER_API_KEY_1"):
    load_dotenv()


# Load company names for validation
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPANY_NAMES = []
COMPANY_SYMBOLS = {}
try:
    names_path = os.path.join(BASE_DIR, "data", "company_names.json")
    if os.path.exists(names_path):
        with open(names_path, "r", encoding="utf-8") as f:
            COMPANY_NAMES = json.load(f)
        print(f"Loaded {len(COMPANY_NAMES)} company names for validation.")
    
    symbols_path = os.path.join(BASE_DIR, "data", "company_symbols.json")
    if os.path.exists(symbols_path):
        with open(symbols_path, "r", encoding="utf-8") as f:
            COMPANY_SYMBOLS = json.load(f)
        print(f"Loaded {len(COMPANY_SYMBOLS)} symbol mappings.")

    # Load stock profiles for sensitivity context
    STOCK_PROFILES = {}
    profiles_path = os.path.join(BASE_DIR, "data", "stock_profiles.json")
    if os.path.exists(profiles_path):
        with open(profiles_path, "r", encoding="utf-8") as f:
            STOCK_PROFILES = json.load(f)
        print(f"Loaded {len(STOCK_PROFILES)} stock profiles.")
except Exception as e:
    print(f"Warning: Could not load data: {e}")


def validate_company_name(name):
    """
    Fuzzy matches the AI-generated company name against the official list.
    Returns the official name if a high-confidence match is found.
    """
    if not name or not COMPANY_NAMES: return name
    
    # Quick exact match check
    if name in COMPANY_NAMES: return name
    
    # Fuzzy match
    match, score = process.extractOne(name, COMPANY_NAMES)
    if score >= 85: # High confidence threshold
        # print(f"  DEBUG: Corrected '{name}' -> '{match}' (Score: {score})")
        return match
    return name

# Updated API Keys logic: Find ALL OpenRouter keys dynamically and sort them
_openrouter_keys = {}
for key, value in os.environ.items():
    if key.startswith("OPENROUTER_API_KEY") and value and value.strip():
        _openrouter_keys[key] = value.strip()

# Sort by key name (e.g., KEY_1, KEY_2) for consistent order
API_KEYS = [v for k, v in sorted(_openrouter_keys.items())]

if not API_KEYS:
    print("WARNING: No OpenRouter API keys found in environment.")
    API_KEYS = []
else:
    print(f"DEBUG: Successfully loaded {len(API_KEYS)} unique OpenRouter API keys.")
    for i, val in enumerate(API_KEYS):
        print(f"  Key {i+1}: {val[:6]}...{val[-4:]}")

# Bytez API Keys Support: Find ALL Bytez keys dynamically and sort them
_bytez_keys = {}
for key, value in os.environ.items():
    if key.startswith("BYTEZ_API_KEY") and value and value.strip():
        _bytez_keys[key] = value.strip()

BYTEZ_API_KEYS = [v for k, v in sorted(_bytez_keys.items())]

if BYTEZ_API_KEYS:
    print(f"DEBUG: Successfully loaded {len(BYTEZ_API_KEYS)} unique Bytez API keys.")
    for i, val in enumerate(BYTEZ_API_KEYS):
        print(f"  Bytez Key {i+1}: {val[:6]}...{val[-4:]}")
else:
    print("DEBUG: No Bytez API keys found.")

# Models in order of preference: Exclusive free models as requested
MODELS = [
    "google/gemma-3-12b-it:free",
    "openai/gpt-oss-20b:free",
    "mistralai/mistral-7b-instruct:free", # Safety fallback to avoid Bytez unless necessary
]


# Load training examples from multiple sources
TRAINING_EXAMPLES = []
try:
    # Source 1: Large synthetic dataset (5000 entries)
    jsonl_path = os.path.join(BASE_DIR, "data", "training_data.jsonl")
    if os.path.exists(jsonl_path):
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    TRAINING_EXAMPLES.append(json.loads(line))
    
    # Source 2: Real-world curated examples (900+ entries)
    json_path = os.path.join(BASE_DIR, "data", "training_examples.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            extra_examples = json.load(f)
            if isinstance(extra_examples, list):
                TRAINING_EXAMPLES.extend(extra_examples)
                
    print(f"Loaded {len(TRAINING_EXAMPLES)} total training examples from multiple sources.")
except Exception as e:
    print(f"Warning: Could not load training examples: {e}")


def clean_json_string(content: str) -> str:
    if not isinstance(content, str): return ""
    if '```json' in content: content = content.split('```json')[1]
    if '```' in content: content = content.split('```')[0]
    content = content.strip()
    # Remove trailing commas before closing braces/brackets that cause JSONDecodeError
    content = re.sub(r',\s*([}\]])', r'\1', content)
    return content

def get_relevant_examples(headline, limit=3, regime="NORMAL"):
    """
    Returns the most relevant training examples for a given headline.
    Uses keyword matching + Regime-Aware Time-Decay Weighting.
    """
    if not TRAINING_EXAMPLES: return []
    
    keywords = set(headline.lower().split())
    current_date = datetime.datetime.now()
    scored_examples = []
    
    # Lambda (Decay Rate) shifts based on Regime
    # NORMAL: 0.5 (~40% after 2 years)
    # HIGH_VOLATILITY: 1.5 (~5% after 2 years) -> Prioritize ultra-recent news during crises.
    decay_lambda = 0.5
    if regime == "HIGH_VOLATILITY":
        decay_lambda = 1.5
    
    for ex in TRAINING_EXAMPLES:
        # Match against news, sector, or reason keywords
        content = (ex.get('news', '') + " " + ex.get('sector', '') + " " + ex.get('reason', '')).lower()
        keyword_matches = sum(1 for k in keywords if k in content and len(k) > 3)
        if keyword_matches == 0: continue
        
        # Recency Weighting: e^(-lambda * YearsAgo)
        recency_weight = 1.0
        if 'date' in ex:
            try:
                ex_date = datetime.datetime.strptime(ex['date'], '%Y-%m-%d')
                years_ago = (current_date - ex_date).days / 365.25
                recency_weight = math.exp(-decay_lambda * years_ago)
            except: pass
            
        final_score = keyword_matches * recency_weight
        scored_examples.append((final_score, ex))
        
    scored_examples.sort(key=lambda x: x[0], reverse=True)
    return [ex for score, ex in scored_examples[:limit]]

# Track keys that are out of credits to avoid retrying them in the same session
depleted_keys = set()
# Track keys that failed in the current analysis cycle
cycle_failed_keys = set()

def start_new_cycle():
    """Reset the per-cycle failure tracking."""
    global cycle_failed_keys
    print("  DEBUG: Starting new analysis cycle - Resetting per-cycle API key blacklists.")
    cycle_failed_keys.clear()

async def analyze_headline(headline_text, regime="NORMAL"):
    # Enforce IST (UTC +5:30) for accurate Indian context mapping
    ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    current_date = ist_now.strftime("%Y-%m-%d")
    
    # RAG-lite: Fetch relevant training examples
    relevant_examples = get_relevant_examples(headline_text, limit=3, regime=regime)
    examples_text = ""
    for i, ex in enumerate(relevant_examples):
        # Dynamically inject current date to prevent AI from copying hardcoded old dates
        if "event_date" in ex: ex["event_date"] = current_date
        if "impact_date_est" in ex: ex["impact_date_est"] = current_date
        examples_text += f"\n    Example {i+1}:\n    News: {ex.get('news')}\n    Output: {json.dumps(ex)}\n"

    prompt = f"""
    Today's Date: {current_date}
    You are an AI that detects whether a news event may impact publicly traded stocks or sectors.
    Analyze the news and return a structured JSON response.

    FINANCIAL THEORIES & MARKET LOGIC TO APPLY:
    1. Efficient Market Hypothesis (EMH) [Eugene Fama]: In an efficient market, prices instantly incorporate all available info. News doesn't just affect price; price is the sum of past news. You must determine if this news is genuinely new information or already priced in.
    2. Abnormal Returns (AR) Formula: AR = Actual Return - Expected Return. Think: What should the stock have done vs what will this news make it do? Positive AR means news is "better than expected". Zero AR means "priced in".
    3. The "Drift" Effect (PEAD) [Ball & Brown, 1968]: Post-Earnings Announcement Drift. Stocks don't react instantly to massive surprises; they drift in that direction for weeks. News has a "long tail" impact.
    5. Sector Contagion: A bankruptcy drags down a sector but benefits direct competitors. Supply chain breaks hurt downstream.
    6. Global to Local Contagion: Foreign macroeconomic news (US Fed rates, China slowdowns, Middle East conflicts) heavily impacts Indian domestic markets. Identify HOW a foreign event directly or indirectly affects Indian sectors (e.g., "US Tech slowdown" -> impacts "Indian IT Services").
    7. Domestic Sensitivity: Local Indian news (RBI rate changes, monsoon data, government policies, local elections) has direct, intense impacts on domestic stocks.

    THE MASTER FORMULA: 7-MODULE IMPACT SCORING
    You MUST calculate the impact using this exact professional framework.
    
    1. Impact Strength Tiering:
    - Tier-1: Direct Earnings Impact (M&A, Govt Tax, Major Contract) ➔ VERY HIGH Impact.
    - Tier-2: Sector Impact (Industry trends, Sector-wide regulations) ➔ MEDIUM Impact.
    - Tier-3: Macro Sentiment (Global trends, Geopolitics, General news) ➔ LOW Impact.

    2. Master Formula (Non-Linear Interaction):
    ImpactScore = (DirectRevenueLink * 0.4) + (SectorRelevance * 0.25) + (MarketSentiment * 0.2) + (LiquiditySensitivity * 0.15) + (0.1 * DirectRevenueLink * MarketSentiment)
    
    Values are 0.0 to 1.0. If Final Score < 0.4 ➔ Return "no impact".
    The interaction term (0.1 * Direct * Sentiment) captures non-linear reaction spikes where news intensity multiplies sentiment.

    3. Stock Sensitivity:
    Consider the stock's profile: Sector, Export exposure, Global beta, Liquidity, and Market Cap. 
    Small-cap stocks with low liquidity should have REDUCED prediction confidence to avoid volatility noise.

    4. Market Context & Momentum:
    - If VIX is high ➔ Amplify impact.
    - If Market is bullish ➔ Reduce negative impact significance.
    - If Earnings season ➔ Filter out macro noise.

    5. Multi-Signal Check:
    News sentiment must be CROSS-REFERENCED with existing trends. 

    6. Confidence Calibration (STRICT):
    - Tier-1 (Strong Direct News) ➔ 70-80% Probability.
    - Tier-2 (Medium Sector News) ➔ 55-65% Probability.
    - Tier-3 (Weak Macro News) ➔ 20-35% Probability.
    NEVER give > 80% unless it is a catastrophic or guaranteed massive earnings event.

    RULES:
    1. Identify the EVENT, COMPANY, SECTOR, and TIER.
    2. If the news is Tier-3 or macro noise, avoid high probability moves.
    3. If the news is FOREIGN, identify the Indian sector linkage (Tier-2).
    4. "probability" MUST reflect the Tier Calibration rules above.

    TRAINING EXAMPLES (Relevant to this news):
    {examples_text}

    TODAY IS: {current_date}.
    
    Return JSON only in this REQUIRED format:
    {{
     "event": "Short title of the event",
     "company": "Primary Indian company (if any)",
     "sector": "Indian sector affected",
     "stocks": ["NSE:SYMBOL", ...],
     "impact_direction": "UP/DOWN/NEUTRAL",
     "impact_description": "2 sentence explanation",
     "event_date": "YYYY-MM-DD",
     "impact_date_est": "YYYY-MM-DD",
     "probability": 1-100,
     "tier": "Tier-1/Tier-2/Tier-3",
     "impact_score": 0.0-1.0,
     "reason": "Brief financial reasoning",
     "impact": "positive/negative/neutral",
     "strength": "low/medium/high",
     "confidence": 1-100,
     "impact_type": "Direct/Indirect"
    }}

    If no stock impact → return {{"impact":"no impact"}}.
    
    CRITICAL: YOU MUST RESPOND ONLY WITH RELEVANT JSON. NO MARKDOWN. NO BACKTICKS. NO OTHER TEXT.

    Headline: "{headline_text}"
    """
    
    print(f"  DEBUG: Prompting AI for: {headline_text[:50]}...")
    
    async with httpx.AsyncClient(timeout=35.0) as client:
        # Multi-layer fallback: Try Primary Model with all keys, then Backup Model with all keys
        for model_idx, model in enumerate(MODELS):
            if model_idx > 0:
                print(f"  --> Falling back to next OpenRouter model: {model}")
            else:
                print(f"  --> Attempting primary OpenRouter model: {model}")
                
            for i, api_key in enumerate(API_KEYS):
                if not api_key: continue
                # Skip keys that are out of credits OR failed in this specific cycle
                is_free_model = model.endswith(":free")
                if api_key in depleted_keys and not is_free_model:
                    continue
                if api_key in cycle_failed_keys:
                    continue
                try:
                    display_key = f"{api_key[:6]}...{api_key[-4:]}"
                    print(f"      >> Trying Key {i+1} ({display_key}) on model {model}")
                    
                    response = await client.post(
                        url="https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key.strip()}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model,
                            "messages": [
                                {"role": "user", "content": prompt}
                            ]
                        },
                        timeout=35
                    )
                    
                    if response.status_code != 200:
                        print(f"      >> AI Error {response.status_code}: {response.text}")

                    if response.status_code == 200:
                        print(f"      >> SUCCESS: OpenRouter Model {model} with Key {i+1} responded.")
                        result = response.json()
                        if 'choices' not in result:
                            print(f"      >> Unexpected response structure: {result}")
                            continue
                        content = result['choices'][0]['message']['content']
                        content = content.strip().replace('```json', '').replace('```', '')

                        data = json.loads(content)
                        
                        # Validate company name against official list
                        if 'company' in data and data['company']:
                            validated_name = validate_company_name(data['company'])
                            data['company'] = validated_name
                            
                            # Auto-inject symbols if known
                            if validated_name in COMPANY_SYMBOLS:
                                symbols = COMPANY_SYMBOLS[validated_name]
                                if isinstance(symbols, list):
                                    data['stocks'] = symbols
                                else:
                                    data['stocks'] = [symbols]
                            
                        return data
                    elif response.status_code == 402:
                        print(f"      >> FAILED: Key {i+1} is out of credits (402 Payment Required).")
                        depleted_keys.add(api_key)
                        continue
                    elif response.status_code == 401:
                        print(f"      >> FAILED: Key {i+1} is Unauthorized (401). Check if the key is valid.")
                        cycle_failed_keys.add(api_key)
                        continue
                    elif response.status_code == 404:
                        print(f"      >> FAILED: Model/Resource not found (404) on Key {i+1}.")
                        err_text = response.text
                        if "Free model" in err_text:
                            print(f"         DETAIL: Check OpenRouter Privacy Settings (Allow free models).")
                        continue
                    elif response.status_code == 429:
                        print(f"      >> FAILED: Rate Limited (429) on {model} with Key {i+1}.")
                        print(f"         RESPONSE: {response.text[:200]}")
                        cycle_failed_keys.add(api_key)
                        continue
                    elif str(response.status_code).startswith('5'):
                        print(f"      >> FAILED: Provider Outage ({response.status_code}) for model {model}.")
                        continue
                    else:
                        print(f"      >> FAILED: Error {response.status_code} on model {model}: {response.text[:200]}")
                        continue
                except Exception as e:
                    print(f"      >> EXCEPTION with Key {i+1} on model {model}: {str(e)}")
                    continue
            
    # --- FALLBACK TO BYTEZ ---
    if BYTEZ_API_KEYS:
        print("  --> ALL OpenRouter models failed. Falling back to Bytez...")
        for b_key_idx, b_key in enumerate(BYTEZ_API_KEYS):
            if b_key in cycle_failed_keys: continue
            try:
                sdk = Bytez(b_key)
                # Primary Bytez model selection
                b_model_name = "google/gemma-3-12b-it" if "gemma" in MODELS[0].lower() else "openai/gpt-oss-20b"
                print(f"  --> Attempting primary Bytez model: {b_model_name} (Key {b_key_idx+1})")
                
                model = sdk.model(b_model_name)
                # Bytez SDK is synchronous, so run in executor to avoid blocking the loop
                loop = asyncio.get_event_loop()
                results = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: model.run([{"role": "user", "content": prompt}])),
                    timeout=35.0
                )
                
                if results and hasattr(results, 'output') and results.output:
                    print(f"      >> SUCCESS: Bytez analysis successful! Key {b_key_idx+1}")
                    
                    if isinstance(results.output, dict):
                        content = results.output.get("content", "")
                        if not content and "message" in results.output:
                            content = results.output["message"].get("content", "")
                        
                        if content:
                            content = clean_json_string(content)
                            try:
                                data = json.loads(content)
                            except json.JSONDecodeError as je:
                                print(f"      >> FAILED: Bytez JSON Parse Error: {je}. Content: {content[:100]}...")
                                continue
                        else:
                            data = results.output
                    else:
                        content = clean_json_string(str(results.output))
                        try:
                            data = json.loads(content)
                        except json.JSONDecodeError as je:
                            print(f"      >> FAILED: Bytez JSON Parse Error: {je}.")
                            continue
                        
                    if data.get('impact', '').lower() in ['positive', 'negative'] and data.get('probability', 0) < 50:
                        data['probability'] = 75
                        print(f"      >> Normalizing probability to 75")
                        
                        if 'company' in data and data['company']:
                            validated_name = validate_company_name(data['company'])
                            data['company'] = validated_name
                            if validated_name in COMPANY_SYMBOLS:
                                symbols = COMPANY_SYMBOLS[validated_name]
                                if isinstance(symbols, list):
                                    data['stocks'] = symbols
                                else:
                                    data['stocks'] = [symbols]
                    return data
                else:
                    err = getattr(results, 'error', 'Empty response')
                    print(f"      >> FAILED: Bytez error with Key {b_key_idx+1}: {err}")
                    cycle_failed_keys.add(b_key)
            except Exception as e:
                print(f"      >> EXCEPTION: Bytez key {b_key_idx+1} failed: {str(e)}")
                cycle_failed_keys.add(b_key)
                continue

    print("  ERROR: All models (OpenRouter & Bytez) and keys failed.")
    return {"impact": "no impact"}

async def perform_deep_analysis(full_content, headline, regime="NORMAL", current_prices=None):
    """
    PASS 2: Performs a deep dive on full article content.
    """
    # Current date and time for context (NSE/BSE specific)
    now = datetime.datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_day = now.strftime("%A")
    current_time = now.strftime("%H:%M")
    is_weekend = current_day in ["Saturday", "Sunday"]
    
    # RAG-lite: Fetch relevant training examples
    relevant_examples = get_relevant_examples(headline, limit=10, regime=regime)
    examples_text = ""
    for i, ex in enumerate(relevant_examples):
        # NOT overwriting dates anymore. Let the AI see the real historical patterns.
        examples_text += f"\n    Example {i+1}:\n    News: {ex.get('news')}\n    Output: {json.dumps(ex)}\n"

    prompt = f"""
    You are a Senior Financial Analyst focused on the Indian Stock Market (NSE/BSE).
    Analyze the full news content below and provide a DEEP IMPACT REPORT.

    MARKET CONTEXT:
    - Today is {current_day}, {current_date}. 
    - Current Time: {current_time} IST.
    - Market Status: {"CLOSED (Weekend)" if is_weekend else "OPEN/PENDING (Weekday)"}.
    - NOTE: For T+1/T+2 calculations, if today is Friday or Weekend, T+1 is NEXT MONDAY.

    FINANCIAL THEORIES & MARKET LOGIC TO APPLY:
    1. Efficient Market Hypothesis (EMH) [Eugene Fama]: In an efficient market, prices instantly incorporate all available info. News doesn't just affect price; price is the sum of past news. You must determine if this news is genuinely new information or already priced in.
    2. Abnormal Returns (AR) Formula: AR = Actual Return - Expected Return. Think: What should the stock have done vs what will this news make it do? Positive AR means news is "better than expected". Zero AR means "priced in".
    3. The "Drift" Effect (PEAD) [Ball & Brown, 1968]: Post-Earnings Announcement Drift. Stocks don't react instantly to massive surprises; they drift in that direction for weeks. News has a "long tail" impact.
    4. Behavioral Finance: Markets overreact to negative panic and underreact to complex positive news. Consider sentiment extremes.
    5. Sector Contagion: A bankruptcy drags down a sector but benefits direct competitors. Supply chain breaks hurt downstream.

    THE MASTER FORMULA: 7-MODULE IMPACT SCORING
    You MUST calculate the impact using this exact professional framework.
    
    1. Impact Strength Tiering:
    - Tier-1: Direct Earnings Impact (M&A, Govt Tax, Major Contract, FDA Approval) ➔ VERY HIGH Impact.
    - Tier-2: Sector Impact (Industry trends, Sector-wide regulations, Peer results) ➔ MEDIUM Impact.
    - Tier-3: Macro Sentiment (Global trends, Geopolitics, General news, Soft sentiment) ➔ LOW Impact.

    2. Weighted Formula:
    ImpactScore = (DirectRevenueLink * 0.4) + (SectorRelevance * 0.25) + (MarketSentiment * 0.2) + (LiquiditySensitivity * 0.15)
    Values are 0.0 to 1.0. If Final Score < 0.4 ➔ Return "no impact".

    3. Stock Sensitivity:
    Consider the stock's profile: Sector, Export exposure, Global beta, Liquidity, and Market Cap. 
    Small-cap stocks with low liquidity should have REDUCED prediction confidence.

    4. Market Context & Momentum:
    - If VIX is high ➔ Amplify impact.
    - If Market is bullish ➔ Reduce negative impact significance.

    5. Confidence Calibration (STRICT):
    - Tier-1 (Strong Direct News) ➔ 70-80% Probability.
    - Tier-2 (Medium Sector News) ➔ 55-65% Probability.
    - Tier-3 (Weak Macro News) ➔ 20-35% Probability.
    NEVER give > 80% unless it is a catastrophic or guaranteed massive earnings event.

    6. Impact Type Classification:
    - Direct: The news is directly about the company (e.g., Earnings, M&A, specific regulatory action).
    - Indirect: The news affects the broader sector, macro environment, or supply chain, which then affects the company. Typically Tier-2 and Tier-3 events are Indirect.

    RULES:
    1. Identify the EVENT, COMPANY, SECTOR, and TIER.
    2. Focus on specific stock/sector impacts.
    3. "probability" MUST reflect the Tier Calibration rules.
    4. IMPACT DATE ESTIMATION (impact_date_est): Calculate exactly when the stock will reach the "predicted_price".
       - Based on Efficient Market Hypothesis (EMH), markets react instantly to Tier-1 news. Set impact_date_est to T+1 or T+2 days from today.
       - Based on Post-Earnings Announcement Drift (PEAD), target gradual moves over T+3 to T+10 days for complex Tier-2 structural news.
       - Based on Macro lag, use T+14 to T+30 days for Tier-3 slow-burn effects.
       - EXCEPTION: If the news explicitly states an upcoming event (e.g., "RBI meeting on March 15"), set the impact date to 1-2 days AFTER that specific event date.
       - WEEKEND AWARENESS: Do not set T+1 to a Saturday or Sunday.
    5. PREDICT STOCK PRICE: If current_prices {current_prices} are provided, calculate a "predicted_price" for the primary stock on the "impact_date_est" based on the probability, impact strength, and direction.
       - Use the mapping: {current_prices} to find the current rate.
       - Formula logic: PredictedPrice = CurrentPrice * (1 + (VolatilityFactor * Probability/100 * DirectionMultiplier))
       - Be realistic. SME stocks like MAANALU can move 5-20% on major news, Large-caps move 1-5%.
       - "live_price" should be the numeric value from the provided current_prices.
    6. STRICT REASONING LOG: You MUST explicitly log your step-by-step mathematical calculations and the exact theories you applied (EMH, PEAD, etc.) inside the "reason" field. 
       - Format: [Theory Used] -> [Calculation: Today({current_date}) + N days = TargetDate] -> [Price Formula]
       - Show your formula work so calculations can be validated.

    TRAINING EXAMPLES (Relevant to this news):
    {examples_text}

    TODAY IS: {current_day}, {current_date}.
    
    Return JSON only in this format:
    {{
     "event": "Short title",
     "article_summary": "2-3 sentence detailed summary",
     "impact_description": "Detailed reasoning on stock impact",
     "company": "Primary Indian company",
     "sector": "Primary Indian sector",
     "stocks": ["NSE:SYMBOL", ...],
     "impact_direction": "UP/DOWN/NEUTRAL",
     "probability": 1-100,
     "tier": "Tier-1/Tier-2/Tier-3",
     "impact_score": 0.0-1.0,
     "event_date": "YYYY-MM-DD",
     "impact_date_est": "YYYY-MM-DD",
     "impact": "positive/negative/neutral",
     "strength": "low/medium/high",
     "reason": "STRICT LOG: [Theory] -> [Date Calc] -> [Price Calc]. Example: 'Applying EMH for Tier-1. Today(Fri) + 3 days (Mon) = {current_date}. Price: 100 * 1.05 = 105.'",
     "live_price": "Current price provided",
     "predicted_price": "Target price for impact date",
     "upside_pct": "A single string value (e.g. '+5.20%') representing the percentage change for the primary stock, NOT a dictionary/map",
     "impact_type": "Direct if company specific, Indirect if sector/macro"
    }}

    Headline: "{headline}"
    Content:
    "{full_content[:4000]}"
    
    CRITICAL: YOU MUST RESPOND ONLY WITH RELEVANT JSON. NO MARKDOWN. NO BACKTICKS. NO OTHER TEXT.
    """
    
    print(f"  DEBUG: Deep Dive Analysis for: {headline[:50]}...")
    async with httpx.AsyncClient(timeout=35.0) as client:
        for model_idx, model in enumerate(MODELS):
            if model_idx > 0:
                print(f"  --> Deep Dive Falling back to next OpenRouter model: {model}")
            else:
                print(f"  --> Deep Dive Attempting primary OpenRouter model: {model}")
                
            for i, api_key in enumerate(API_KEYS):
                if not api_key: continue
                # Skip depleted or cycle-failed keys
                is_free_model = model.endswith(":free")
                if api_key in depleted_keys and not is_free_model:
                    continue
                if api_key in cycle_failed_keys:
                    continue
                try:
                    display_key = f"{api_key[:6]}...{api_key[-4:]}"
                    print(f"      >> Trying Key {i+1} ({display_key}) for DEEP analysis")
                    response = await client.post(
                        url="https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key.strip()}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": "https://market-impact-alerts.onrender.com",
                            "X-Title": "Market Impact Alerts",
                        },
                        json={
                            "model": model, 
                            "messages": [{"role": "user", "content": prompt}]
                        },
                        timeout=50
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        if 'choices' not in result:
                            print(f"      >> Unexpected response: {result}")
                            continue
                        content = result['choices'][0]['message']['content']
                        content = content.replace('```json', '').replace('```', '').strip()
                        
                        # Handle "no impact" or empty response
                        if not content or "no impact" in content.lower()[:20]:
                            print(f"      >> AI determined no market impact for this news.")
                            return None

                        try:
                            data = json.loads(content)
                        except json.JSONDecodeError:
                            # Fallback: Try to extract JSON using regex if AI added conversational text
                            json_match = re.search(r'(\{.*\})', content, re.DOTALL)
                            if json_match:
                                try:
                                    data = json.loads(json_match.group(1))
                                except:
                                    print(f"      >> Failed to parse extracted JSON.")
                                    continue
                            else:
                                print(f"      >> AI response was not valid JSON.")
                                continue
                        
                        # Validate company name against official list
                        if 'company' in data and data['company']:
                            validated_name = validate_company_name(data['company'])
                            data['company'] = validated_name
                            
                            # Auto-inject symbols if known
                            if validated_name in COMPANY_SYMBOLS:
                                symbols = COMPANY_SYMBOLS[validated_name]
                                if isinstance(symbols, list):
                                    data['stocks'] = symbols
                                else:
                                    data['stocks'] = [symbols]
                            
                        return data
                    elif response.status_code == 402:
                        print(f"      >> Key {i+1} is out of credits (402). Skipping.")
                        depleted_keys.add(api_key)
                        continue
                    elif response.status_code == 429:
                        print(f"      >> Rate limit (429) on DEEP analysis. Blacklisting key for this cycle.")
                        cycle_failed_keys.add(api_key)
                        continue
                    elif str(response.status_code).startswith('5'):
                        print(f"      >> Deep Analysis Model Outage ({response.status_code}) on {model}. Trying next...")
                        continue
                    else:
                        print(f"      >> Deep Analysis Error {response.status_code} with Key {i+1}")
                        if response.status_code == 401:
                            cycle_failed_keys.add(api_key)
                        continue
                except Exception as e:
                    print(f"      >> Deep Analysis Exception with Key {i+1} on {model}: {e}")
                    continue
    # --- FALLBACK TO BYTEZ ---
    if BYTEZ_API_KEYS:
        print("  --> ALL OpenRouter models failed for DEEP analysis. Falling back to Bytez...")
        for b_key_idx, b_key in enumerate(BYTEZ_API_KEYS):
            if b_key in cycle_failed_keys: continue
            try:
                sdk = Bytez(b_key)
                b_model_name = "google/gemma-3-12b-it" if "gemma" in MODELS[0].lower() else "openai/gpt-oss-20b"
                print(f"  --> Deep Dive Attempting primary Bytez model: {b_model_name} (Key {b_key_idx+1})")
                
                model = sdk.model(b_model_name)
                loop = asyncio.get_event_loop()
                results = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: model.run([{"role": "user", "content": prompt}])),
                    timeout=45.0
                )
                
                if results and hasattr(results, 'output') and results.output:
                    print(f"      >> Bytez DEEP analysis successful! RAW Output: {str(results.output)[:150]}...")
                    
                    if isinstance(results.output, dict):
                        content = results.output.get("content", "")
                        if not content and "message" in results.output:
                            content = results.output["message"].get("content", "")
                            
                        if content:
                            content = clean_json_string(content)
                            try:
                                data = json.loads(content)
                            except json.JSONDecodeError as je:
                                print(f"      >> Bytez DEEP JSON Parse Error: {je}. Raw content: {content}")
                                cycle_failed_keys.add(b_key)
                                continue
                        else:
                            data = results.output
                    else:
                        content = clean_json_string(str(results.output))
                        try:
                            data = json.loads(content)
                        except json.JSONDecodeError as je:
                            print(f"      >> Bytez DEEP JSON Parse Error: {je}. Raw content: {content}")
                            cycle_failed_keys.add(b_key)
                            continue
                    
                    # Ensure probability carries over
                    if data.get('impact', '').lower() in ['positive', 'negative'] and data.get('probability', 0) < 50:
                        data['probability'] = 75
                        print(f"      >> Forcing DEEP probability to 75 since impact was {data.get('impact')}")

                        if 'company' in data and data['company']:
                            validated_name = validate_company_name(data['company'])
                            data['company'] = validated_name
                            if validated_name in COMPANY_SYMBOLS:
                                symbols = COMPANY_SYMBOLS[validated_name]
                                if isinstance(symbols, list):
                                    data['stocks'] = symbols
                                else:
                                    data['stocks'] = [symbols]
                    return data
            except Exception as e:
                print(f"      >> Bytez DEEP analysis exception: {e}")
                cycle_failed_keys.add(b_key)
                continue

    return None

async def identify_high_impact_events(headlines, regime="NORMAL"):
    """
    PASS 1: Quickly identifies which headlines are highly impactful for the app.
    """
    results = []
    print(f"PASS 1: Identifying high-impact candidates from {len(headlines)} headlines in {regime} regime...")
    
    # Analyze all headlines provided (Pass 1 filtering)
    for i, h in enumerate(headlines):
        print(f"  Check ({i+1}/{len(headlines)}): {h['title'][:50]}...")
        analysis = await analyze_headline(h['title'], regime=regime)
        if analysis.get('impact', '').lower() != "no impact":
            # Tag as a candidate for Pass 2 if probability or strength is high
            analysis['id'] = h['link']
            analysis['link'] = h['link']
            analysis['published'] = h['published']
            
            # Ensure event title exists for logging and display
            if not analysis.get('event') or analysis.get('event') == "None":
                analysis['event'] = analysis.get('article_summary', h['title'][:50])
            
            results.append(analysis)
            print(f"    --> Candidate found: {analysis.get('event')}")
        else:
            print(f"    Result: No impact")
            
    return results

# analyze_headlines_bulk is now a legacy wrapper or can be removed if we update main.py
async def analyze_headlines_bulk(headlines):
    return await identify_high_impact_events(headlines)

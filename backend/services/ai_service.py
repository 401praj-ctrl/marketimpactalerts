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

    # Load valid Angel One symbols for strict ticker validation
    VALID_SYMBOLS = set()
    tokens_path = os.path.join(BASE_DIR, "data", "angel_tokens.json")
    if os.path.exists(tokens_path):
        with open(tokens_path, "r", encoding="utf-8") as f:
            tokens_data = json.load(f)
            VALID_SYMBOLS = set(tokens_data.keys())
        print(f"Loaded {len(VALID_SYMBOLS)} valid stock symbols for strict validation.")

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

# Models in order of preference: Gemma 12b Primary, GPT-OSS 20b Secondary
MODELS = [
    "google/gemma-3-12b-it:free",
    "openai/gpt-oss-20b:free",
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
# Track keys that failed in the current analysis cycle (per model)
cycle_failed_keys = {} # Model name -> set of failed keys

def start_new_cycle():
    """Reset the per-cycle failure tracking."""
    global cycle_failed_keys
    print("  DEBUG: Starting new analysis cycle - Resetting per-cycle API key blacklists.")
    cycle_failed_keys = {}

def validate_stocks(stocks_list):
    """
    Strips exchange prefixes and validates symbols against the master list.
    Also handles common NSE symbols that might be missing the -EQ suffix.
    """
    if not isinstance(stocks_list, list): return []
    clean_stocks = []
    for stock in stocks_list:
        s = stock.replace("NSE:", "").replace("BSE:", "").strip()
        # Check raw symbol or appended -EQ for NSE stocks
        if s in VALID_SYMBOLS:
            clean_stocks.append(s)
        elif f"{s}-EQ" in VALID_SYMBOLS:
            clean_stocks.append(f"{s}-EQ")
        else:
            print(f"      >> [REJECTED] Unknown Stock: {stock}")
    return list(set(clean_stocks))

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
    
    Values are 0.0 to 1.0. If Final Score < 0.4 ➔ Return "no impact".

    RELEVANT HISTORICAL EXAMPLES TO FOLLOW:
    {examples_text}

    RULES:
    1. Identify the EVENT, COMPANY, SECTOR, and TIER.
    2. Use JSON format.
    3. Return "no impact" if not relevant.
    4. EMH & AR APPLICATION: If news is strictly "priced in", return probability < 50%.
    5. PEAD APPLICATION: Use the drift effect to set 'impact_date_est' significantly in the future if the news has long-term implications.

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
                if api_key in cycle_failed_keys.get(model, set()):
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
                    
                    if response.status_code == 200:
                        print(f"      >> SUCCESS: OpenRouter Model {model} with Key {i+1} responded.")
                        result = response.json()
                        if 'choices' not in result: continue
                        content = result['choices'][0]['message']['content']
                        content = content.strip().replace('```json', '').replace('```', '')

                        data = json.loads(content)
                        
                        # Validate company and stocks
                        if 'company' in data and data['company']:
                            data['company'] = validate_company_name(data['company'])
                            if data['company'] in COMPANY_SYMBOLS:
                                s = COMPANY_SYMBOLS[data['company']]
                                data['stocks'] = s if isinstance(s, list) else [s]
                        
                        if 'stocks' in data:
                            data['stocks'] = validate_stocks(data['stocks'])
                            
                        return data
                    elif response.status_code == 402:
                        depleted_keys.add(api_key)
                    elif response.status_code == 401 or response.status_code == 429:
                        print(f"      >> NOTICE: Key {i+1} rate limited or unauthorized on {model} (Status {response.status_code})")
                        cycle_failed_keys.setdefault(model, set()).add(api_key)
                    else:
                        print(f"      >> WARNING: Model {model} returned status {response.status_code} with Key {i+1}")
                except Exception as e:
                    print(f"      >> EXCEPTION with Key {i+1} on {model}: {str(e)}")
                    continue
            
    # --- FALLBACK TO BYTEZ ---
    if BYTEZ_API_KEYS:
        b_model_name = "google/gemma-3-12b-it"
        for b_key_idx, b_key in enumerate(BYTEZ_API_KEYS):
            # For Bytez, we skip if the key is in the general cycle_failed_keys for the bytez model
            if b_key in cycle_failed_keys.get(f"bytez/{b_model_name}", set()): continue
            try:
                sdk = Bytez(b_key)
                model = sdk.model(b_model_name)
                loop = asyncio.get_event_loop()
                results = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: model.run([{"role": "user", "content": prompt}])),
                    timeout=35.0
                )
                if results and hasattr(results, 'output') and results.output:
                    content = clean_json_string(str(results.output))
                    data = json.loads(content)
                    if 'stocks' in data:
                        data['stocks'] = validate_stocks(data['stocks'])
                    return data
            except Exception as e:
                print(f"      >> BYTEZ EXCEPTION with Key {b_key_idx+1}: {str(e)}")
                cycle_failed_keys.setdefault(f"bytez/{b_model_name}", set()).add(b_key)
                continue

    return {"impact": "no impact"}

async def perform_deep_analysis(full_content, headline, regime="NORMAL", current_prices=None):
    """
    PASS 2: Performs a deep dive on full article content.
    """
    now = datetime.datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_day = now.strftime("%A")
    current_time = now.strftime("%H:%M")
    is_weekend = current_day in ["Saturday", "Sunday"]
    
    relevant_examples = get_relevant_examples(headline, limit=10, regime=regime)
    examples_text = ""
    for i, ex in enumerate(relevant_examples):
        examples_text += f"\n    Example {i+1}:\n    News: {ex.get('news')}\n    Output: {json.dumps(ex)}\n"

    prompt = f"""
    Senior Analyst Mode: Indian Market ({current_date} {current_time} IST)
    Analyze the full news content for stock impacts.
    
    1. Tier Calibration: Direct(Tier-1), Sector(Tier-2), Macro(Tier-3).
    2. Date Estimation: Apply PEAD [Post-Earnings Announcement Drift] to set 'impact_date_est'. For major surprises, set it T+3 to T+10 days for entry/drift.
    3. Price Logic: Calculate 'predicted_price' (Impact Price) using EMH [Efficient Market Hypothesis] to determine if current price {current_prices} already reflects the news.
    
    RELEVANT HISTORICAL EXAMPLES:
    {examples_text}

    Return JSON format only.
    Headline: "{headline}"
    Content: "{full_content[:4000]}"
    """
    
    async with httpx.AsyncClient(timeout=35.0) as client:
        for model in MODELS:
            for i, api_key in enumerate(API_KEYS):
                if api_key in depleted_keys or api_key in cycle_failed_keys.get(model, set()): continue
                try:
                    display_key = f"{api_key[:6]}...{api_key[-4:]}"
                    print(f"      >> [DEEP] Trying Key {i+1} ({display_key}) on model {model}")
                    response = await client.post(
                        url="https://openrouter.ai/api/v1/chat/completions",
                        headers={"Authorization": f"Bearer {api_key.strip()}"},
                        json={"model": model, "messages": [{"role": "user", "content": prompt}]},
                        timeout=50
                    )
                    if response.status_code == 200:
                        content = response.json()['choices'][0]['message']['content'].strip().replace('```json', '').replace('```', '')
                        data = json.loads(content)
                        if 'stocks' in data:
                            data['stocks'] = validate_stocks(data['stocks'])
                        return data
                    else:
                        print(f"      >> [DEEP] WARNING: Model {model} returned status {response.status_code}")
                except Exception as e: 
                    print(f"      >> [DEEP] EXCEPTION: {str(e)}")
                    continue
    return None

async def identify_high_impact_events(headlines, regime="NORMAL"):
    results = []
    for h in headlines:
        analysis = await analyze_headline(h['title'], regime=regime)
        if analysis.get('impact', '').lower() != "no impact":
            analysis['id'] = h['link']
            analysis['link'] = h['link']
            analysis['published'] = h['published']
            results.append(analysis)
    return results

async def analyze_headlines_bulk(headlines):
    return await identify_high_impact_events(headlines)

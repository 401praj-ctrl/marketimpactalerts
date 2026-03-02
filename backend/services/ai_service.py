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
from google import genai
from services.search_service import search_ticker_online

# Environment variables are managed by main.py
# Only load here if running standalone
if not os.environ.get("OPENROUTER_API_KEY_1"):
    load_dotenv()


# Load company names for validation
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPANY_NAMES = []
COMPANY_SYMBOLS = {}
GLOBAL_SYMBOLS = {
    "DELL", "NVDA", "AAPL", "MSFT", "GOOGL", "GOOG", "TSLA", "META", "AMZN", 
    "NFLX", "INTC", "AMD", "AVGO", "CSCO", "ORCL", "TSM", "ARM", "ASML", 
    "QCOM", "MU", "SMCI", "SNOW", "PLTR", "WDC", "STX", "HPQ",
    "WBD", "PARA", "DIS", "AMC", "CMG", "MCD", "SBUX", "COST", "WMT", "TGT",
    "JPM", "GS", "MS", "BAC", "C", "V", "MA", "AXP", "BABA", "SONY", "XIACF",
    "XOM", "SHEL", "BP", "JNJ", "PG", "TM", "HMC",
    "LMT", "RTX", "HON", "BA", "CAT", "GE", "IBM", "NOW", "UBER", "ABNB",
    "CVX", "SLB", "COP", "UNH", "PFE", "MRK", "ABBV", "LLY",
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "DOGE-USD", "ADA-USD"
}
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

# Models in order of preference
MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-3-12b-it:free",
    "openai/gpt-oss-20b:free",
]

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")


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
    if '```json' in content:
        content = content.split('```json', 1)[-1]
    elif '```' in content:
        content = content.split('```', 1)[-1]
    
    if '```' in content:
        content = content.split('```', 1)[0]
        
    content = content.strip()
    
    # Handle cases where AI returns "Output: { ... }"
    if content.startswith("Output:"):
        content = content[len("Output:"):].strip()
        
    # Remove trailing commas before closing braces/brackets
    content = re.sub(r',\s*([}\]])', r'\1', content)
    
    # CRITICAL: Fix Python dict string representations and malformed JSON
    try:
        # First check if it's already valid JSON
        json.loads(content)
        return content
    except json.JSONDecodeError:
        pass

    try:
        # Attempt to safely evaluate a python dictionary string
        import ast
        parsed_dict = ast.literal_eval(content)
        if isinstance(parsed_dict, dict):
            return json.dumps(parsed_dict)
    except:
        pass
        
    # Last resort: Try to find a JSON-like object string using regex
    try:
        # Find the first { and the last }
        start_idx = content.find('{')
        end_idx = content.rfind('}')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            extracted = content[start_idx:end_idx+1]
            try:
                json.loads(extracted)
                return extracted
            except json.JSONDecodeError:
                # Replace single quotes with double quotes as a rough fix
                extracted = extracted.replace("'", '"')
                json.loads(extracted)
                return extracted
    except:
        pass

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

# Track keys that are out of credits or rate-limited to avoid retrying them in the same session
depleted_keys = set()
rate_limited_keys = set()
unauthorized_keys = set()
depleted_bytez_keys = set()
# Track keys that failed in the current analysis cycle (per model)
cycle_failed_keys = {} # Model name -> set of failed keys

def start_new_cycle():
    """Reset the per-cycle failure tracking."""
    global cycle_failed_keys
    print("  DEBUG: Starting new analysis cycle - Resetting per-cycle API key blacklists.")
    cycle_failed_keys = {}

# Sector to Representative Tickers mapping for Macro news
MACRO_SECTOR_MAPPING = {
    "Banking": ["NSE:SBIN", "NSE:HDFCBANK"],
    "IT Services": ["NSE:TCS", "NSE:INFY"],
    "Pharma": ["NSE:SUNPHARMA", "NSE:DRREDDY"],
    "Auto": ["NSE:TATAMOTORS", "NSE:MARUTI"],
    "Energy": ["NSE:RELIANCE", "NSE:ONGC"],
    "Consumer": ["NSE:HINDUNILVR", "NSE:ITC"],
    "Metal": ["NSE:TATASTEEL", "NSE:JINDALSTEL"],
    "Real Estate": ["NSE:DLF", "NSE:GODREJPROP"],
    "Infrastructure": ["NSE:LT", "NSE:ADANIPORTS"],
    "Insurance": ["NSE:HDFCLIFE", "NSE:LICHSGFIN"],
    "Telecom": ["NSE:BHARTIARTL", "NSE:IDEA"],
    "FMCG": ["NSE:HINDUNILVR", "NSE:ITC"],
    "Retail": ["NSE:TRENT", "NSE:RELIANCE"],
    "Agriculture": ["NSE:COROMANDEL", "NSE:UPL"],
    "Macro": ["NSE:RELIANCE", "NSE:HDFCBANK"], # Market proxies
    "Tech": ["NSE:TCS", "NSE:INFY", "NSE:WIPRO"],
    "Artificial Intelligence": ["NSE:TCS", "NSE:INFY", "NSE:HCLTECH"],
    "Entertainment": ["NSE:PVRINOX", "NSE:ZEEL", "NSE:SUNTV"],
    "Media": ["NSE:ZEEL", "NSE:SUNTV", "NSE:NETWORK18"],
}

async def validate_stocks(stocks_list, sector=None, headline=None, company_name=None):
    """
    Strips exchange prefixes and validates symbols against the master list.
    Also handles common NSE symbols that might be missing the -EQ suffix.
    If stocks_list is empty, attempts to provide sector-based proxies using sector or headline.
    """
    if not isinstance(stocks_list, list): stocks_list = []
    
    clean_stocks = []
    for stock in stocks_list:
        raw_s = str(stock).upper()
        s = raw_s.replace("NSE:", "").replace("BSE:", "").strip()
        
        # Blacklist generic terms that aren't real stocks
        if s in ["INDIA", "STOCK", "STOCKS", "NEWS", "MARKET", "NIFTY", "SENSEX", "BSE", "NSE"]:
            print(f"      >> [REJECTED] Generic term blocked: {s}")
            continue
        
        # Determine prefix if it was in the original string
        prefix = "NSE:" if "NSE:" in raw_s else ("BSE:" if "BSE:" in raw_s else "NSE:")
        
        # Check raw symbol or appended -EQ for NSE stocks
        if s in VALID_SYMBOLS:
            clean_stocks.append(f"{prefix}{s}")
        elif f"{s}-EQ" in VALID_SYMBOLS:
            clean_stocks.append(f"NSE:{s}-EQ")
        elif s in GLOBAL_SYMBOLS:
            # Allow well-known global symbols (will be fetched via YFinance)
            clean_stocks.append(s)
        elif s == "DELLTECH": # Common AI hallucination for Dell
            clean_stocks.append("DELL")
        elif "NIFTY" in s or s in ["SENSEX", "NASDAQ", "DOW", "S&P", "USDINR", "CRUDE", "BANKNIFTY", "FINNIFTY"]:
            # Map NIFTY indices and Macro terms to sector proxies
            if "BANK" in s or "FIN" in s: clean_stocks.extend(MACRO_SECTOR_MAPPING.get("Banking", []))
            elif "INFRA" in s: clean_stocks.extend(MACRO_SECTOR_MAPPING.get("Infrastructure", []))
            elif "IT" in s or "TECH" in s or "NASDAQ" in s: clean_stocks.extend(MACRO_SECTOR_MAPPING.get("IT Services", []))
            elif "FMCG" in s: clean_stocks.extend(MACRO_SECTOR_MAPPING.get("FMCG", []))
            elif "AUTO" in s: clean_stocks.extend(MACRO_SECTOR_MAPPING.get("Auto", []))
            elif "PHARMA" in s: clean_stocks.extend(MACRO_SECTOR_MAPPING.get("Pharma", []))
            elif "METAL" in s: clean_stocks.extend(MACRO_SECTOR_MAPPING.get("Metal", []))
            elif "REAL" in s: clean_stocks.extend(MACRO_SECTOR_MAPPING.get("Real Estate", []))
            elif "ENERGY" in s: clean_stocks.extend(MACRO_SECTOR_MAPPING.get("Energy", []))
            elif "MEDIA" in s: clean_stocks.extend(MACRO_SECTOR_MAPPING.get("Media", []))
            else: clean_stocks.extend(MACRO_SECTOR_MAPPING.get("Macro", []))
        elif s in ["BTC", "BITCOIN"]: clean_stocks.append("BTC-USD")
        elif s in ["ETH", "ETHEREUM"]: clean_stocks.append("ETH-USD")
        elif s in ["SOL", "SOLANA"]: clean_stocks.append("SOL-USD")
        elif s in ["XRP"]: clean_stocks.append("XRP-USD")
        else:
            print(f"      >> [REJECTED] Unknown Stock: {stock}")

    # ONLINE FALLBACK: If list is empty, try searching the company name online
    if not clean_stocks and company_name:
        online_tickers = await search_ticker_online(company_name)
        if online_tickers:
            print(f"      >> [ONLINE FALLBACK] Found tickers via web search: {online_tickers}")
            clean_stocks.extend(online_tickers)
            
    # FALLBACK: If list is still empty after validation, use sector mapping or headline keywords
    if not clean_stocks:
        search_target = (str(sector or "") + " " + str(headline or "")).lower()
        for cat, proxies in MACRO_SECTOR_MAPPING.items():
            if cat.lower() in search_target:
                print(f"      >> [FALLBACK] Triggered for '{cat}' match in context. Using proxies: {proxies}")
                return list(set(proxies))
        
        # Final safety: If headline mentions broad market terms but index-specific check missed
        if any(w in search_target for w in ["gdp", "fiscal", "inflation", "market", "economy", "sensex", "nifty", "wall st"]):
            print(f"      >> [FALLBACK] Broad macro match. Using Macro proxies.")
            return list(set(MACRO_SECTOR_MAPPING.get("Macro", [])))
                
    # FINAL SAFETY: If list is still empty, use the company name itself to allow price search to try web scraping
    if not clean_stocks and company_name and company_name.lower() != "n/a":
        print(f"      >> [FINAL FALLBACK] No tickers found. Using company name '{company_name}' as symbol.")
        clean_stocks.append(company_name)
                
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
    Today's Date: {current_date} IST
    You are a Senior Financial Analyst specializing in the Indian Stock Market (NSE/BSE).
    Analyze the news headline and return a structured JSON response.

    FINANCIAL THEORIES TO APPLY:
    1. Efficient Market Hypothesis (EMH): Determine if this news is new information or if it's already "priced in" (Probability < 50% if priced in).
    2. Abnormal Returns (AR): Think: What should the stock have done vs what will this news make it do? (Positive AR = Bullish).
    3. Post-Earnings Announcement Drift (PEAD): If the news has long-term tail implications, set 'impact_date_est' to a future range (T+3 to T+10).
    4. IPO & Listing Logic: 
       - Premium Listing = Bullish/UP. 
       - Discount Listing = Bearish/NEUTRAL. NEVER mark a discount listing as UP.

    JSON SCHEMA:
    {{
      "event": "Short title of the news event",
      "company": "Primary company name (e.g. Reliance Industries)",
      "sector": "Affected sector (e.g. Banking, IT, Pharma)",
      "tier": "Tier-1 (Direct), Tier-2 (Sector-wide), or Tier-3 (Macro-market)",
      "impact_direction": "UP, DOWN, or NEUTRAL",
      "probability": 0 to 100 integer,
      "impact_date_est": "T+0", "T+1", "T+3", "T+0 to T+2", or "T+3 to T+10",
      "reason": "MANDATORY: 2-3 sentence explanation combining the executive summary and the impact logic.",
      "stocks": ["NSE:SYMBOL", "NSE:OTHER"]
    }}

    RULES:
    1. Return "no impact" ONLY if the news is completely irrelevant to any public stocks.
    2. STOCK IDENTIFICATION (CRITICAL): Provide 1-3 valid NSE/BSE symbols. 
       - Macro/Sector news? List the 2-3 biggest leaders of that sector.
    3. Accuracy: Ensure the Tier correctly reflects the scope (Direct vs Sector vs Macro).

    RELEVANT HISTORICAL EXAMPLES:
    {examples_text}

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
                if (api_key in depleted_keys and not is_free_model) or api_key in rate_limited_keys or api_key in unauthorized_keys:
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
                            ],
                            "temperature": 0.1,
                            "max_tokens": 1000
                        },
                        timeout=35
                    )
                    
                    if response.status_code == 200:
                        print(f"      >> SUCCESS: OpenRouter Model {model} with Key {i+1} responded.")
                        result = response.json()
                        if 'choices' not in result: continue
                        message = result['choices'][0]['message']
                        content = message.get('content', '')
                        
                        # Logging reasoning tokens if present (as requested in user snippet)
                        reasoning = message.get('reasoning')
                        if reasoning:
                            print(f"      >> Reasoning: {reasoning[:200]}...")
                        
                        # Robust JSON cleaning
                        content = clean_json_string(content)
                        data = json.loads(content)
                        
                        # Validate company and stocks
                        if 'company' in data and data['company']:
                            data['company'] = validate_company_name(data['company'])
                            if data['company'] in COMPANY_SYMBOLS:
                                s = COMPANY_SYMBOLS[data['company']]
                                data['stocks'] = s if isinstance(s, list) else [s]
                        
                        if 'stocks' in data:
                            data['stocks'] = await validate_stocks(
                                data['stocks'], 
                                sector=data.get('sector'), 
                                headline=headline_text,
                                company_name=data.get('company')
                            )
                            
                        return data
                    elif response.status_code == 402:
                        print(f"      >> BLACKLISTING Key {i+1} (Depleted/Status 402)")
                        depleted_keys.add(api_key)
                    elif response.status_code == 429:
                        print(f"      >> BLACKLISTING Key {i+1} (Rate Limited/Status 429)")
                        rate_limited_keys.add(api_key)
                    elif response.status_code == 401:
                        print(f"      >> BLACKLISTING Key {i+1} (Unauthorized/Status 401)")
                        unauthorized_keys.add(api_key)
                    else:
                        print(f"      >> WARNING: Model {model} returned status {response.status_code} with Key {i+1}")
                except Exception as e:
                    print(f"      >> [ERROR] AI Parsing failed for {model}: {e}")
                    # Optionally print first 100 chars of content for debugging
                    try:
                        print(f"      >> Raw content (truncated): {repr(content)[:100]}")
                    except: pass
                    continue
            
    # --- FALLBACK TO BYTEZ ---
    if BYTEZ_API_KEYS:
        BYTEZ_MODELS = [
            "Qwen/Qwen2.5-1.5B-Instruct",
            "mistralai/Mistral-7B-Instruct-v0.2", 
            "HuggingFaceH4/zephyr-7b-beta"
        ]
        print(f"  --> [FALLBACK] All OpenRouter keys failed or rate-limited. Trying Bytez Text-Generation models...")
        for b_model_name in BYTEZ_MODELS:
            for b_key_idx, b_key in enumerate(BYTEZ_API_KEYS):
                if b_key in depleted_bytez_keys:
                    continue
                try:
                    print(f"      >> Trying Bytez Key {b_key_idx+1} on model {b_model_name}...")
                    sdk = Bytez(b_key)
                    model = sdk.model(b_model_name)
                    loop = asyncio.get_event_loop()
                    results = await asyncio.wait_for(
                        loop.run_in_executor(None, lambda: model.run([{"role": "user", "content": prompt}])),
                        timeout=35.0
                    )
                    
                    # Robust output extraction
                    raw_output = None
                    if results and hasattr(results, 'output') and results.output:
                        raw_output = results.output
                    elif isinstance(results, dict) and 'output' in results:
                        raw_output = results['output']
                    elif isinstance(results, str):
                        raw_output = results
                    
                    # Handle Bytez/OpenAI chat completion dictionary format
                    if isinstance(raw_output, dict) and 'content' in raw_output:
                        raw_output = raw_output['content']
                    elif isinstance(raw_output, dict) and 'message' in raw_output and 'content' in raw_output['message']:
                        raw_output = raw_output['message']['content']
                    
                    if raw_output:
                        print(f"      >> SUCCESS: Bytez Model {b_model_name} with Key {b_key_idx+1} responded.")
                        print(f"      >> RAW OUTPUT: {repr(raw_output)[:300]}")
                        content = clean_json_string(str(raw_output))
                        data = json.loads(content)
                        if 'stocks' in data:
                            data['stocks'] = await validate_stocks(
                                data['stocks'], 
                                sector=data.get('sector'), 
                                headline=headline_text,
                                company_name=data.get('company')
                            )
                        return data
                    else:
                        print(f"      >> NOTICE: Bytez {b_model_name} Key {b_key_idx+1} returned empty/unexpected: {str(results)[:100]}")
                except Exception as e:
                    error_msg = str(e)
                    print(f"      >> BYTEZ EXCEPTION with Key {b_key_idx+1} on {b_model_name}: {error_msg}")
                    if "min balance" in error_msg.lower() or "0.1 credits" in error_msg.lower():
                        print(f"      >> BLACKLISTING Bytez Key {b_key_idx+1} (Depleted/Insufficient Balance)")
                        depleted_bytez_keys.add(b_key)
                    continue

    # --- FALLBACK TO GEMINI ---
    gemini_key = os.environ.get("GEMINI_API_KEY") or GEMINI_API_KEY
    if gemini_key:
        try:
            print("  --> [FALLBACK] OpenRouter AND Bytez failed. Trying Google Gemini...")
            client = genai.Client(api_key=gemini_key)
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt
            )
            raw_output = response.text
            if raw_output:
                print("      >> SUCCESS: Google Gemini Model gemini-2.0-flash responded.")
                content = clean_json_string(str(raw_output))
                data = json.loads(content)
                if 'stocks' in data:
                    data['stocks'] = await validate_stocks(
                        data['stocks'], 
                        headline=headline_text,
                        company_name=data.get('company')
                    )
                return data
        except Exception as e:
            print(f"      >> GEMINI EXCEPTION: {str(e)}")

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
    2. Date Estimation: For Direct (Tier-1) impacts, set 'impact_date_est' within T+0 to T+2 range (Current Date: {current_date}). If a long-term drift is expected (Sector/Macro), apply PEAD [Post-Earnings Announcement Drift] to set it T+3 to T+10 days.
    3. Price Logic: Calculate 'predicted_price' (Impact Price) using EMH [Efficient Market Hypothesis] to determine if current price {current_prices} already reflects the news.
    4. ANALYSIS: Provide a granular 'impact_description' explaining the move.
    5. STOCKS (MANDATORY): List specific ticker symbols impacted. NEVER leave this empty. If it's macro news, list the top 2-3 companies in the most affected sector (e.g., \"NSE:SBIN\", \"NSE:HDFCBANK\" for banking macro news).
    
    RELEVANT HISTORICAL EXAMPLES:
    {examples_text}

    Return JSON format only.
    JSON SCHEMA:
    {{
      "event": "Short title of the news event",
      "company": "Primary company name (e.g. Reliance Industries)",
      "sector": "Affected sector (e.g. Banking, IT, Pharma)",
      "tier": "Tier-1 (Direct), Tier-2 (Sector-wide), or Tier-3 (Macro-market)",
      "impact_direction": "UP, DOWN, or NEUTRAL",
      "probability": 0 to 100 integer,
      "impact_date_est": "T+0", "T+1", "T+3", "T+0 to T+2", or "T+3 to T+10",
      "reason": "MANDATORY: 2-3 sentence explanation combining the executive summary and the impact logic.",
      "stocks": ["NSE:SYMBOL", "NSE:OTHER"]
    }}

    Headline: "{headline}"
    Content: "{full_content[:4000]}"
    """
    
    async with httpx.AsyncClient(timeout=35.0) as client:
        for model in MODELS:
            for i, api_key in enumerate(API_KEYS):
                if api_key in depleted_keys or api_key in rate_limited_keys or api_key in unauthorized_keys or api_key in cycle_failed_keys.get(model, set()):
                    continue
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
                        result = response.json()
                        content = result['choices'][0]['message']['content'].strip().replace('```json', '').replace('```', '')
                        
                        # Logging for reasoning tokens from user snippet logic
                        try:
                            usage = result.get('usage')
                            if usage and 'reasoning_tokens' in usage:
                                print(f"      >> Reasoning Tokens: {usage['reasoning_tokens']}")
                        except: pass

                        data = json.loads(content)
                        if 'stocks' in data:
                            data['stocks'] = validate_stocks(data['stocks'], sector=data.get('sector'), headline=headline)
                        return data
                    else:
                        print(f"      >> [DEEP] WARNING: Model {model} returned status {response.status_code}")
                        if response.status_code == 402:
                            print(f"      >> [DEEP] BLACKLISTING Key {i+1} (Depleted/Status 402)")
                            depleted_keys.add(api_key)
                        elif response.status_code == 429:
                            print(f"      >> [DEEP] BLACKLISTING Key {i+1} (Rate Limited/Status 429)")
                            rate_limited_keys.add(api_key)
                        elif response.status_code == 401:
                            print(f"      >> [DEEP] BLACKLISTING Key {i+1} (Unauthorized/Status 401)")
                            unauthorized_keys.add(api_key)
                except Exception as e: 
                    print(f"      >> [DEEP] EXCEPTION: {str(e)}")
                    continue
                    
    # --- FALLBACK TO BYTEZ for Deep Analysis ---
    if BYTEZ_API_KEYS:
        BYTEZ_MODELS = [
            "Qwen/Qwen2.5-1.5B-Instruct",
            "mistralai/Mistral-7B-Instruct-v0.2", 
            "HuggingFaceH4/zephyr-7b-beta"
        ]
        print(f"      >> [DEEP-FALLBACK] All OpenRouter keys failed. Trying Bytez Text-Generation models...")
        for b_model_name in BYTEZ_MODELS:
            for b_key_idx, b_key in enumerate(BYTEZ_API_KEYS):
                if b_key in depleted_bytez_keys:
                    continue
                try:
                    print(f"      >> [DEEP] Trying Bytez Key {b_key_idx+1} on model {b_model_name}...")
                    sdk = Bytez(b_key)
                    model = sdk.model(b_model_name)
                    loop = asyncio.get_event_loop()
                    results = await asyncio.wait_for(
                        loop.run_in_executor(None, lambda: model.run([{"role": "user", "content": prompt}])),
                        timeout=50.0
                    )
                    
                    raw_output = None
                    if results and hasattr(results, 'output') and results.output:
                        raw_output = results.output
                    elif isinstance(results, dict) and 'output' in results:
                        raw_output = results['output']
                    elif isinstance(results, str):
                        raw_output = results
                    
                    # Handle Bytez/OpenAI chat completion dictionary format
                    if isinstance(raw_output, dict) and 'content' in raw_output:
                        raw_output = raw_output['content']
                    elif isinstance(raw_output, dict) and 'message' in raw_output and 'content' in raw_output['message']:
                        raw_output = raw_output['message']['content']
    
                    if raw_output:
                        print(f"      >> [DEEP] SUCCESS: Bytez Model {b_model_name} with Key {b_key_idx+1} responded.")
                        print(f"      >> [DEEP] RAW OUTPUT: {repr(raw_output)[:300]}")
                        content = clean_json_string(str(raw_output))
                        data = json.loads(content)
                        if 'stocks' in data:
                            data['stocks'] = validate_stocks(data['stocks'], sector=data.get('sector'), headline=headline)
                        return data
                    else:
                        print(f"      >> [DEEP-NOTICE] Bytez {b_model_name} Key {b_key_idx+1} returned empty/unexpected: {str(results)[:100]}")
                except Exception as e:
                    error_msg = str(e)
                    print(f"      >> [DEEP] BYTEZ EXCEPTION with Key {b_key_idx+1} on {b_model_name}: {error_msg}")
                    if "min balance" in error_msg.lower() or "0.1 credits" in error_msg.lower():
                        print(f"      >> [DEEP] BLACKLISTING Bytez Key {b_key_idx+1} (Depleted/Insufficient Balance)")
                        depleted_bytez_keys.add(b_key)
                    continue

    # --- FALLBACK TO GEMINI for Deep Analysis ---
    gemini_key = os.environ.get("GEMINI_API_KEY") or GEMINI_API_KEY
    if gemini_key:
        try:
            print("      >> [DEEP-FALLBACK] OpenRouter AND Bytez failed. Trying Google Gemini...")
            client = genai.Client(api_key=gemini_key)
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            raw_output = response.text
            if raw_output:
                print("      >> [DEEP] SUCCESS: Google Gemini Model gemini-2.5-flash responded.")
                content = clean_json_string(str(raw_output))
                data = json.loads(content)
                if 'stocks' in data:
                    data['stocks'] = await validate_stocks(
                        data['stocks'], 
                        headline=headline,
                        company_name=data.get('company')
                    )
                return data
        except Exception as e:
            print(f"      >> [DEEP] GEMINI EXCEPTION: {str(e)}")

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

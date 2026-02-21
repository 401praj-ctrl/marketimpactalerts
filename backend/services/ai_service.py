import httpx
import json
import os
import asyncio
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
except Exception as e:
    print(f"Warning: Could not load company data: {e}")


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

# Updated API Keys logic: Find ALL OpenRouter keys dynamically
API_KEYS = []
for key, value in os.environ.items():
    if key.startswith("OPENROUTER_API_KEY") and value and value.strip():
        val = value.strip()
        if val not in API_KEYS:
            API_KEYS.append(val)
            print(f"DEBUG: Found OpenRouter key from {key}: {val[:6]}...{val[-4:]}")

if not API_KEYS:
    print("WARNING: No API keys found in environment. AI features will be disabled until keys are set.")
    API_KEYS = []
else:
    print(f"DEBUG: Successfully loaded {len(API_KEYS)} unique OpenRouter API keys from environment.")

# Bytez API Keys Support: Find ALL Bytez keys dynamically
BYTEZ_API_KEYS = []
for key, value in os.environ.items():
    if key.startswith("BYTEZ_API_KEY") and value and value.strip():
        val = value.strip()
        if val not in BYTEZ_API_KEYS:
            BYTEZ_API_KEYS.append(val)
            print(f"DEBUG: Found Bytez key from {key}: {val[:6]}...{val[-4:]}")

if BYTEZ_API_KEYS:
    print(f"DEBUG: Successfully loaded {len(BYTEZ_API_KEYS)} unique Bytez API keys.")

# Models in order of preference: Exclusive free models as requested
MODELS = [
    "google/gemma-3-12b-it:free",
    "openai/gpt-oss-20b:free",
]


# Load training examples
TRAINING_EXAMPLES = []
try:
    examples_path = os.path.join(BASE_DIR, "data", "training_examples.json")
    if os.path.exists(examples_path):
        with open(examples_path, "r", encoding="utf-8") as f:
            TRAINING_EXAMPLES = json.load(f)
        print(f"Loaded {len(TRAINING_EXAMPLES)} training examples.")
except Exception as e:
    print(f"Warning: Could not load training examples: {e}")


def get_relevant_examples(headline, limit=3):
    """
    Returns the most relevant training examples for a given headline.
    Uses simple keyword matching for RAG-lite.
    """
    if not TRAINING_EXAMPLES: return []
    
    # Simple keyword extraction
    keywords = set(headline.lower().split())
    
    scored_examples = []
    for ex in TRAINING_EXAMPLES:
        # Match against event, sector, or reason keywords
        content = (ex['event'] + " " + ex.get('sector', '') + " " + ex.get('reason', '')).lower()
        score = sum(1 for k in keywords if k in content and len(k) > 3)
        scored_examples.append((score, ex))
        
    # Sort by score descending
    scored_examples.sort(key=lambda x: x[0], reverse=True)
    
    # Return top N examples
    return [ex for score, ex in scored_examples[:limit]]

# Track keys that are out of credits to avoid retrying them in the same session
depleted_keys = set()

async def analyze_headline(headline_text):
    # ... existing RAG-lite code ...
    
    # [Lines 108-154 truncated for brevity in thought, but included in tool call]
    # RAG-lite: Fetch relevant training examples
    relevant_examples = get_relevant_examples(headline_text, limit=3)
    examples_text = ""
    for i, ex in enumerate(relevant_examples):
        examples_text += f"\n    Example {i+1}:\n    News: {ex.get('news')}\n    Output: {json.dumps(ex)}\n"

    prompt = f"""
    You are an AI that detects whether a news event may impact publicly traded stocks or sectors.
    Analyze the news and return a structured JSON response.

    FINANCIAL THEORIES & MARKET LOGIC TO APPLY:
    1. Efficient Market Hypothesis (EMH) [Eugene Fama]: In an efficient market, prices instantly incorporate all available info. News doesn't just affect price; price is the sum of past news. You must determine if this news is genuinely new information or already priced in.
    2. Abnormal Returns (AR) Formula: AR = Actual Return - Expected Return. Think: What should the stock have done vs what will this news make it do? Positive AR means news is "better than expected". Zero AR means "priced in".
    3. The "Drift" Effect (PEAD) [Ball & Brown, 1968]: Post-Earnings Announcement Drift. Stocks don't react instantly to massive surprises; they drift in that direction for weeks. News has a "long tail" impact.
    4. Behavioral Finance: Markets overreact to negative panic and underreact to complex positive news. Consider sentiment extremes.
    5. Sector Contagion: A bankruptcy drags down a sector but benefits direct competitors. Supply chain breaks hurt downstream.

    THE MASTER FORMULA: NEWS IMPACT SCORE
    You MUST calculate the impact using this exact quantitative NLP framework internally.
    
    Step 1. NLP Sentiment Score (-1 to +1)
    - Very positive = +1.0, Positive = +0.5, Neutral = 0.0, Negative = -0.5, Very negative = -1.0
    
    Step 2. Surprise Factor (0.0 to 1.0) [MOST IMPORTANT]
    - If news is already known/expected = 0.1
    - Massive unexpected surprise = 1.0
    
    Step 3. Importance Weight (0.0 to 1.0)
    - Earnings/Major M&A = 1.0
    - Govt Policy/Interest Rates = 0.9
    - Large Order/Contract = 0.8
    - CEO/Mgmt Change = 0.6
    - Rumor/Speculation = 0.3
    - Trivial/Tweet = 0.2
    
    Step 4. Source Credibility (0.0 to 1.0)
    - Official Filing/Press Release = 1.0
    - Reuters/Bloomberg/Major Outlet = 0.9
    - Standard News Channel = 0.8
    - Twitter/Social Media = 0.4
    - Unknown/Unverified = 0.2
    
    Step 5. The News Z-Score (Outlier Check)
    - Evaluate if this news volume/severity is "market noise" (routine daily updates) or a "statistical outlier" (>2 standard deviations from normal = Real Trade Signal).
    - If it is just noise, artificially lower your final impact confidence.

    Step 6. IMPACT SCORE CALCULATION
    Internal Raw Score = (Sentiment * Surprise * Importance * Credibility)
    - If Raw Score > 0.7 AND high Z-Score ➔ STRONG BUY (Probability 85-100)
    - If Raw Score > 0.3 ➔ BUY (Probability 60-84)
    - If Raw Score between -0.3 and 0.3 or low Z-Score (noise) ➔ IGNORE (Return "impact": "no impact")
    - If Raw Score < -0.3 ➔ SELL (Probability 60-84)
    - If Raw Score < -0.7 AND high Z-Score ➔ STRONG SELL (Probability 85-100)

    RULES:
    1. Identify the EVENT, COMPANY, SECTOR, and IMPACT.
    2. If the news is irrelevant to stocks (e.g., crime, sports, entertainment without business angle), return {{"impact": "no impact"}}.
    3. Use "NSE:SYMBOL" format for stocks if known (e.g., "NSE:RELIANCE").
    4. "probability" is confidence event happened (1-100).
    5. "confidence" is analysis confidence (1-100).

    TRAINING EXAMPLES (Relevant to this news):
    {examples_text}

    TODAY IS: 2026-02-19.
    
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
     "reason": "Brief financial reasoning",
     "impact": "positive/negative/neutral",
     "strength": "low/medium/high",
     "confidence": 1-100
    }}

    If no stock impact → return {{"impact":"no impact"}}.

    Headline: "{headline_text}"
    """
    
    print(f"  DEBUG: Prompting AI for: {headline_text[:50]}...")
    
    async with httpx.AsyncClient() as client:
        # Multi-layer fallback: Try Primary Model with all keys, then Backup Model with all keys
        for model in MODELS:
            print(f"    > Attempting model: {model}")
            for i, api_key in enumerate(API_KEYS):
                if not api_key: continue
                # Skip keys that were previously found to be out of credits, unless using a free model
                is_free_model = model.endswith(":free")
                if api_key in depleted_keys and not is_free_model:
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

                        result = response.json()
                        if 'choices' not in result:
                            print(f"      >> Unexpected response: {result}")
                            continue
                        content = result['choices'][0]['message']['content']
                        content = content.strip().replace('```json', '').replace('```', '')

                        data = json.loads(content)
                        
                        # Validate company name against official list
                        if 'company' in data and data['company']:
                            validated_name = validate_company_name(data['company'])
                            data['company'] = validated_name
                            
                            # Auto-inject symbol if known
                            if validated_name in COMPANY_SYMBOLS:
                                data['stocks'] = [COMPANY_SYMBOLS[validated_name]]
                            
                        return data
                    elif response.status_code == 402:
                        print(f"      >> Key {i+1} is out of credits (402). Skipping for this session.")
                        depleted_keys.add(api_key)
                        continue
                    elif response.status_code == 404:
                        # Silently skip 404s (Model not supported on this key)
                        print(f"      >> Model {model} not found on Key {i+1}. Skipping.")
                        continue
                    elif response.status_code == 429:
                        print(f"      >> Rate Limit (429) on {model} with Key {i+1}. Rotating...")
                        continue
                    else:
                        # Other errors -> Try next key
                        print(f"      >> Error {response.status_code} on {model}: {response.text[:100]}...")
                        # Map 401 specifically for logging
                        if response.status_code == 401:
                             print(f"         WARNING: Key {i+1} might be invalid.")
                        continue
                except Exception as e:
                    print(f"      >> Exception with Key {i+1}: {e}")
                    continue
            
    
    # --- FALLBACK TO BYTEZ ---
    if BYTEZ_API_KEYS:
        print("  DEBUG: OpenRouter failed. Falling back to Bytez...")
        for b_key in BYTEZ_API_KEYS:
            try:
                sdk = Bytez(b_key)
                # Primary Bytez model selection
                b_model_name = "google/gemma-3-12b-it" if "gemma" in MODELS[0].lower() else "openai/gpt-oss-20b"
                print(f"    > Attempting Bytez model: {b_model_name}")
                
                model = sdk.model(b_model_name)
                # Bytez SDK is synchronous, so run in executor to avoid blocking the loop
                loop = asyncio.get_event_loop()
                results = await loop.run_in_executor(None, lambda: model.run([{"role": "user", "content": prompt}]))
                
                if results and hasattr(results, 'output') and results.output:
                    print("      >> Bytez analysis successful!")
                    
                    if isinstance(results.output, dict):
                        data = results.output
                    else:
                        content = results.output.strip().replace('```json', '').replace('```', '')
                        data = json.loads(content)
                        
                    if 'company' in data and data['company']:
                        validated_name = validate_company_name(data['company'])
                        data['company'] = validated_name
                        if validated_name in COMPANY_SYMBOLS:
                            data['stocks'] = [COMPANY_SYMBOLS[validated_name]]
                    return data
                else:
                    print(f"      >> Bytez error or empty output: {getattr(results, 'error', 'Unknown error')}")
            except Exception as e:
                print(f"      >> Bytez exception: {e}")
                continue

    print("  ERROR: All models (OpenRouter & Bytez) and keys failed.")
    return {"impact": "no impact"}

async def perform_deep_analysis(full_content, headline):
    """
    PASS 2: Performs a deep dive on full article content.
    """
    # RAG-lite: Fetch relevant training examples
    relevant_examples = get_relevant_examples(headline, limit=3)
    examples_text = ""
    for i, ex in enumerate(relevant_examples):
        # Adapt example format for deep analysis
        examples_text += f"\n    Example {i+1}:\n    News: {ex.get('news')}\n    Output: {json.dumps(ex)}\n"

    prompt = f"""
    You are a Senior Financial Analyst focused on the Indian Stock Market (NSE/BSE).
    Analyze the full news content below and provide a DEEP IMPACT REPORT.

    FINANCIAL THEORIES & MARKET LOGIC TO APPLY:
    1. Efficient Market Hypothesis (EMH) [Eugene Fama]: In an efficient market, prices instantly incorporate all available info. News doesn't just affect price; price is the sum of past news. You must determine if this news is genuinely new information or already priced in.
    2. Abnormal Returns (AR) Formula: AR = Actual Return - Expected Return. Think: What should the stock have done vs what will this news make it do? Positive AR means news is "better than expected". Zero AR means "priced in".
    3. The "Drift" Effect (PEAD) [Ball & Brown, 1968]: Post-Earnings Announcement Drift. Stocks don't react instantly to massive surprises; they drift in that direction for weeks. News has a "long tail" impact.
    4. Behavioral Finance: Markets overreact to negative panic and underreact to complex positive news. Consider sentiment extremes.
    5. Sector Contagion: A bankruptcy drags down a sector but benefits direct competitors. Supply chain breaks hurt downstream.

    THE MASTER FORMULA: NEWS IMPACT SCORE
    You MUST calculate the impact using this exact quantitative NLP framework internally.
    
    Step 1. NLP Sentiment Score (-1 to +1)
    - Very positive = +1.0, Positive = +0.5, Neutral = 0.0, Negative = -0.5, Very negative = -1.0
    
    Step 2. Surprise Factor (0.0 to 1.0) [MOST IMPORTANT]
    - If news is already known/expected = 0.1
    - Massive unexpected surprise = 1.0
    
    Step 3. Importance Weight (0.0 to 1.0)
    - Earnings/Major M&A = 1.0
    - Govt Policy/Interest Rates = 0.9
    - Large Order/Contract = 0.8
    - CEO/Mgmt Change = 0.6
    - Rumor/Speculation = 0.3
    - Trivial/Tweet = 0.2
    
    Step 4. Source Credibility (0.0 to 1.0)
    - Official Filing/Press Release = 1.0
    - Reuters/Bloomberg/Major Outlet = 0.9
    - Standard News Channel = 0.8
    - Twitter/Social Media = 0.4
    - Unknown/Unverified = 0.2
    
    Step 5. The News Z-Score (Outlier Check)
    - Evaluate if this news volume/severity is "market noise" (routine daily updates) or a "statistical outlier" (>2 standard deviations from normal = Real Trade Signal).
    - If it is just noise, artificially lower your final impact confidence.

    Step 6. IMPACT SCORE CALCULATION
    Internal Raw Score = (Sentiment * Surprise * Importance * Credibility)
    (Note: Assume Volume Spike is neutral/1.0 since you cannot read live volume)
    
    - If Raw Score > 0.7 AND high Z-Score ➔ STRONG BUY (Probability 85-100)
    - If Raw Score > 0.3 ➔ BUY (Probability 60-84)
    - If Raw Score between -0.3 and 0.3 or low Z-Score (noise) ➔ IGNORE (Return "impact": "no impact")
    - If Raw Score < -0.3 ➔ SELL (Probability 60-84)
    - If Raw Score < -0.7 AND high Z-Score ➔ STRONG SELL (Probability 85-100)

    RULES:
    1. Focus on specific stock/sector impacts.
    2. "probability" = likelihood the event happened (1-100).
    3. "confidence" = your analytical confidence (1-100).
    4. Use "NSE:SYMBOL" format.

    TRAINING EXAMPLES (Relevant to this news):
    {examples_text}

    TODAY IS: 2026-02-19.
    
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
     "event_date": "YYYY-MM-DD",
     "impact_date_est": "YYYY-MM-DD",
     "impact": "positive/negative/neutral",
     "strength": "low/medium/high",
     "reason": "Technical/Financial reason"
    }}

    Headline: "{headline}"
    Content:
    "{full_content[:4000]}"
    """
    
    print(f"  DEBUG: Performing DEEP ANALYSIS for: {headline[:50]}...")
    
    async with httpx.AsyncClient() as client:
        for model in MODELS:
            print(f"    > Attempting DEEP analysis with model: {model}")
            for i, api_key in enumerate(API_KEYS):
                if not api_key: continue
                # Skip depleted keys unless using a free model
                is_free_model = model.endswith(":free")
                if api_key in depleted_keys and not is_free_model:
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
                        data = json.loads(content)
                        
                        # Validate company name against official list
                        if 'company' in data and data['company']:
                            validated_name = validate_company_name(data['company'])
                            data['company'] = validated_name
                            
                            # Auto-inject symbol if known
                            if validated_name in COMPANY_SYMBOLS:
                                data['stocks'] = [COMPANY_SYMBOLS[validated_name]]
                            
                        return data
                    elif response.status_code == 402:
                        print(f"      >> Key {i+1} is out of credits (402). Skipping.")
                        depleted_keys.add(api_key)
                        continue
                    elif response.status_code == 429:
                        print(f"      >> Rate limit (429) on DEEP analysis. Rotating...")
                        continue
                    else:
                        print(f"      >> Deep Analysis Error {response.status_code} with Key {i+1}")
                        continue
                except Exception as e:
                    print(f"      >> Deep Analysis Exception with Key {i+1}: {e}")
                    continue
    # --- FALLBACK TO BYTEZ ---
    if BYTEZ_API_KEYS:
        print("  DEBUG: OpenRouter failed for DEEP analysis. Falling back to Bytez...")
        for b_key in BYTEZ_API_KEYS:
            try:
                sdk = Bytez(b_key)
                b_model_name = "google/gemma-3-12b-it" if "gemma" in MODELS[0].lower() else "openai/gpt-oss-20b"
                print(f"    > Attempting Bytez model for DEEP analysis: {b_model_name}")
                
                model = sdk.model(b_model_name)
                loop = asyncio.get_event_loop()
                results = await loop.run_in_executor(None, lambda: model.run([{"role": "user", "content": prompt}]))
                
                if results and hasattr(results, 'output') and results.output:
                    print("      >> Bytez DEEP analysis successful!")
                    
                    if isinstance(results.output, dict):
                        data = results.output
                    else:
                        content = results.output.strip().replace('```json', '').replace('```', '')
                        data = json.loads(content)
                        
                    if 'company' in data and data['company']:
                        validated_name = validate_company_name(data['company'])
                        data['company'] = validated_name
                        if validated_name in COMPANY_SYMBOLS:
                            data['stocks'] = [COMPANY_SYMBOLS[validated_name]]
                    return data
            except Exception as e:
                print(f"      >> Bytez DEEP analysis exception: {e}")
                continue

    return None

async def identify_high_impact_events(headlines):
    """
    PASS 1: Quickly identifies which headlines are highly impactful for the app.
    """
    results = []
    print(f"PASS 1: Identifying high-impact candidates from {len(headlines)} headlines...")
    
    # We use the existing analyze_headline as Pass 1 filter
    for i, h in enumerate(headlines[:20]):
        print(f"  Check ({i+1}/{min(len(headlines), 20)}): {h['title'][:50]}...")
        analysis = await analyze_headline(h['title'])
        if analysis.get('impact') != "no impact":
            # Tag as a candidate for Pass 2 if probability or strength is high
            analysis['id'] = h['link']
            analysis['link'] = h['link']
            analysis['published'] = h['published']
            results.append(analysis)
            print(f"    --> Candidate found: {analysis.get('event')}")
        else:
            print(f"    Result: No impact")
            
    return results

# analyze_headlines_bulk is now a legacy wrapper or can be removed if we update main.py
async def analyze_headlines_bulk(headlines):
    return await identify_high_impact_events(headlines)

import httpx
import json
import os
import asyncio
from dotenv import load_dotenv
from thefuzz import process

load_dotenv()

# Load company names for validation
COMPANY_NAMES = []
COMPANY_SYMBOLS = {}
try:
    with open(r"backend/data/company_names.json", "r", encoding="utf-8") as f:
        COMPANY_NAMES = json.load(f)
    print(f"Loaded {len(COMPANY_NAMES)} company names for validation.")
    
    if os.path.exists(r"backend/data/company_symbols.json"):
        with open(r"backend/data/company_symbols.json", "r", encoding="utf-8") as f:
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

# Updated API Keys provided by user
# Read API keys from environment variables
API_KEYS = []
for i in range(1, 6):
    key = os.environ.get(f"OPENROUTER_API_KEY_{i}")
    if key:
        API_KEYS.append(key.strip())

# Fallback if no specific keys found (check generic)
if not API_KEYS:
    generic_key = os.environ.get("OPENROUTER_API_KEY")
    if generic_key:
        API_KEYS.append(generic_key.strip())

# Last resort hardcoded keys (kept for absolute safety but environment is preferred)
if not API_KEYS:
    print("DEBUG: No API keys found in environment. Using fallback hardcoded keys.")
    API_KEYS = [
        "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",
        "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",
        "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",
        "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",
        "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"
    ]
else:
    print(f"DEBUG: Successfully loaded {len(API_KEYS)} API keys from environment.")

# Models in order of preference: Primary -> Backup
MODELS = [
    "openai/gpt-3.5-turbo", # Fast, reliable
    "openai/gpt-oss-20b:free", 
    "google/gemini-2.0-flash-lite-preview-02-05:free", # Added reliable fast model
    "google/gemma-3-12b-it:free",
    "mistralai/mistral-7b-instruct:free"
]

# Load training examples
TRAINING_EXAMPLES = []
try:
    if os.path.exists(r"backend/data/training_examples.json"):
        with open(r"backend/data/training_examples.json", "r", encoding="utf-8") as f:
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

async def analyze_headline(headline_text):
    # RAG-lite: Fetch relevant training examples
    relevant_examples = get_relevant_examples(headline_text, limit=3)
    examples_text = ""
    for i, ex in enumerate(relevant_examples):
        examples_text += f"\n    Example {i+1}:\n    News: {ex.get('news')}\n    Output: {json.dumps(ex)}\n"

    prompt = f"""
    You are an AI that detects whether a news event may impact publicly traded stocks or sectors.
    Analyze the news and return a structured JSON response.

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
                try:
                    display_key = f"{api_key[:6]}...{api_key[-4:]}"
                    print(f"      >> Trying Key {i+1} ({display_key}) on model {model}")
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
                            "messages": [
                                {"role": "user", "content": prompt}
                            ]
                        },
                        timeout=35
                    )
                    
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
                        continue
                except Exception as e:
                    print(f"      >> Exception with Key {i+1}: {e}")
                    continue
            
    print("  ERROR: All models and keys failed.")
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
                try:
                    response = await client.post(
                        url="https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": "http://localhost:8000",
                        },
                        json={
                            "model": model, 
                            "messages": [{"role": "user", "content": prompt}],
                            "response_format": { "type": "json_object" }
                        },
                        timeout=50
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
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
                    else:
                        print(f"      >> Deep Analysis Error {response.status_code} with Key {i+1}")
                except Exception as e:
                    print(f"      >> Deep Analysis Exception: {e}")
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

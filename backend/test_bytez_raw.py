import os
import sys
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from services.ai_service import clean_json_string

tests = [
    [{"generated_text": "```json\n{\"impact\": \"high\"}\n```"}],
    [{"output": "{\"impact\": \"high\"}"}],
    [{"text": "{\"impact\": \"high\"}"}],
    "{\"impact\": \"high\"}",
    "[{'generated_text': '```json\\n{\"impact\": \"high\"}\\n```'}]",
    "[{'output': '{\"impact\": \"high\"}'}]"
]

for t in tests:
    print("---")
    print(f"Input type: {type(t)}")
    raw_str = str(t)
    print("raw stringified:", repr(raw_str))
    res = clean_json_string(raw_str)
    try:
        j = json.loads(res)
        print("SUCCESS JSON:", j)
    except Exception as e:
        print("FAIL JSON decoded string:", repr(res))
        print("Exception:", e)

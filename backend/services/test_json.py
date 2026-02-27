import re
import json
import ast

def clean_json_string(content: str) -> str:
    if not isinstance(content, str): return ""
    if '```json' in content:
        content = content.split('```json')[1]
    elif '```' in content:
        content = content.split('```')[1]
    
    if '```' in content:
        content = content.split('```')[0]
        
    content = content.strip()
    
    if content.startswith("Output:"):
        content = content[len("Output:"):].strip()
        
    content = re.sub(r',\s*([}\]])', r'\1', content)
    
    try:
        json.loads(content)
        return content
    except json.JSONDecodeError:
        pass

    try:
        parsed_dict = ast.literal_eval(content)
        if isinstance(parsed_dict, dict):
            return json.dumps(parsed_dict)
    except:
        pass
        
    try:
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            extracted = match.group(0)
            extracted = extracted.replace("'", '"')
            json.loads(extracted)
            return extracted
    except:
        pass

    return content

# Test cases
bad_json_1 = "{'impact': 'high'}"
bad_json_2 = "Here is the output: {'impact': 'high'}"
bad_json_3 = "```json\n{'impact': 'high'}\n```"

print("Test 1:", clean_json_string(bad_json_1))
print("Test 2:", clean_json_string(bad_json_2))
print("Test 3:", clean_json_string(bad_json_3))

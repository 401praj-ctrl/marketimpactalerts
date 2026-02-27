import requests

try:
    response = requests.get("https://api.bytez.com/models")
    if response.status_code == 200:
        models = response.json()
        free_text = []
        for m in models:
            tags = m.get('tags', [])
            task = m.get('task', '')
            model_id = m.get('id', '')
            if 'free tier' in tags or 'free' in tags:
                if 'text-generation' in task or 'conversational' in task:
                    free_text.append(model_id)
        
        print("Free Text Generation Models on Bytez:")
        for ft in free_text:
            print(f" - {ft}")
    else:
        print(f"Failed to fetch: {response.status_code} {response.text}")
except Exception as e:
    print(f"Exception: {e}")

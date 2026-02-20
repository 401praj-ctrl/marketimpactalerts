import requests
import time

INSTANCES = [
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
    "https://nitter.lucabased.xyz",
    "https://nitter.cz",
    "https://nitter.projectsegfau.lt",
    "https://nitter.eu",
    "https://nitter.moomoo.me",
    "https://nitter.soopy.moe",
    "https://nitter.x86-64-unknown-linux-gnu.zip",
    "https://nitter.woodland.cafe",
    "https://nitter.catsarch.com",
    "https://nitter.perennialte.ch",
    "https://nitter.freedit.eu",
    "https://nitter.kavin.rocks"
]

TEST_ACCOUNT = "Deltaone"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

print("Testing Nitter instances with User-Agent...")
for instance in INSTANCES:
    url = f"{instance}/{TEST_ACCOUNT}/rss"
    try:
        start = time.time()
        response = requests.get(url, headers=headers, timeout=5)
        duration = time.time() - start
        
        if response.status_code == 200:
            print(f"✅ {instance} - OK ({duration:.2f}s)")
            # print(response.text[:200]) # First 200 chars
        else:
            print(f"❌ {instance} - Status {response.status_code}")
    except Exception as e:
        print(f"❌ {instance} - Error: {e}")

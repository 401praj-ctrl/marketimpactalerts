import trafilatura
import httpx
import asyncio

async def fetch_article_content(url):
    """
    Fetches the full article content from a URL and extracts clean text.
    """
    print(f"  SCRAPING: {url}")
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, timeout=15, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            if response.status_code == 200:
                downloaded = response.text
                # trafilatura extracts main content and ignores boilerplate
                content = trafilatura.extract(downloaded)
                if content:
                    # Limit content length to avoid context window issues
                    return content[:5000] 
                return "Could not extract clean text content."
            else:
                return f"Failed to fetch content. Status: {response.status_code}"
    except Exception as e:
        print(f"  Scraping Error: {e}")
        return f"Error during scraping: {str(e)}"

if __name__ == "__main__":
    # Test scraping
    async def test():
        url = "https://www.reuters.com/business/finance/indias-hdfc-bank-beats-q3-profit-estimates-2024-01-16/"
        content = await fetch_article_content(url)
        print(f"Content length: {len(content)}")
        print(f"Snippet: {content[:200]}...")
    
    asyncio.run(test())

import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import json
import os
import time
from datetime import datetime

# ==========================================
# CONFIGURATION
# ==========================================
SITEMAP_INDEX_URL = "https://docs.ravendb.net/sitemap.xml"
base_dir = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(base_dir, "collected_discussions")
RATE_LIMIT_DELAY = 1  

# The precise list of topics required for the Helpdesk Bot
MAIN_TOPICS = [
    "client-api",
    "indexes",
    "ai-integration",
    "vector-search",
    "attachments",     
    "getting-started",
    "installation",
    "studio",          
    "troubleshooting",
    "licensing"        
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def get_filtered_doc_links() -> list:
    """Dynamically unrolls the Sitemap Index, filters by target topics, and builds backend API URLs."""
    print(f"🔍 Fetching Master Sitemap from: {SITEMAP_INDEX_URL}...")
    try:
        response = requests.get(SITEMAP_INDEX_URL, headers=HEADERS, timeout=30)
        root = ET.fromstring(response.content)
        ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        # Extract links to nested sitemaps
        initial_locs = [loc.text for loc in root.findall('.//ns:loc', ns)]
        all_page_urls = []
        
        # Unroll all nested sitemaps to get raw page URLs
        for loc in initial_locs:
            if loc.endswith('.xml'):
                try:
                    sub_resp = requests.get(loc, headers=HEADERS, timeout=15)
                    sub_root = ET.fromstring(sub_resp.content)
                    sub_locs = [l.text for l in sub_root.findall('.//ns:loc', ns)]
                    all_page_urls.extend(sub_locs)
                except Exception:
                    pass
            else:
                all_page_urls.append(loc)
                
        print(f"🌍 Success! Discovered a massive total of {len(all_page_urls)} raw URLs across the site.")
        
        links = set()
        for url in all_page_urls:
            url = url.split('#')[0].rstrip('/')
            
            # 1. Check if it's a public version 7.2 URL
            if "/7.2/" in url:
                # 2. Semantic Filter: Keep only links containing our MAIN_TOPICS
                if any(topic in url.lower() for topic in MAIN_TOPICS):
                    
                    # === The Backend API Trick ===
                    # Extract the path after the version
                    # e.g., from: https://docs.ravendb.net/7.2/client-api/operations
                    # Extract: client-api/operations
                    path_after_version = url.split("/7.2/")[-1]
                    
                    # Construct the hidden backend API URL to fetch raw content (bypassing SPA/JS)
                    backend_api_url = f"https://ravendb.net/docs/article-page/7.2/csharp/{path_after_version}"
                    
                    # Store both URLs as a tuple: (Frontend URL for user, Backend URL for scraper)
                    links.add((url, backend_api_url))
                    
        discovered = list(links)
        print(f"🎯 Smart Hybrid Filter: Narrowed down to {len(discovered)} highly-relevant target pages!")
        return discovered
    except Exception as e:
        print(f"❌ Error during sitemap parsing: {e}")
        return []

def fetch_page(url: str) -> str:
    """Fetches HTML content safely with a delay."""
    try:
        time.sleep(RATE_LIMIT_DELAY)
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            return response.text
        return None
    except requests.RequestException:
        return None

def extract_doc_content(html: str, original_url: str) -> dict:
    """Extracts raw text, removing site navigation and noise."""
    soup = BeautifulSoup(html, 'html.parser')
    content_area = (
        soup.find('article') or 
        soup.find('div', class_='documentation-content') or
        soup.find('main')
    )
    if not content_area:
        content_area = soup.find('body')
        
    title_elem = soup.find('h1') or soup.find('title')
    title = title_elem.get_text(strip=True) if title_elem else original_url.split('/')[-1]
    
    if content_area:
        # Strip out code blocks from UI scripts, footers, etc.
        for tag in content_area.find_all(['script', 'style', 'nav', 'footer', 'aside']):
            tag.decompose()
        body = content_area.get_text(separator='\n', strip=True)
    else:
        body = ""
        
    return {
        'title': title,
        'url': original_url, # Save the original user-facing URL for the DB
        'body': body[:20000] # Safe limit for embedding models
    }

def main():
    print("=" * 60)
    print("🚀 RavenDB Smart Hybrid Scraper (The Backend API Trick)")
    print("=" * 60)
    
    urls_to_scrape = get_filtered_doc_links()
    
    if not urls_to_scrape:
        print("❌ No matching targeted links found. Exiting.")
        return
        
    collected_docs = []
    
    # Iterate over the tuples: (Frontend URL, Backend API URL)
    for idx, (original_url, api_fetch_url) in enumerate(urls_to_scrape, 1):
        topic_name = original_url.split("/7.2/")[-1]
        print(f"📄 [{idx}/{len(urls_to_scrape)}] Scrapping API for: {topic_name}...")
        
        # Fetch from the backend API, but attribute to the original URL
        html = fetch_page(api_fetch_url)
        if html:
            doc = extract_doc_content(html, original_url)
            if doc['body'] and len(doc['body']) > 100:
                collected_docs.append(doc)
            else:
                print("   ⚠️ Empty or too short, skipping")
        else:
            print("   ❌ Failed to fetch")
            
    if collected_docs:
        ravendb_docs = []
        for doc in collected_docs:
            ravendb_docs.append({
                "@metadata": {"@collection": "Documentation"},
                "Source": "RavenDBDocs",
                "Title": doc['title'],
                "Url": doc['url'],
                "Body": doc['body'],
                "CollectedAt": datetime.now().isoformat(),
                "SearchableContent": f"{doc['title']} {doc['body']}"
            })
            
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        latest_path = os.path.join(OUTPUT_DIR, "documentation_latest.json")
        with open(latest_path, 'w', encoding='utf-8') as f:
            json.dump(ravendb_docs, f, ensure_ascii=False, indent=2)
            
        print("\n" + "=" * 60)
        print(f"✅ Masterpiece completed! Saved {len(ravendb_docs)} pure gold pages to {latest_path}")
        print("=" * 60)

if __name__ == "__main__":
    main()
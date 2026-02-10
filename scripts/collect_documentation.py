"""
RavenDB Documentation Collector
Collects documentation pages from RavenDB official docs for AI training

Usage:
    python collect_documentation.py

The official RavenDB documentation is at: https://ravendb.net/docs
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import time
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
import re

# Configuration
DOCS_BASE_URL = "https://ravendb.net/docs/article-page/7.0"
DOCS_SECTIONS = [
    "/csharp",  # C# Documentation
    "/python",  # Python Documentation
]

OUTPUT_DIR = "collected_discussions"
RATE_LIMIT_DELAY = 1  # seconds between requests

# Headers
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

# Key documentation topics to collect
DOC_TOPICS = [
    # Getting Started
    "getting-started",
    "start/getting-started",
    "start/installation",
    
    # AI & Vector Search (Most Relevant!)
    "ai-integration",
    "ai-integration/ai-agents",
    "ai-integration/vector-search",
    "ai-integration/generating-embeddings",
    
    # Client API
    "client-api/session",
    "client-api/operations",
    "client-api/bulk-insert",
    
    # Indexes
    "indexes/what-are-indexes",
    "indexes/creating-and-deploying",
    "indexes/querying",
    
    # Studio
    "studio/overview",
    "studio/database/indexes",
    
    # Cloud
    "cloud/cloud-instances",
]


def fetch_page(url: str) -> Optional[str]:
    """Fetch a page with rate limiting."""
    try:
        time.sleep(RATE_LIMIT_DELAY)
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            return response.text
        else:
            print(f"⚠️ Status {response.status_code} for {url}")
            return None
    except requests.RequestException as e:
        print(f"❌ Error fetching {url}: {e}")
        return None


def extract_doc_content(html: str, url: str) -> Dict:
    """Extract documentation content from a page."""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Try to find main content area
    content_area = (
        soup.find('article') or 
        soup.find('div', class_='documentation-content') or
        soup.find('div', class_='content') or
        soup.find('main')
    )
    
    if not content_area:
        content_area = soup.find('body')
    
    # Get title
    title = ""
    title_elem = soup.find('h1') or soup.find('title')
    if title_elem:
        title = title_elem.get_text(strip=True)
    
    # Get text content
    body = ""
    if content_area:
        # Remove scripts and styles
        for tag in content_area.find_all(['script', 'style', 'nav', 'footer']):
            tag.decompose()
        body = content_area.get_text(separator='\n', strip=True)
    
    # Get code examples
    code_examples = []
    for code_block in soup.find_all(['code', 'pre']):
        code_text = code_block.get_text(strip=True)
        if len(code_text) > 50:  # Only meaningful code blocks
            code_examples.append(code_text[:500])  # Limit size
    
    return {
        'title': title,
        'url': url,
        'body': body[:10000],  # Limit body size
        'code_examples': code_examples[:5],  # Limit examples
    }


def collect_documentation() -> List[Dict]:
    """Collect documentation from RavenDB docs."""
    print("=" * 60)
    print("🚀 RavenDB Documentation Collector")
    print("=" * 60)
    print(f"Base URL: {DOCS_BASE_URL}")
    print()
    
    collected_docs = []
    
    for topic in DOC_TOPICS:
        url = f"{DOCS_BASE_URL}/csharp/{topic}"
        print(f"📄 Fetching: {topic}...")
        
        html = fetch_page(url)
        if html:
            doc = extract_doc_content(html, url)
            if doc['body']:
                collected_docs.append(doc)
                print(f"   ✅ Collected: {doc['title'][:50]}...")
            else:
                print(f"   ⚠️ No content found")
        else:
            print(f"   ❌ Failed to fetch")
    
    return collected_docs


def save_documentation(docs: List[Dict]):
    """Save documentation to JSON file for RavenDB import."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Format for RavenDB
    ravendb_docs = []
    for doc in docs:
        ravendb_doc = {
            "@metadata": {
                "@collection": "Documentation"
            },
            "Source": "RavenDBDocs",
            "Title": doc['title'],
            "Url": doc['url'],
            "Body": doc['body'],
            "CodeExamples": doc.get('code_examples', []),
            "CollectedAt": datetime.now().isoformat(),
            "SearchableContent": f"{doc['title']} {doc['body']}"
        }
        ravendb_docs.append(ravendb_doc)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"documentation_{timestamp}.json"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(ravendb_docs, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Saved to {filepath}")
    
    # Also save as latest
    latest_path = os.path.join(OUTPUT_DIR, "documentation_latest.json")
    with open(latest_path, 'w', encoding='utf-8') as f:
        json.dump(ravendb_docs, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Saved to {latest_path}")
    
    return len(ravendb_docs)


def main():
    """Main entry point."""
    print()
    
    # Collect documentation
    docs = collect_documentation()
    
    if docs:
        count = save_documentation(docs)
        print()
        print("=" * 60)
        print(f"✅ Collected {count} documentation pages!")
        print("=" * 60)
        print()
        print("📊 Data Sources Summary:")
        print(f"   - GitHub Discussions: 1,052 discussions")
        print(f"   - RavenDB Docs: {count} pages")
        print()
    else:
        print("❌ No documentation collected")
        print()
        print("💡 Alternative: Use the official docs manually")
        print("   https://ravendb.net/docs/article-page/7.0/csharp")


if __name__ == "__main__":
    main()

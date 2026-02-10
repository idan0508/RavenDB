"""
RavenDB Google Groups Discussion Collector
Collects discussions from Google Groups for RavenDB Helpdesk AI

Usage:
    python collect_google_groups.py

Note: Google Groups doesn't have an official API, so this uses web scraping.
Rate limiting is applied to be respectful to the server.
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import time
from datetime import datetime
from typing import List, Dict, Optional
import re

# Configuration
GOOGLE_GROUPS_URL = "https://groups.google.com/g/ravendb"
OUTPUT_DIR = "collected_discussions"
RATE_LIMIT_DELAY = 2  # seconds between requests

# Headers to mimic a browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}


def fetch_page(url: str) -> Optional[str]:
    """Fetch a page with rate limiting and error handling."""
    try:
        time.sleep(RATE_LIMIT_DELAY)
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"❌ Error fetching {url}: {e}")
        return None


def parse_discussion_list(html: str) -> List[Dict]:
    """Parse the discussion list page to extract topics."""
    soup = BeautifulSoup(html, 'html.parser')
    discussions = []
    
    # Find discussion entries (Google Groups structure may vary)
    # This is a simplified parser - may need adjustment based on actual page structure
    topic_elements = soup.find_all('div', class_='topic-item') or soup.find_all('tr', class_='topic')
    
    for topic in topic_elements:
        try:
            title_elem = topic.find('a', class_='topic-title') or topic.find('a')
            if title_elem:
                discussions.append({
                    'title': title_elem.get_text(strip=True),
                    'url': title_elem.get('href', ''),
                })
        except Exception as e:
            print(f"⚠️ Error parsing topic: {e}")
            continue
    
    return discussions


def collect_from_google_groups() -> List[Dict]:
    """
    Collect discussions from Google Groups.
    
    Note: Google Groups has dynamic content loaded via JavaScript,
    which makes direct scraping difficult. This function provides
    a basic structure, but for full functionality, consider:
    1. Using Selenium for dynamic content
    2. Using the unofficial Google Groups API
    3. Manual export from Google Groups
    """
    print("=" * 60)
    print("🚀 RavenDB Google Groups Collector")
    print("=" * 60)
    print(f"Target: {GOOGLE_GROUPS_URL}")
    print()
    
    # Try to fetch the page
    print("📄 Attempting to fetch Google Groups page...")
    html = fetch_page(GOOGLE_GROUPS_URL)
    
    if not html:
        print("❌ Could not fetch Google Groups page.")
        print()
        print("🔧 Alternative options:")
        print("   1. Google Groups uses JavaScript - consider using Selenium")
        print("   2. Export manually from Google Groups interface")
        print("   3. Use Google Takeout to export group data")
        print()
        return []
    
    # Try to parse discussions
    discussions = parse_discussion_list(html)
    print(f"📊 Found {len(discussions)} discussions")
    
    return discussions


def save_discussions(discussions: List[Dict], source: str = "google_groups"):
    """Save discussions to JSON file."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Format for RavenDB import
    ravendb_docs = []
    for discussion in discussions:
        doc = {
            "@metadata": {
                "@collection": "GoogleGroupsDiscussions"
            },
            "Source": "GoogleGroups",
            "Title": discussion.get('title', ''),
            "Url": discussion.get('url', ''),
            "Body": discussion.get('body', ''),
            "Author": discussion.get('author', 'Unknown'),
            "CreatedAt": discussion.get('created_at', datetime.now().isoformat()),
            "SearchableContent": f"{discussion.get('title', '')} {discussion.get('body', '')}"
        }
        ravendb_docs.append(doc)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{source}_{timestamp}.json"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(ravendb_docs, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Saved to {filepath}")
    
    # Also save as latest
    latest_path = os.path.join(OUTPUT_DIR, f"{source}_latest.json")
    with open(latest_path, 'w', encoding='utf-8') as f:
        json.dump(ravendb_docs, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Saved to {latest_path}")


def print_manual_export_guide():
    """Print instructions for manual export from Google Groups."""
    print()
    print("=" * 60)
    print("📋 Manual Export Guide for Google Groups")
    print("=" * 60)
    print()
    print("Since Google Groups requires JavaScript and doesn't have")
    print("a public API, here's how to manually export data:")
    print()
    print("Option 1: Google Takeout")
    print("   1. Go to: https://takeout.google.com")
    print("   2. Select 'Groups'")
    print("   3. Choose format and download")
    print("   4. Convert the exported data to our JSON format")
    print()
    print("Option 2: Manual Collection")
    print("   1. Go to: https://groups.google.com/g/ravendb")
    print("   2. Browse discussions and copy relevant Q&As")
    print("   3. Format and add to our JSON file")
    print()
    print("Option 3: Selenium Script (Recommended)")
    print("   1. Install: pip install selenium webdriver-manager")
    print("   2. Use the selenium version of this script")
    print("   3. It will handle JavaScript-rendered content")
    print()


def main():
    """Main entry point."""
    print()
    print("⚠️  Important Note About Google Groups")
    print("=" * 60)
    print("Google Groups uses JavaScript to render content dynamically.")
    print("Direct web scraping has limited success.")
    print()
    
    # Try basic scraping first
    discussions = collect_from_google_groups()
    
    if discussions:
        save_discussions(discussions)
        print()
        print(f"✅ Collected {len(discussions)} discussions!")
    else:
        print_manual_export_guide()
    
    print()
    print("=" * 60)
    print("💡 Recommendation:")
    print("   For best results, focus on GitHub Discussions")
    print("   which we already collected (1,052 discussions).")
    print("   Google Groups can be added later if needed.")
    print("=" * 60)


if __name__ == "__main__":
    main()

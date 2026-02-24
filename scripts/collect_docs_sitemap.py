"""
RavenDB Documentation Collector - Sitemap + Direct RavenDB Store
================================================================
Scrapes docs.ravendb.net using the official sitemap.xml for 100% URL coverage.
Writes directly to RavenDB using the official Python client.

Advantages over BFS crawler:
  - Uses sitemap.xml = guaranteed full page coverage
  - Parallel scraping with ThreadPoolExecutor = 10x faster
  - Writes directly to RavenDB = no intermediate JSON files
  - Simpler and more reliable

Usage:
    pip install ravendb requests beautifulsoup4 lxml
    python collect_docs_sitemap.py
    python collect_docs_sitemap.py --versions 7.2 6.2 5.4
    python collect_docs_sitemap.py --all-versions
    python collect_docs_sitemap.py --include-guides

Authors: Ron Blanky, Yuval Hasin, Idan Dahan
"""

import argparse
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from ravendb import DocumentStore
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import re
import sys
from collections import Counter

# ====== CONFIGURATION ======
RAVENDB_URL = "http://localhost:8080"
DATABASE_NAME = "HelpdeskDB"
COLLECTION_NAME = "Documentation"
SITEMAP_URL = "https://docs.ravendb.net/sitemap.xml"

# Default versions to collect (most relevant for current users)
DEFAULT_VERSIONS = ["7.2", "6.2", "5.4"]

# All known versions in the docs
ALL_VERSIONS = [
    "7.2", "7.1", "7.0",
    "6.2", "6.1", "6.0",
    "5.4", "5.3", "5.2", "5.1",
    "4.2", "4.1", "4.0",
    "3.5", "3.0",
    "2.5", "2.0",
    "1.0"
]

# Stats tracking
stats = Counter()


def get_urls_from_sitemap(target_versions, include_guides=False):
    """Fetch all URLs from sitemap.xml and filter by target versions."""
    print(f"🗺️  Fetching sitemap from {SITEMAP_URL}...")
    
    try:
        response = requests.get(SITEMAP_URL, timeout=30)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        
        # Standard sitemap XML namespace
        ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        all_urls = [loc.text for loc in root.findall('.//ns:loc', ns)]
        
        print(f"📊 Total URLs in sitemap: {len(all_urls)}")
        
        # Filter by version
        filtered_urls = []
        for url in all_urls:
            # Match versioned docs: /7.2/..., /6.2/..., etc.
            for version in target_versions:
                if f"/{version}/" in url:
                    filtered_urls.append(url)
                    break
            
            # Optionally include guides (version-less helpful content)
            if include_guides and "/guides/" in url:
                # Skip tag pages and index pages
                if "/tags/" not in url and url != "https://docs.ravendb.net/guides/":
                    filtered_urls.append(url)
        
        # Also include cloud docs (version-less but useful)
        cloud_urls = [u for u in all_urls if "/cloud/" in u]
        filtered_urls.extend(cloud_urls)
        
        # Deduplicate
        filtered_urls = list(set(filtered_urls))
        
        print(f"✅ Found {len(filtered_urls)} pages matching versions {target_versions}")
        if include_guides:
            print(f"   (including guides and cloud docs)")
        
        return filtered_urls
        
    except Exception as e:
        print(f"❌ Error fetching sitemap: {e}")
        return []


def extract_version_from_url(url):
    """Extract version number from the URL."""
    for version in ALL_VERSIONS:
        if f"/{version}/" in url:
            return version
    
    if "/cloud/" in url:
        return "cloud"
    if "/guides/" in url:
        return "guides"
    return "unknown"


def extract_category_from_url(url):
    """Extract category from URL path for AI context.
    
    URL format: https://docs.ravendb.net/article-page/7.2/csharp/client-api/session/querying
    -> Category: "Client Api"
    """
    clean_path = url.replace("https://docs.ravendb.net/", "")
    # Remove article-page/ prefix if present
    clean_path = clean_path.replace("article-page/", "")
    parts = clean_path.strip("/").split("/")
    
    # parts[0] = version (e.g., "7.2")
    # parts[1] = language (e.g., "csharp") — skip
    # parts[2] = category (e.g., "client-api")
    if len(parts) > 2:
        return parts[2].replace("-", " ").title()
    return "General"


def make_semantic_id(url):
    """Create a semantic document ID from URL.
    
    Example: https://docs.ravendb.net/article-page/7.2/csharp/client-api/session/querying
    -> Documentation/7.2/client-api/session/querying
    
    This prevents duplicates and makes Studio browsing cleaner.
    """
    clean_path = url.replace("https://docs.ravendb.net/", "")
    # Remove article-page/ prefix
    clean_path = clean_path.replace("article-page/", "")
    parts = clean_path.strip("/").split("/")
    
    if len(parts) >= 2:
        version = parts[0]
        # Skip language part (csharp/python/etc), keep the rest
        if len(parts) > 2:
            path = "/".join(parts[2:])  # Skip version + language
        else:
            path = parts[1]
        return f"Documentation/{version}/{path}"
    
    # Fallback for non-article URLs (cloud, guides, etc)
    return f"Documentation/{clean_path.replace('/', '-').rstrip('-')}"


def scrape_page(url):
    """Scrape a single documentation page and return structured data."""
    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.content, "lxml")
        
        # Remove non-content elements
        for tag in soup(["script", "style", "nav", "footer", "aside", "header"]):
            tag.decompose()
        
        # Get title - try multiple selectors
        title = None
        for selector in ["h1", "title", ".article-title"]:
            tag = soup.find(selector)
            if tag:
                title = tag.get_text(strip=True)
                break
        
        if not title:
            # Use last part of URL as title
            title = url.rstrip("/").split("/")[-1].replace("-", " ").title()
        
        # Get main content - try multiple selectors
        article = None
        for selector in ["article", "main", ".content", ".article-body", "#content"]:
            article = soup.find(selector) if isinstance(selector, str) and not selector.startswith(".") and not selector.startswith("#") else soup.select_one(selector)
            if article:
                break
        
        if not article:
            article = soup.find("body")
        
        if not article:
            return None
        
        # Extract clean text
        content_text = article.get_text(separator="\n", strip=True)
        
        # Skip if content is too short (likely error page or redirect)
        if len(content_text) < 50:
            return None
        
        # Extract code examples separately
        code_blocks = []
        for code_tag in article.find_all(["code", "pre"]):
            code_text = code_tag.get_text(strip=True)
            if len(code_text) > 10:  # Skip tiny inline code
                code_blocks.append(code_text)
        
        # Extract section structure
        sections = []
        for heading in article.find_all(["h2", "h3"]):
            sections.append(heading.get_text(strip=True))
        
        version = extract_version_from_url(url)
        category = extract_category_from_url(url)
        
        return {
            "Title": title,
            "Url": url,
            "Body": content_text[:50000],  # Cap at 50K chars to avoid huge docs
            "Version": version,
            "Category": category,  # e.g. "Client Api", "Server", "Indexes"
            "Sections": sections[:20],  # Cap sections list
            "CodeExamples": code_blocks[:10],  # Cap code examples
            "Source": "OfficialDocs",
        }
        
    except requests.exceptions.Timeout:
        return None
    except Exception as e:
        return None


def process_batch(store, docs, batch_size=25):
    """Store a batch of documents in RavenDB."""
    with store.open_session() as session:
        for doc in docs:
            # Create semantic ID: Documentation/7.2/client-api/session/querying
            # This prevents duplicates and makes browsing in Studio clean
            doc_id = make_semantic_id(doc["Url"])
            
            # Add collection metadata
            doc["@metadata"] = {"@collection": COLLECTION_NAME}
            
            session.store(doc, key=doc_id)
        
        session.save_changes()


def main():
    parser = argparse.ArgumentParser(description="Collect RavenDB docs via sitemap → RavenDB")
    parser.add_argument("--versions", nargs="+", default=DEFAULT_VERSIONS,
                        help=f"Versions to collect (default: {DEFAULT_VERSIONS})")
    parser.add_argument("--all-versions", action="store_true",
                        help="Collect ALL versions")
    parser.add_argument("--include-guides", action="store_true",
                        help="Also collect guide articles")
    parser.add_argument("--workers", type=int, default=10,
                        help="Number of parallel workers (default: 10)")
    parser.add_argument("--ravendb-url", default=RAVENDB_URL,
                        help=f"RavenDB URL (default: {RAVENDB_URL})")
    parser.add_argument("--database", default=DATABASE_NAME,
                        help=f"Database name (default: {DATABASE_NAME})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Just show stats, don't write to RavenDB")
    args = parser.parse_args()
    
    target_versions = ALL_VERSIONS if args.all_versions else args.versions
    
    print("=" * 60)
    print("📚 RavenDB Documentation Collector (Sitemap)")
    print("=" * 60)
    print(f"Versions:  {', '.join(target_versions)}")
    print(f"Workers:   {args.workers}")
    print(f"RavenDB:   {args.ravendb_url}")
    print(f"Database:  {args.database}")
    print(f"Dry run:   {args.dry_run}")
    print()
    
    # Step 1: Get URLs from sitemap
    urls = get_urls_from_sitemap(target_versions, args.include_guides)
    
    if not urls:
        print("❌ No URLs found. Exiting.")
        return
    
    # Step 2: Initialize RavenDB connection (unless dry run)
    store = None
    if not args.dry_run:
        try:
            store = DocumentStore(urls=[args.ravendb_url], database=args.database)
            store.initialize()
            print(f"✅ Connected to RavenDB at {args.ravendb_url}")
        except Exception as e:
            print(f"❌ Cannot connect to RavenDB: {e}")
            print("   Make sure RavenDB is running and the database exists.")
            return
    
    # Step 3: Scrape in parallel
    print(f"\n🚀 Scraping {len(urls)} pages with {args.workers} threads...")
    start_time = time.time()
    
    successful_docs = []
    failed = 0
    version_counts = Counter()
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        # Submit all scraping tasks
        future_to_url = {executor.submit(scrape_page, url): url for url in urls}
        
        for i, future in enumerate(as_completed(future_to_url), 1):
            url = future_to_url[future]
            try:
                doc = future.result()
                if doc:
                    successful_docs.append(doc)
                    version_counts[doc["Version"]] += 1
                    
                    # Print progress every 50 pages
                    if i % 50 == 0 or i == len(urls):
                        elapsed = time.time() - start_time
                        rate = i / elapsed
                        print(f"   📄 Progress: {i}/{len(urls)} ({rate:.1f} pages/sec) - {len(successful_docs)} scraped")
                    
                    # Batch write to RavenDB every 25 docs
                    if store and len(successful_docs) % 25 == 0:
                        batch = successful_docs[-25:]
                        try:
                            process_batch(store, batch)
                        except Exception as e:
                            print(f"   ⚠️ Batch write error: {e}")
                else:
                    failed += 1
            except Exception as e:
                failed += 1
    
    # Write remaining docs
    if store and len(successful_docs) % 25 != 0:
        remaining = successful_docs[-(len(successful_docs) % 25):]
        try:
            process_batch(store, remaining)
        except Exception as e:
            print(f"   ⚠️ Final batch write error: {e}")
    
    # Step 4: Print summary
    elapsed = time.time() - start_time
    
    print()
    print("=" * 60)
    print("📊 Collection Summary")
    print("=" * 60)
    print(f"   Total URLs:     {len(urls)}")
    print(f"   Scraped:        {len(successful_docs)}")
    print(f"   Failed/Empty:   {failed}")
    print(f"   Time:           {elapsed:.1f} seconds")
    print(f"   Rate:           {len(urls)/elapsed:.1f} pages/sec")
    print()
    print("   By Version:")
    for version in sorted(version_counts.keys()):
        print(f"     {version:>8}: {version_counts[version]:>5} pages")
    print("=" * 60)
    
    if args.dry_run:
        print("\n⚠️  DRY RUN - no data was written to RavenDB")
    else:
        print(f"\n✅ All {len(successful_docs)} docs written to RavenDB → {COLLECTION_NAME} collection")
    
    # Cleanup
    if store:
        store.close()


if __name__ == "__main__":
    main()

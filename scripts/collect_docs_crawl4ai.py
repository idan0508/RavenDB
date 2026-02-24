"""
RavenDB Documentation Collector - Crawl4AI Smart Markdown Scraper
================================================================
An advanced, adaptive web crawler designed specifically for LLM/RAG ingestion.
This script uses Crawl4AI (via Playwright) to render JavaScript tabs, extract 
clean Markdown, and strip out unnecessary HTML navigation headers.

IMPORTANT: Because this runs a real headless browser (Chromium) and respects 
polite scraping delays, it is much slower than the basic requests script. 
It is recommended to run this overnight.

Hardware: This runs entirely on your CPU and RAM. It does not use your RTX 4060 GPU.
More info: https://crawl4ai.com/

Dependencies:
    pip install "crawl4ai[all]" ravendb
    playwright install chromium
"""

import sys
import asyncio
from typing import List, Dict, Any
from urllib.parse import urlparse

try:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
except ImportError:
    print("❌ Crawl4AI is not installed. Please run: pip install crawl4ai")
    sys.exit(1)

from ravendb import DocumentStore

# ====== CONFIGURATION ======
RAVENDB_URL = "http://localhost:8080"
DATABASE_NAME = "HelpdeskDB"
COLLECTION_NAME = "Documentation"
CONFIG_CONCURRENCY = 3  # Keep low to prevent overwhelming the RavenDB docs server

# The specific versions requested by the architecture document isolated pipelines
TARGET_VERSIONS = ["7.2", "6.2", "5.4"]

def make_semantic_id(url: str) -> str:
    """Create a semantic document ID from URL."""
    clean_path = url.replace("https://docs.ravendb.net/", "").replace("article-page/", "")
    parts = clean_path.strip("/").split("/")
    
    if len(parts) >= 2:
        version = parts[0]
        path = "/".join(parts[2:]) if len(parts) > 2 else parts[1]
        return f"Documentation/{version}/{path}"
    return f"Documentation/{clean_path.replace('/', '-').rstrip('-')}"


async def process_and_store_urls(urls: List[str]):
    """
    Spins up the AsyncWebCrawler to render the pages, execute JavaScript (to open tabs),
    and extract pure Markdown.
    """
    print(f"🚀 Starting Crawl4AI Headless Browser pipeline for {len(urls)} URLs...")
    print(f"⚠️  This uses your CPU/RAM (Playwright Browser), NOT your GPU.")
    
    # Configure the browser to be headless and efficient
    browser_config = BrowserConfig(
        headless=True,
        verbose=False
    )
    
    # Configure the crawler rule-set
    # We use a CSS selector to ONLY scrape the <article> or main content area, 
    # completely ignoring the sidebar navigation and footers!
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        css_selector=".content-pane, article, main", # Target the meat of the RavenDB docs
        exclude_external_links=True,
        word_count_threshold=50, # Skip empty or error pages
        delay_before_return_html=1.5 # Wait 1.5 seconds for JS tabs to finish rendering!
    )

    try:
        store = DocumentStore(urls=[RAVENDB_URL], database=DATABASE_NAME)
        store.initialize()
        print(f"✅ Connected to RavenDB at {RAVENDB_URL}")
    except Exception as e:
        print(f"❌ Cannot connect to RavenDB: {e}")
        return

    async with AsyncWebCrawler(config=browser_config) as crawler:
        processed_count = 0
        
        # We process in small chunks to avoid memory blowing up
        for i in range(0, len(urls), CONFIG_CONCURRENCY):
            batch_urls = urls[i:i + CONFIG_CONCURRENCY]
            
            # Run the crawler concurrently for this batch
            tasks = [crawler.arun(url=url, config=run_config) for url in batch_urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            with store.open_session() as session:
                for url, result in zip(batch_urls, results):
                    if isinstance(result, Exception):
                        print(f"❌ Failed to crawl {url}: {result}")
                        continue
                        
                    if not result.success:
                        print(f"⚠️ Crawl failed for {url}: {result.error_message}")
                        continue
                        
                    # result.markdown contains the magically clean, formatted Markdown!
                    markdown_content = result.markdown
                    
                    if not markdown_content or len(markdown_content) < 50:
                        continue
                        
                    doc_id = make_semantic_id(url)
                    
                    # We store the pure Markdown in the 'Body' field.
                    # The AI Agent will read this perfectly because LLMs natively understand Markdown.
                    doc = {
                        "Url": url,
                        "Body": markdown_content,
                        "Source": "OfficialDocs_Crawl4AI",
                        "@metadata": {"@collection": COLLECTION_NAME}
                    }
                    
                    session.store(doc, key=doc_id)
                    processed_count += 1
                
                # Save batch to database
                session.save_changes()
                print(f"   💾 Saved batch to RavenDB. Progress: {min(i + CONFIG_CONCURRENCY, len(urls))}/{len(urls)}")
                
            # Sleep between batches - BE POLITE to the docs server! (Rate limiting)
            await asyncio.sleep(2)
            
    print(f"\n🎉 Finished! Successfully processed and stored {processed_count} highly-formatted Markdown pages.")
    store.close()

if __name__ == "__main__":
    # For demonstration, we just use a tiny hardcoded list.
    # In a real run, you would combine this with the sitemap logic from your previous script!
    test_urls = [
        "https://docs.ravendb.net/article-page/7.2/csharp/client-api/session/querying/how-to-query",
        "https://docs.ravendb.net/article-page/7.2/csharp/indexes/querying/vector-search"
    ]
    
    print("WARNING: You must have Crawl4AI installed:")
    print("1. pip install crawl4ai")
    print("2. playwright install")
    print("-" * 50)
    
    asyncio.run(process_and_store_urls(test_urls))

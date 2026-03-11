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
import re
import asyncio
from typing import List, Dict, Any
from urllib.parse import urlparse

# Fix Windows console encoding (cp1252 can't print special characters)
import io
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
except ImportError:
    print("❌ Crawl4AI is not installed. Please run: pip install crawl4ai")
    sys.exit(1)

from ravendb import DocumentStore

# ====== CONFIGURATION ======
RAVENDB_URL = "http://localhost:8080"
DATABASE_NAME = "HelpdeskDB"
COLLECTION_NAME = "Documentation_Crawl4AI"
CONFIG_CONCURRENCY = 3  # Keep low to prevent overwhelming the RavenDB docs server

# The specific versions requested by the architecture document isolated pipelines
TARGET_VERSIONS = ["7.2", "6.2", "5.4"]

# All known RavenDB doc versions (for version detection in URLs)
ALL_VERSIONS = ["7.2", "6.2", "6.0", "5.4", "5.3", "5.2", "5.1", "5.0",
                "4.2", "4.1", "4.0", "3.5", "3.0", "2.5", "2.0", "1.0"]


# ====== METADATA EXTRACTION ======
def extract_version_from_url(url: str) -> str:
    """Extract version number from the URL."""
    for version in ALL_VERSIONS:
        if f"/{version}/" in url:
            return version
    if "/cloud/" in url:
        return "cloud"
    if "/guides/" in url:
        return "guides"
    return "unknown"


def extract_category_from_url(url: str) -> str:
    """Extract category from URL path for AI context.
    
    URL format: https://docs.ravendb.net/7.2/ai-integration/vector-search/...
    -> Category: "Ai Integration"
    """
    clean_path = url.replace("https://docs.ravendb.net/", "")
    parts = clean_path.strip("/").split("/")
    
    # parts[0] = version (e.g., "7.2")
    # parts[1] = category (e.g., "ai-integration")
    if len(parts) > 1:
        return parts[1].replace("-", " ").title()
    return "General"


def extract_title_from_url(url: str) -> str:
    """Extract a human-readable title from URL as fallback.
    
    URL: https://docs.ravendb.net/7.2/ai-integration/vector-search/indexing-attachments-for-vector-search/
    -> "Indexing Attachments For Vector Search"
    """
    last_segment = url.rstrip("/").split("/")[-1]
    return last_segment.replace("-", " ").title()


def extract_title_from_markdown(markdown: str) -> str:
    """Extract the first H1 heading from Markdown content as the title."""
    match = re.search(r'^#\s+(.+)$', markdown, re.MULTILINE)
    if match:
        # Clean up any trailing link markers like [](...)
        title = re.sub(r'\[.*?\]\(.*?\)', '', match.group(1)).strip()
        return title
    return ""


def extract_sections_from_markdown(markdown: str) -> list:
    """Extract H2/H3 headings from Markdown content as section names."""
    sections = []
    for match in re.finditer(r'^#{2,3}\s+(.+?)(?:\[|$)', markdown, re.MULTILINE):
        section_name = match.group(1).strip()
        if section_name and section_name not in sections:
            sections.append(section_name)
    return sections[:20]  # Cap at 20 sections


# ====== DEDUPLICATION ======
def deduplicate_markdown(markdown: str) -> str:
    """Smart, generic cleanup of scraped RavenDB documentation markdown.
    
    Works for ANY page, no hardcoded page names or categories.
    
    Strategy:
      1. Cut everything BEFORE the first H1 heading (removes breadcrumbs)
      2. Cut everything from the SECOND H1 onward (removes full-page duplicate)
      3. Remove all 'C#PythonNode.js' lines globally (UI tab selectors, not content)
      4. Smart footer detection: find the bare page title near the end and cut from there
    """
    if not markdown:
        return markdown
    
    lines = markdown.split('\n')
    
    # === STEP 1: Find the first H1 heading — everything before it is noise ===
    h1_pattern = re.compile(r'^#\s+\S')
    first_h1_idx = None
    first_h1_text = None
    
    for i, line in enumerate(lines):
        if h1_pattern.match(line.strip()):
            first_h1_idx = i
            first_h1_text = line.strip()
            break
    
    if first_h1_idx is not None:
        lines = lines[first_h1_idx:]
    
    # === STEP 2: Find the SECOND occurrence of the same H1 — cut from there ===
    if first_h1_text:
        for i, line in enumerate(lines):
            if i == 0:
                continue
            if line.strip() == first_h1_text:
                lines = lines[:i]
                break
    
    # === STEP 3: Remove ALL 'C#PythonNode.js' lines (tab selectors, not content) ===
    # These appear on every multi-language page as UI elements.
    lines = [l for l in lines if l.strip() != 'C#PythonNode.js']
    
    # === STEP 4: Smart footer detection ===
    # The footer on every RavenDB docs page follows this pattern (from bottom):
    #   "In this article"           (ToC sidebar repeat)
    #   "* Page Title"              (breadcrumb)
    #   "* Category Name"           (breadcrumb)  
    #   "* [Docs](link)"            (breadcrumb)
    #   "C#PythonNode.js"           (already removed in step 3)
    #   "Page Title"                (bare title, no # prefix)
    #
    # We search backwards from the end for the bare title text.
    # If found in the last ~30 lines, everything from there onward is footer.
    if first_h1_text:
        bare_title = first_h1_text.lstrip('#').strip()
        search_range = min(30, len(lines))
        for i in range(len(lines) - 1, max(len(lines) - search_range - 1, -1), -1):
            stripped = lines[i].strip()
            # Match bare title (exact or as a list item like "* Title")
            if stripped == bare_title or stripped == f'* {bare_title}':
                lines = lines[:i]
                break
    
    # Strip any remaining trailing noise (empty lines, stray nav items)
    while lines:
        last = lines[-1].strip()
        if not last:
            lines.pop()
            continue
        if last.startswith('[Previous ') or last.startswith('[Next '):
            lines.pop()
            continue
        if 'In this article' in last:
            lines.pop()
            continue
        if last.startswith('* ') and len(last) < 80 and '```' not in last:
            # Short bullet lines at the very end are likely breadcrumb/nav remnants
            # (Real content bullets are longer or inside code blocks)
            lines.pop()
            continue
        break
    
    result = '\n'.join(lines).strip()
    return result if result else markdown


# ====== DOCUMENT ID ======
def make_semantic_id(url: str) -> str:
    """Create a semantic document ID from URL.
    
    Example: https://docs.ravendb.net/7.2/ai-integration/vector-search/indexing-attachments-for-vector-search/
    -> Documentation_Crawl4AI/7.2/ai-integration/vector-search/indexing-attachments-for-vector-search
    """
    clean_path = url.replace("https://docs.ravendb.net/", "")
    clean_path = clean_path.strip("/")
    
    if clean_path:
        return f"{COLLECTION_NAME}/{clean_path}"
    return f"{COLLECTION_NAME}/unknown"


# ====== MAIN PIPELINE ======
async def process_and_store_urls(urls: List[str]):
    """
    Spins up the AsyncWebCrawler to render the pages, execute JavaScript (to open tabs),
    and extract pure Markdown.
    """
    print(f">> Starting Crawl4AI Headless Browser pipeline for {len(urls)} URLs...")
    print(f"   NOTE: This uses your CPU/RAM (Playwright Browser), NOT your GPU.")
    
    # Configure the browser to be headless and efficient
    browser_config = BrowserConfig(
        headless=True,
        verbose=False
    )
    
    # Configure the crawler rule-set
    # We target only the main article content area, ignoring sidebar/footer/nav
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        css_selector="article, .content-pane, main",  # Target the main documentation content
        exclude_external_links=True,
        word_count_threshold=50,  # Skip empty or error pages
        delay_before_return_html=1.5  # Wait 1.5 seconds for JS tabs to finish rendering!
    )

    try:
        store = DocumentStore(urls=[RAVENDB_URL], database=DATABASE_NAME)
        store.initialize()
        print(f"[OK] Connected to RavenDB at {RAVENDB_URL}")
    except Exception as e:
        print(f"[ERROR] Cannot connect to RavenDB: {e}")
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
                        print(f"[FAIL] Failed to crawl {url}: {result}")
                        continue
                        
                    if not result.success:
                        print(f"[WARN] Crawl failed for {url}: {result.error_message}")
                        continue
                        
                    # result.markdown contains the raw Markdown from Crawl4AI
                    raw_markdown = result.markdown
                    
                    if not raw_markdown or len(raw_markdown) < 50:
                        continue
                    
                    # === POST-PROCESSING ===
                    # 1. Remove duplicated content from multi-tab rendering
                    clean_markdown = deduplicate_markdown(raw_markdown)
                    
                    # 2. Extract metadata
                    title = extract_title_from_markdown(clean_markdown)
                    if not title:
                        title = extract_title_from_url(url)
                    version = extract_version_from_url(url)
                    category = extract_category_from_url(url)
                    sections = extract_sections_from_markdown(clean_markdown)
                    
                    doc_id = make_semantic_id(url)
                    
                    # Build the document with both clean Markdown AND structured metadata
                    doc = {
                        "Title": title,
                        "Url": url,
                        "Body": clean_markdown,
                        "Version": version,
                        "Category": category,
                        "Sections": sections,
                        "Source": "OfficialDocs_Crawl4AI",
                        "@metadata": {"@collection": COLLECTION_NAME}
                    }
                    
                    session.store(doc, key=doc_id)
                    processed_count += 1
                
                # Save batch to database
                session.save_changes()
                print(f"   [SAVED] Saved batch to RavenDB. Progress: {min(i + CONFIG_CONCURRENCY, len(urls))}/{len(urls)}")
                
            # Sleep between batches - BE POLITE to the docs server! (Rate limiting)
            await asyncio.sleep(2)
            
    print(f"\n=== DONE! Successfully processed and stored {processed_count} highly-formatted Markdown pages. ===")
    store.close()

if __name__ == "__main__":
    # For demonstration, we just use a tiny hardcoded list.
    # In a real run, you would combine this with the sitemap logic from your previous script!
    test_urls = [
        "https://docs.ravendb.net/7.2/ai-integration/vector-search/indexing-attachments-for-vector-search/",
        "https://docs.ravendb.net/7.2/ai-integration/vector-search/vector-search-using-dynamic-query/"
    ]
    
    print("WARNING: You must have Crawl4AI installed:")
    print("1. pip install crawl4ai")
    print("2. playwright install")
    print("-" * 50)
    
    asyncio.run(process_and_store_urls(test_urls))

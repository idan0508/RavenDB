"""
Documentation Collection Quality Comparison Test
=================================================
Compares the quality of Documentation vs Documentation_Crawl4AI collections
to determine which scraping method produces better results for RAG.

Usage:
    python tests/compare_documentation_collections.py
    python tests/compare_documentation_collections.py --detailed

Requirements:
    pip install ravendb
"""

import sys
import argparse
from ravendb import DocumentStore
from collections import Counter

# Windows PowerShell compatibility - disable emojis
WINDOWS_POWERSHELL = sys.platform == 'win32'

# Symbols that work in PowerShell
CHECK = '[OK]' if WINDOWS_POWERSHELL else '✓'
CROSS = '[X]' if WINDOWS_POWERSHELL else '✗'
WARN = '[!]' if WINDOWS_POWERSHELL else '⚠️'
TROPHY = '[WINNER]' if WINDOWS_POWERSHELL else '🏆'
HANDSHAKE = '[TIE]' if WINDOWS_POWERSHELL else '🤝'
DOCUMENT = '[DOC]' if WINDOWS_POWERSHELL else '📄'

# Configuration
RAVENDB_URL = "http://localhost:8080"
DATABASE_NAME = "HelpdeskDB"

# Noise indicators (common scraping artifacts)
NOISE_PATTERNS = [
    "Previous",
    "Next",
    "In this article",
    "C#PythonNode.js",
    "Table of Contents",
    "Skip to content",
    "Cookie",
]


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_section(text):
    """Print a formatted section."""
    print(f"\n{text}")
    print("-" * 70)


def test_basic_statistics(session):
    """Test 1: Basic Statistics - Document counts and averages."""
    print_header("TEST 1: Basic Statistics")
    
    # Count documents - FIXED: Use object_type=dict for dynamic documents
    try:
        doc_count = session.query(object_type=dict, collection_name="Documentation").count()
        print(f"{CHECK} Documentation collection:          {doc_count:>6} documents")
    except Exception as e:
        print(f"{CROSS} Documentation collection:          ERROR - {e}")
        doc_count = 0
    
    try:
        crawl_count = session.query(object_type=dict, collection_name="Documentation_Crawl4AI").count()
        print(f"{CHECK} Documentation_Crawl4AI collection: {crawl_count:>6} documents")
    except Exception as e:
        print(f"{CROSS} Documentation_Crawl4AI collection: ERROR - {e}")
        crawl_count = 0
    
    if doc_count == 0 and crawl_count == 0:
        print(f"\n{WARN} No collections found! Have you run the collection scripts?")
        return None
    
    # Calculate coverage difference
    if doc_count > 0 and crawl_count > 0:
        diff_pct = abs(doc_count - crawl_count) / max(doc_count, crawl_count) * 100
        print(f"\nCoverage difference: {diff_pct:.1f}%")
        
        if doc_count > crawl_count * 1.2:
            print("→ Documentation has significantly better coverage (+20%)")
        elif crawl_count > doc_count * 1.2:
            print("→ Documentation_Crawl4AI has significantly better coverage (+20%)")
        else:
            print("→ Similar coverage")
    
    return {"doc_count": doc_count, "crawl_count": crawl_count}


def test_content_quality(session, sample_size=10):
    """Test 2: Content Quality - Average lengths and completeness."""
    print_header("TEST 2: Content Quality")
    
    # Sample from Documentation - FIXED: Use object_type=dict and .get() for dict access
    print_section("Documentation Collection Sample")
    try:
        doc_sample = list(session.query(object_type=dict, collection_name="Documentation").take(sample_size))
        
        if doc_sample:
            avg_body = sum(len(d.get("Body", "") or "") for d in doc_sample) / len(doc_sample)
            avg_code = sum(len(d.get("CodeExamples", []) or []) for d in doc_sample) / len(doc_sample)
            avg_sections = sum(len(d.get("Sections", []) or []) for d in doc_sample) / len(doc_sample)
            
            print(f"Average Body Length:     {avg_body:>8.0f} chars")
            print(f"Average Code Examples:   {avg_code:>8.1f} blocks")
            print(f"Average Sections:        {avg_sections:>8.1f} sections")
            
            # Check for empty bodies
            empty_bodies = sum(1 for d in doc_sample if not d.get("Body") or len(d.get("Body", "")) < 100)
            if empty_bodies > 0:
                print(f"{WARN} Empty/short bodies:    {empty_bodies}/{len(doc_sample)} documents")
        else:
            print(f"{WARN} No documents found in sample")
            avg_body = avg_code = avg_sections = 0
    except Exception as e:
        print(f"{CROSS} Error sampling Documentation: {e}")
        avg_body = avg_code = avg_sections = 0
    
    # Sample from Documentation_Crawl4AI - FIXED: Use object_type=dict and .get() for dict access
    print_section("Documentation_Crawl4AI Collection Sample")
    try:
        crawl_sample = list(session.query(object_type=dict, collection_name="Documentation_Crawl4AI").take(sample_size))
        
        if crawl_sample:
            crawl_avg_body = sum(len(d.get("Body", "") or "") for d in crawl_sample) / len(crawl_sample)
            crawl_avg_code = sum(len(d.get("CodeExamples", []) or []) for d in crawl_sample) / len(crawl_sample)
            crawl_avg_sections = sum(len(d.get("Sections", []) or []) for d in crawl_sample) / len(crawl_sample)
            
            print(f"Average Body Length:     {crawl_avg_body:>8.0f} chars")
            print(f"Average Code Examples:   {crawl_avg_code:>8.1f} blocks")
            print(f"Average Sections:        {crawl_avg_sections:>8.1f} sections")
            
            # Check for empty bodies
            empty_bodies = sum(1 for d in crawl_sample if not d.get("Body") or len(d.get("Body", "")) < 100)
            if empty_bodies > 0:
                print(f"{WARN} Empty/short bodies:    {empty_bodies}/{len(crawl_sample)} documents")
        else:
            print(f"{WARN} No documents found in sample")
            crawl_avg_body = crawl_avg_code = crawl_avg_sections = 0
    except Exception as e:
        print(f"{CROSS} Error sampling Documentation_Crawl4AI: {e}")
        crawl_avg_body = crawl_avg_code = crawl_avg_sections = 0
    
    # Comparison
    print_section("Quality Comparison")
    if avg_body > 0 and crawl_avg_body > 0:
        if avg_body > crawl_avg_body * 1.2:
            print("→ Documentation has richer content (+20%)")
        elif crawl_avg_body > avg_body * 1.2:
            print("→ Documentation_Crawl4AI has richer content (+20%)")
        else:
            print("→ Similar content richness")
    
    return {
        "doc_avg_body": avg_body,
        "crawl_avg_body": crawl_avg_body,
        "doc_avg_code": avg_code,
        "crawl_avg_code": crawl_avg_code,
    }


def test_noise_detection(session, sample_size=50):
    """Test 3: Noise Detection - Check for scraping artifacts."""
    print_header("TEST 3: Noise Detection")
    
    results = {}
    
    for collection_name in ["Documentation", "Documentation_Crawl4AI"]:
        print_section(f"{collection_name} Collection")
        
        try:
            # Sample documents - FIXED: Use object_type=dict
            sample = list(session.query(object_type=dict, collection_name=collection_name).take(sample_size))
            
            if not sample:
                print(f"{WARN} No documents found")
                continue
            
            # Count noise patterns - FIXED: Use .get() for dict access
            noise_counts = Counter()
            docs_with_noise = 0
            
            for doc in sample:
                body = doc.get("Body", "") or ""
                has_noise = False
                
                for pattern in NOISE_PATTERNS:
                    if pattern in body:
                        noise_counts[pattern] += 1
                        has_noise = True
                
                if has_noise:
                    docs_with_noise += 1
            
            # Report results
            noise_pct = (docs_with_noise / len(sample)) * 100
            print(f"Documents with noise: {docs_with_noise}/{len(sample)} ({noise_pct:.1f}%)")
            
            if noise_counts:
                print("\nNoise patterns found:")
                for pattern, count in noise_counts.most_common(5):
                    print(f"  - '{pattern}': {count} occurrences")
            else:
                print(f"{CHECK} No noise patterns detected!")
            
            results[collection_name] = {
                "noise_pct": noise_pct,
                "noise_counts": dict(noise_counts)
            }
            
        except Exception as e:
            print(f"{CROSS} Error checking {collection_name}: {e}")
            # FIXED: Add None check - store None result to prevent KeyError later
            results[collection_name] = None
    
    # Comparison - FIXED: Add None checks before accessing nested dicts
    if len(results) == 2:
        print_section("Noise Comparison")
        doc_result = results.get("Documentation")
        crawl_result = results.get("Documentation_Crawl4AI")
        
        # Only compare if both results are valid (not None)
        if doc_result is not None and crawl_result is not None:
            doc_noise = doc_result.get("noise_pct", 0)
            crawl_noise = crawl_result.get("noise_pct", 0)
            
            if doc_noise < crawl_noise * 0.8:
                print("→ Documentation has cleaner content (-20% noise)")
            elif crawl_noise < doc_noise * 0.8:
                print("→ Documentation_Crawl4AI has cleaner content (-20% noise)")
            else:
                print("→ Similar noise levels")
        else:
            print(f"{WARN} Cannot compare - one or both collections had errors")
    
    return results


def test_coverage_overlap(session, sample_size=100):
    """Test 4: Coverage Overlap - Check which URLs are unique to each collection."""
    print_header("TEST 4: Coverage Overlap")
    
    try:
        # Get URLs from both collections - FIXED: Fetch full documents (no .select() in Python client)
        doc_urls = set()
        crawl_urls = set()
        
        print("Fetching URLs from Documentation...")
        docs = list(session.query(object_type=dict, collection_name="Documentation").take(sample_size))
        # FIXED: Access dict keys safely from full documents
        doc_urls = {d.get("Url") for d in docs if d.get("Url")}
        
        print("Fetching URLs from Documentation_Crawl4AI...")
        crawls = list(session.query(object_type=dict, collection_name="Documentation_Crawl4AI").take(sample_size))
        # FIXED: Access dict keys safely from full documents
        crawl_urls = {d.get("Url") for d in crawls if d.get("Url")}
        
        # Calculate overlap
        common = doc_urls & crawl_urls
        doc_only = doc_urls - crawl_urls
        crawl_only = crawl_urls - doc_urls
        
        print(f"\nURLs in both collections:     {len(common):>6}")
        print(f"URLs only in Documentation:   {len(doc_only):>6}")
        print(f"URLs only in Crawl4AI:        {len(crawl_only):>6}")
        
        if doc_only:
            print(f"\nExample URLs only in Documentation (first 3):")
            for url in list(doc_only)[:3]:
                print(f"  - {url}")
        
        if crawl_only:
            print(f"\nExample URLs only in Crawl4AI (first 3):")
            for url in list(crawl_only)[:3]:
                print(f"  - {url}")
        
        # Overlap percentage
        if doc_urls and crawl_urls:
            overlap_pct = (len(common) / max(len(doc_urls), len(crawl_urls))) * 100
            print(f"\nOverlap: {overlap_pct:.1f}%")
        
        return {
            "common": len(common),
            "doc_only": len(doc_only),
            "crawl_only": len(crawl_only)
        }
        
    except Exception as e:
        print(f"{CROSS} Error checking coverage: {e}")
        return None


def test_detailed_inspection(session):
    """Test 5: Detailed Inspection - Show sample documents for manual review."""
    print_header("TEST 5: Detailed Document Inspection")
    
    print(f"\n{DOCUMENT} Sample from Documentation Collection:")
    print("-" * 70)
    
    try:
        # FIXED: Use object_type=dict
        doc = session.query(object_type=dict, collection_name="Documentation").first()
        if doc:
            # FIXED: Access dict keys safely with .get()
            print(f"Title:    {doc.get('Title', 'N/A')}")
            print(f"URL:      {doc.get('Url', 'N/A')}")
            print(f"Version:  {doc.get('Version', 'N/A')}")
            print(f"Category: {doc.get('Category', 'N/A')}")
            print(f"Body:     {doc.get('Body', '')[:300]}...")
            print(f"Sections: {doc.get('Sections', [])[:5]}")
            print(f"Code:     {len(doc.get('CodeExamples', []))} examples")
        else:
            print(f"{WARN} No documents found")
    except Exception as e:
        print(f"{CROSS} Error: {e}")
    
    print(f"\n{DOCUMENT} Sample from Documentation_Crawl4AI Collection:")
    print("-" * 70)
    
    try:
        # FIXED: Use object_type=dict
        doc = session.query(object_type=dict, collection_name="Documentation_Crawl4AI").first()
        if doc:
            # FIXED: Access dict keys safely with .get()
            print(f"Title:    {doc.get('Title', 'N/A')}")
            print(f"URL:      {doc.get('Url', 'N/A')}")
            print(f"Version:  {doc.get('Version', 'N/A')}")
            print(f"Category: {doc.get('Category', 'N/A')}")
            print(f"Body:     {doc.get('Body', '')[:300]}...")
            print(f"Sections: {doc.get('Sections', [])[:5]}")
            print(f"Code:     {len(doc.get('CodeExamples', []))} examples")
        else:
            print(f"{WARN} No documents found")
    except Exception as e:
        print(f"{CROSS} Error: {e}")


def generate_final_recommendation(results):
    """Generate final recommendation based on all test results."""
    print_header("FINAL RECOMMENDATION")
    
    scores = {"Documentation": 0, "Documentation_Crawl4AI": 0}
    
    # Score based on coverage - FIXED: Add None checks
    basic_results = results.get("basic")
    if basic_results is not None:
        doc_count = basic_results.get("doc_count", 0)
        crawl_count = basic_results.get("crawl_count", 0)
        
        if doc_count > crawl_count * 1.2:
            scores["Documentation"] += 2
            print(f"{CHECK} Documentation wins on coverage (+2 points)")
        elif crawl_count > doc_count * 1.2:
            scores["Documentation_Crawl4AI"] += 2
            print(f"{CHECK} Documentation_Crawl4AI wins on coverage (+2 points)")
        else:
            print("-> Tie on coverage")
    
    # Score based on content quality - FIXED: Add None checks
    quality_results = results.get("quality")
    if quality_results is not None:
        doc_body = quality_results.get("doc_avg_body", 0)
        crawl_body = quality_results.get("crawl_avg_body", 0)
        
        if doc_body > crawl_body * 1.2:
            scores["Documentation"] += 2
            print(f"{CHECK} Documentation wins on content richness (+2 points)")
        elif crawl_body > doc_body * 1.2:
            scores["Documentation_Crawl4AI"] += 2
            print(f"{CHECK} Documentation_Crawl4AI wins on content richness (+2 points)")
        else:
            print("-> Tie on content richness")
    
    # Score based on noise - FIXED: Add None checks for nested dicts
    noise_results = results.get("noise")
    if noise_results is not None:
        doc_noise_result = noise_results.get("Documentation")
        crawl_noise_result = noise_results.get("Documentation_Crawl4AI")
        
        # Only score if both collections have valid results
        if doc_noise_result is not None and crawl_noise_result is not None:
            doc_noise = doc_noise_result.get("noise_pct", 100)
            crawl_noise = crawl_noise_result.get("noise_pct", 100)
            
            if doc_noise < crawl_noise * 0.8:
                scores["Documentation"] += 1
                print(f"{CHECK} Documentation wins on cleanliness (+1 point)")
            elif crawl_noise < doc_noise * 0.8:
                scores["Documentation_Crawl4AI"] += 1
                print(f"{CHECK} Documentation_Crawl4AI wins on cleanliness (+1 point)")
            else:
                print("-> Tie on cleanliness")
        else:
            print(f"{WARN} Cannot score cleanliness - one or both collections had errors")
    
    # Final verdict
    print("\n" + "=" * 70)
    print(f"Final Scores:")
    print(f"  Documentation:          {scores['Documentation']} points")
    print(f"  Documentation_Crawl4AI: {scores['Documentation_Crawl4AI']} points")
    print("=" * 70)
    
    if scores["Documentation"] > scores["Documentation_Crawl4AI"]:
        print(f"\n{TROPHY} WINNER: Documentation (Sitemap-based collection)")
        print("\nRecommended Action:")
        print("  1. Keep the 'Documentation' collection")
        print("  2. Delete 'Documentation_Crawl4AI' to save space")
        print("  3. Use collect_docs_sitemap.py for future updates")
    elif scores["Documentation_Crawl4AI"] > scores["Documentation"]:
        print(f"\n{TROPHY} WINNER: Documentation_Crawl4AI (Crawl4AI-based collection)")
        print("\nRecommended Action:")
        print("  1. Rename 'Documentation_Crawl4AI' to 'Documentation'")
        print("  2. Delete old 'Documentation' collection")
        print("  3. Use collect_docs_crawl4ai.py for future updates")
    else:
        print(f"\n{HANDSHAKE} TIE: Both collections have similar quality")
        print("\nRecommended Action:")
        print("  1. Run TEST 5 (RAG Retrieval Test) manually")
        print("  2. Create two AI agents and test with real questions")
        print("  3. Keep the collection that gives better answers")
        print("\nNote: Sitemap approach is faster (5-10x), so prefer it if quality is equal")


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="Compare Documentation collections")
    parser.add_argument("--detailed", action="store_true", 
                       help="Show detailed document inspection")
    parser.add_argument("--ravendb-url", default=RAVENDB_URL,
                       help=f"RavenDB URL (default: {RAVENDB_URL})")
    parser.add_argument("--database", default=DATABASE_NAME,
                       help=f"Database name (default: {DATABASE_NAME})")
    args = parser.parse_args()
    
    print("=" * 70)
    print("  Documentation Collection Quality Comparison")
    print("=" * 70)
    print(f"RavenDB:  {args.ravendb_url}")
    print(f"Database: {args.database}")
    
    # FIXED: Initialize store as None for proper cleanup
    store = None
    
    try:
        # Connect to RavenDB
        store = DocumentStore(urls=[args.ravendb_url], database=args.database)
        store.initialize()
        print(f"{CHECK} Connected to RavenDB")
        
        # Run tests
        results = {}
        
        with store.open_session() as session:
            # Test 1: Basic Statistics
            results["basic"] = test_basic_statistics(session)
            
            # Test 2: Content Quality
            results["quality"] = test_content_quality(session)
            
            # Test 3: Noise Detection
            results["noise"] = test_noise_detection(session)
            
            # Test 4: Coverage Overlap
            results["coverage"] = test_coverage_overlap(session)
            
            # Test 5: Detailed Inspection (optional)
            if args.detailed:
                test_detailed_inspection(session)
        
        # Generate recommendation
        generate_final_recommendation(results)
        
        print("\n" + "=" * 70)
        print("  Next Steps")
        print("=" * 70)
        print("\n1. Review the results above")
        print("2. If you want more detail, run with --detailed flag")
        print("3. For the ultimate test, create two AI agents and compare answers")
        print("4. See docs/DOCUMENTATION_QUALITY_COMPARISON.md for full guide")
        print()
        
    except Exception as e:
        print(f"\n{CROSS} Failed to connect to RavenDB: {e}")
        print("\nMake sure:")
        print("  1. RavenDB is running")
        print("  2. Database exists")
        print("  3. URL is correct")
        sys.exit(1)
    finally:
        # FIXED: Always close store if it was initialized
        if store is not None:
            store.close()


if __name__ == "__main__":
    main()

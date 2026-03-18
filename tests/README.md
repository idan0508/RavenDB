# Tests Directory

This directory contains test scripts for the RavenDB AI Helpdesk project.

## Available Tests

### 1. Documentation Collection Quality Comparison

**File:** `compare_documentation_collections.py`

**Purpose:** Compare the quality of different documentation collection methods (sitemap vs Crawl4AI) to determine which produces better results for RAG.

**Usage:**
```bash
# Basic comparison
python tests/compare_documentation_collections.py

# Detailed inspection with sample documents
python tests/compare_documentation_collections.py --detailed

# Custom RavenDB connection
python tests/compare_documentation_collections.py --ravendb-url http://localhost:8080 --database HelpdeskDB
```

**What it tests:**
1. **Basic Statistics** - Document counts and coverage
2. **Content Quality** - Average body length, code examples, sections
3. **Noise Detection** - Scraping artifacts and navigation text
4. **Coverage Overlap** - Which URLs are in each collection
5. **Detailed Inspection** - Sample documents for manual review (with --detailed flag)

**Output:**
- Comparison scores for each collection
- Final recommendation on which collection to keep
- Actionable next steps

**Requirements:**
```bash
pip install ravendb
```

---

## Running Tests

### Prerequisites

1. RavenDB must be running locally
2. Database `HelpdeskDB` must exist
3. At least one of these collections must exist:
   - `Documentation` (from sitemap collection)
   - `Documentation_Crawl4AI` (from Crawl4AI collection)

### Quick Start

```bash
# Navigate to project root
cd RavenDB

# Run the comparison test
python tests/compare_documentation_collections.py
```

### Expected Output

```
======================================================================
  Documentation Collection Quality Comparison
======================================================================
RavenDB:  http://localhost:8080
Database: HelpdeskDB
✓ Connected to RavenDB

======================================================================
  TEST 1: Basic Statistics
======================================================================
✓ Documentation collection:             523 documents
✓ Documentation_Crawl4AI collection:    187 documents

Coverage difference: 64.3%
→ Documentation has significantly better coverage (+20%)

[... more test results ...]

======================================================================
  FINAL RECOMMENDATION
======================================================================
Final Scores:
  Documentation:          5 points
  Documentation_Crawl4AI: 1 points
======================================================================

🏆 WINNER: Documentation (Sitemap-based collection)

Recommended Action:
  1. Keep the 'Documentation' collection
  2. Delete 'Documentation_Crawl4AI' to save space
  3. Use collect_docs_sitemap.py for future updates
```

---

## Future Tests

Additional tests to be added:

- [ ] RAG retrieval accuracy test (automated question answering)
- [ ] Embedding quality test (vector similarity metrics)
- [ ] GitHub Discussions quality test
- [ ] Google Groups collection test
- [ ] End-to-end AI agent test

---

## Contributing

When adding new tests:

1. Create a descriptive filename: `test_<feature>_<aspect>.py`
2. Add docstrings explaining what the test does
3. Include usage examples in this README
4. Make tests runnable from project root
5. Handle errors gracefully with helpful messages

---

*Last Updated: March 18, 2026*

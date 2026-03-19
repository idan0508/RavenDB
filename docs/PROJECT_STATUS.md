# RavenDB AI Helpdesk - Project Status

**Team:** Ron Blanky, Idan Dahan
**Last Updated:** 2026-03-18

---

## Project Goal

Build a production-ready AI Helpdesk pipeline for RavenDB support:
- Collect high-quality knowledge from Discussions, Groups, and Docs.
- Store in RavenDB with stable IDs and metadata.
- Generate embeddings for semantic retrieval.
- Answer users through an AI Agent and Telegram entry point.

---

## Latest Milestone (March 18, 2026)

### Commit audited
- `a027962508c7f211bad96df243a4e83c52205b74`
- Scope: hardening `collect_docs_sitemap.py`, adding tests, improving RAG ingestion quality.

### What was completed

| Item | Status | Why it matters |
|------|--------|----------------|
| Sitemap scraper upgraded | Completed | Better coverage and extraction quality |
| Collection prefix bug fixed | Completed | Correct RavenDB collection routing |
| Incremental skip-existing flow | Completed | Fast reruns and safer recovery |
| Failure reasons + failed URL export | Completed | Real observability and retry path |
| RAG metadata enrichment | Completed | Better filtering, change tracking, and embedding workflow |
| Token counting with `tiktoken` | Completed | Safer embedding limits and cost awareness |
| Extraction tests added | Completed | Prevents regression on glossary/reference pages |
| Workspace Python import issues fixed | Completed | Pylance and runtime aligned with `.venv` |

---

## Technical Challenges Solved Today

### 1. Architecture and performance misconceptions
- Clarified that this workload is I/O bound; Python + concurrency is the right strategy.
- Kept direct-to-RavenDB ETL instead of staging files locally.

### 2. RavenDB collection behavior
- Root cause: document ID prefix controls collection assignment.
- Fix: semantic IDs now use dynamic collection prefix.

### 3. False negatives in scraping
- Root cause: extractor was too strict for short or glossary-style pages.
- Fix: expanded supported tags and improved fallback text extraction.

### 4. Reporting and reliability issues
- Fixed inaccurate final totals by tracking persistent `total_saved`.
- Added HTTP retries and stronger error categorization.

### 5. RAG metadata and compatibility
- Added `SearchableContent`, `TokenCount`, `ContentHash`, `ScrapedAt`, `ProgrammingLanguage`, `WordCount`.
- Standardized UTC handling with timezone-aware timestamps.

### 6. Environment diagnostics
- Resolved missing import diagnostics by installing required packages in workspace `.venv`.

---

## Current Data Pipeline Status

| Source | Status | Notes |
|--------|--------|-------|
| GitHub Discussions | Completed | Ingested into RavenDB |
| Google Groups | In progress | Collection/import flow exists |
| Documentation (sitemap) | In progress | Main scraper fixed and ready for rerun |

---

## What To Run Now

1. Re-run the modified sitemap script once against the same collection.
2. Do not delete the collection before this rerun.
3. Review final counts and `scripts/failed_urls.txt` after run.

Recommended command:

```powershell
.\.venv\Scripts\python.exe .\scripts\collect_docs_sitemap.py --all-versions --workers 20 --collection "Documentation_Sitemaps"
```

---

## Rebuild Decision Rule

Keep existing collection and rerun first.
Only do full delete/rebuild if one of these is true:
- Failure count remains high after rerun and root cause is unresolved.
- You need a completely clean baseline for final demo.

---

## Presentation-Ready Narrative

What we built is not just a scraper.
It is an ETL pipeline with:
- deterministic IDs,
- incremental ingestion,
- extraction quality controls,
- runtime observability,
- embedding-oriented metadata,
- regression tests.

This is the strongest final-project story: engineering decisions, measurable fixes, and production behavior.

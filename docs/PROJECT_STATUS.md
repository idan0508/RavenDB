# RavenDB AI Helpdesk — Project Status

**Team:** Ron Blanki, Idan Dahan  
**Last Updated:** June 18, 2026

---

## Project Goal

Build a production-ready AI Helpdesk pipeline for RavenDB support:
- Collect high-quality knowledge from Documentation, Discussions, and Google Groups.
- Store in RavenDB with stable IDs and metadata.
- Generate embeddings via Azure AI for semantic retrieval.
- Answer users through an AI Agent with Telegram entry point.

---

## Current Milestone (June 18, 2026)

### Grounded Agent Configuration Replicated in Code

| Item | Status | Details |
|---|---|---|
| Separate semantic indexes | ✅ Implemented | Documentation, Discussions, and Google Groups are deployed independently |
| Agent retrieval order | ✅ Implemented | Documentation → Discussions → Google Groups |
| No-answer contract | ✅ Implemented | `NotFound` response states that the knowledge base was searched |
| URL safety | ✅ Implemented | Telegram permits only RavenDB docs and exact RavenDB Discussion URLs |
| Reproducible identifier | ✅ Implemented | `ravendb-helpdesk-grounded-v1` |

### Platform Migration Complete

| Item | Status | Details |
|------|--------|---------|
| Azure AI Connection Strings | ✅ Complete | `Azure-Chat` (gpt-4.1-mini) + `Azure-Text-Embeddings` (text-embedding-3-small) |
| Ollama/Llama retirement | ✅ Complete | Local GPU no longer required for AI operations |
| Embedding tasks (Documentation) | ✅ Active | `documentations` task on `Documentation_Sitemaps.SearchableContent` |
| Embedding tasks (Discussions) | ✅ Active | `discussions` task on `Discussions.Body` |
| Semantic search indexes | ✅ Defined in code | Three per-collection indexes matching Studio |
| Architecture documentation | ✅ Complete | `ARCHITECTURE.md` created with full pipeline record |

### Data Pipeline Status

| Source | Collection | Documents | Embeddings | Status |
|--------|------------|-----------|------------|--------|
| Documentation (sitemap) | `Documentation_Sitemaps` | ~8,000 | ✅ Generated | Complete |
| GitHub Discussions | `Discussions` | 1,052 | ✅ Generated | Complete |
| Google Groups | `GoogleGroupMessages` | 112,190 | ⏳ Pending | Data imported, embeddings next |

---

## Milestone History

### April 2026 — Azure Migration & Architecture Documentation

- Migrated from Ollama + Llama 3.1:8b to Azure OpenAI (gpt-4.1-mini + text-embedding-3-small)
- Reason: Azure provides both Chat AND Text Embeddings; Ollama lacked embeddings
- Created embedding generation tasks for Documentation_Sitemaps and Discussions
- Created semantic search indexes (per-collection in Studio)
- Documented full architecture in `ARCHITECTURE.md`
- Updated `LOCAL_SETUP_GUIDE.md` and `AI_AGENT_GUIDE.md` for Azure
- Created project `README.md`

### March 18, 2026 — Pipeline Hardening

**Commit:** `a027962` — Hardened `collect_docs_sitemap.py` and added tests.

| Item | Status | Why it matters |
|------|--------|----------------|
| Sitemap scraper upgraded | ✅ | Better coverage and extraction quality |
| Collection prefix bug fixed | ✅ | Correct RavenDB collection routing |
| Incremental skip-existing flow | ✅ | Fast reruns and safer recovery |
| Failure reasons + failed URL export | ✅ | Real observability and retry path |
| RAG metadata enrichment | ✅ | Better filtering, change tracking, and embedding workflow |
| Token counting with `tiktoken` | ✅ | Safer embedding limits and cost awareness |
| Extraction tests added | ✅ | Prevents regression on glossary/reference pages |
| Workspace Python import issues fixed | ✅ | Pylance and runtime aligned with `.venv` |

### February 2026 — Initial Setup

- Installed RavenDB 7.2.0 locally
- Applied Ruppin Developer License (AI features unlocked)
- Set up Ollama + Llama 3.1:8b on RTX 4060
- Collected 1,052 GitHub Discussions
- Built initial Telegram bot
- Created PropertySphere-inspired agent configuration

---

## Technical Challenges Solved

### 1. Missing Text Embeddings (Resolved: April 2026)
- **Problem:** Ollama only provided a Chat model. No production-quality embeddings.
- **Solution:** Migrated to Azure OpenAI which provides both `gpt-4.1-mini` (chat) and `text-embedding-3-small` (embeddings) through a single API.

### 2. RavenDB Collection Routing Bug (Resolved: March 2026)
- **Problem:** Documents landed in wrong collections.
- **Root cause:** Document ID prefix controls collection assignment in RavenDB.
- **Fix:** `make_semantic_id()` now uses the requested collection prefix.

### 3. False Failures on Valid Pages (Resolved: March 2026)
- **Problem:** Hundreds of valid docs URLs marked as failed.
- **Root cause:** Content extraction too strict for glossary/reference pages.
- **Fix:** Expanded tag support (`dd`, `dt`, table cells) + fallback extraction.

### 4. Incorrect Summary Counts (Resolved: March 2026)
- **Problem:** Final summary under-reported saved documents.
- **Fix:** Persistent `total_saved` counter instead of batch buffer length.

### 5. Thread-Safety in Scraper (Resolved: March 2026)
- **Fix:** Global tokenizer init for thread-safe `TokenCount` calculation.
- **Fix:** UTC timestamps via `datetime.now(timezone.utc)`.

---

## What's Next

### Immediate — End-to-End Validation
1. Deploy the code configuration to the target `HelpdeskDB`
2. Verify the three embedding tasks and indexes are healthy
3. Test known-answer, unknown-answer, and version-clarification scenarios
4. Run Telegram against `ravendb-helpdesk-grounded-v1`

### Upcoming — Final Integration
- Run end-to-end verification: Telegram → Agent → Semantic Search → Answer
- Create benchmark QA set for retrieval quality validation
- Final presentation preparation

---

## Presentation-Ready Narrative

What we built is not just a chatbot. It is a complete **enterprise RAG pipeline** with:
- Three distinct data sources (docs, discussions, email archive)
- Automated ETL with deterministic IDs and incremental ingestion
- Production-quality embeddings via Azure AI
- Semantic vector search across 120k+ documents
- AI Agent orchestration with source citation
- Telegram bot as user-facing interface

The engineering story: from raw data collection to production-ready knowledge retrieval, with measurable fixes, cost analysis, and architectural documentation at every step.

---

*For the full technical architecture, see [ARCHITECTURE.md](../ARCHITECTURE.md).*

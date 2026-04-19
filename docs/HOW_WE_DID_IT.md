# How We Built It: End-to-End Technical Path

This document is the final, end-to-end technical story for the project.
It explains what we changed, why we changed it, how we validated it, and what to run next.

For the full system architecture diagram, data schemas, and cost analysis, see [ARCHITECTURE.md](../ARCHITECTURE.md).

---

## April 2026 — Azure AI Migration & Documentation

### What changed

We migrated the entire AI backend from **Ollama + Llama 3.1:8b** (local GPU) to **Azure OpenAI** (cloud API).

### Why we changed this

The fundamental blocker was **text embeddings**. Our RAG pipeline requires two AI capabilities:
1. **Chat** — to generate human-readable answers from retrieved documents.
2. **Text Embeddings** — to convert text into vectors for semantic search.

Ollama provided only Chat. Its available embedding models (like `nomic-embed-text`) lacked the quality and integration we needed for production semantic search. Azure OpenAI provides both capabilities through a single, consistent API:

| Capability | Old (Ollama) | New (Azure) |
|---|---|---|
| Chat | `llama3.1:8b` (local, 8GB VRAM) | `gpt-4.1-mini` (cloud) |
| Embeddings | ❌ Not available | `text-embedding-3-small` (cloud) |
| Context window | 8K (VRAM-limited) | 128K+ (no local constraint) |
| Tool-calling | Fragile (state machine prompts) | Reliable (native support) |

### What we configured

1. **Connection Strings** in RavenDB Studio:
   - `Azure-Chat` — Chat type, `gpt-4.1-mini`, Azure OpenAI connector
   - `Azure-Text-Embeddings` — Text Embeddings type, `text-embedding-3-small`

2. **Embedding Generation Tasks:**
   - `documentations` — embeds `SearchableContent` from `Documentation_Sitemaps` using MarkDownSplitParagraphs chunking
   - `discussions` — embeds `Body` from `Discussions` using PlainTextSplit chunking

3. **Semantic Search Indexes:**
   - `KnowledgeBase/SemanticSearch/Documentations` — vectorizes documentation
   - `KnowledgeBase/SemanticSearch/Discussions` — vectorizes discussions

4. **Documentation overhaul:**
   - Created `ARCHITECTURE.md` — permanent record of the full RAG pipeline
   - Created `README.md` — project-level overview
   - Updated `LOCAL_SETUP_GUIDE.md` — Azure AI setup instructions
   - Updated `AI_AGENT_GUIDE.md` — removed Ollama-specific content, preserved prompt engineering
   - Updated `PROJECT_STATUS.md` — current milestone status
   - Updated `SETTING_UP_VECTORS.md` — Azure embedding task configuration
   - Created `reference_projects/PURPOSE.md` — explainer for PropertySphere

### Impact

- The RAG pipeline is now fully operational with real embeddings.
- Semantic search works across Documentation and Discussions.
- The system prompt is simpler (Azure models handle tool-calling natively).
- Total estimated AI cost: < $2.00 for all embeddings across all collections.
- All documentation is current and internally consistent.

---

## March 18–19, 2026 — Pipeline Hardening

Summary: we hardened the sitemap scraper and ingestion pipeline to reduce false negatives, make reruns safe and incremental, and improve embedding hygiene.

### Why we changed this
  - Hundreds of valid reference/glossary pages were being marked as failed due to brittle extraction rules.
  - Some documents landed in the wrong RavenDB collection because IDs forced routing.
  - Editor diagnostics (Pylance) diverged from the runtime environment, slowing development.
  - Existing vectors showed contamination from prior malformed embeddings.

- **How we fixed it (high level):**
### How we fixed it
  - Extended extraction to handle `dd`/`dt`, table cells, and fallback plain-text extraction; improved normalization to avoid short-content false negatives.
  - Parameterized `make_semantic_id()` so generated IDs use the requested collection prefix and avoid misrouting.
  - Implemented per-thread `requests.Session` reuse and per-thread tokenizer initialization for `tiktoken` to improve throughput and correctness.
  - Added incremental mode to skip existing documents, a persistent `total_saved` counter, and failure-reason logging (exported to `scripts/failed_urls.txt`).
  - Installed required packages into the workspace `.venv` and added unit tests for extraction helpers to prevent regressions.

- **Impact:**
### Impact
  - Reruns are safe (no duplicates) and more likely to recover valid pages.
  - Clearer failure reasons let you triage problem URLs quickly.
  - Embedding regeneration is straightforward after cleaning contaminated vectors.

Refer to the "March 18 — Major Implementation" section below for exact file-level changes and commands to run.


## Mission and Constraints

Goal: build a production-ready RavenDB knowledge pipeline for a Helpdesk AI agent.

Non-negotiables:
- Full documentation coverage across versions.
- Fast collection runs on local hardware.
- Reliable reruns without duplicate documents.
- Metadata rich enough for high-quality RAG and embeddings.

---

## Key Architecture Decisions

### Direct-to-DB over local file staging

Decision:
- Scrape and write directly to RavenDB.

Why:
- Fewer moving parts.
- No unnecessary disk I/O.
- Easier reruns because document IDs are deterministic.

### Keep Python, optimize concurrency

Decision:
- Keep the scraper in Python with `ThreadPoolExecutor`.

Why:
- This workload is I/O bound (network + remote server latency), not CPU bound.
- More threads improve throughput without a language rewrite.

---

## March 18 — Major Implementation

Primary script:
- `scripts/collect_docs_sitemap.py`

What was added or improved:
- Sitemap-first URL discovery for complete coverage.
- Better extraction (`_normalize_content_lines`, `_extract_content_text`) for glossary and short reference pages.
- Per-thread HTTP session reuse with retries.
- Incremental mode: skip existing docs already in RavenDB.
- Robust batch writing with error handling.
- Rich RAG metadata:
  - `SearchableContent`
  - `WordCount`
  - `ProgrammingLanguage`
  - `ScrapedAt`
  - `ContentHash`
  - `TokenCount` (from `tiktoken`)
- Failure observability:
  - reason buckets in summary
  - failed URLs persisted to `scripts/failed_urls.txt`

Validation added:
- `tests/test_collect_docs_sitemap.py`
- `tests/compare_documentation_collections.py`

---

## Production Bugs We Solved

### RavenDB collection routing bug

Symptom:
- Documents were landing in the wrong collection.

Root cause:
- In RavenDB, the document ID prefix determines collection routing.
- Metadata collection name does not override a mismatched ID prefix.

Fix:
- `make_semantic_id(url, collection_prefix)` now uses the requested collection prefix.

### False failures on valid pages

Symptom:
- Hundreds of valid URLs were marked failed.

Root cause:
- Content extraction was too strict for glossary/reference markup.

Fix:
- Added extraction support for `dd`, `dt`, table cells, and fallback plain extraction.
- Lowered content rejection threshold to reduce false negatives.

### Incorrect scraped total in summary

Symptom:
- Final summary under-reported saved docs.

Root cause:
- Batch buffer length was used as total.

Fix:
- Introduced a persistent `total_saved` counter.

### Thread-safety and compatibility

Fixes:
- Global tokenizer init for thread-safe `TokenCount` calculation.
- UTC timestamp updated to `datetime.now(timezone.utc)` for modern compatibility.

### Pylance missing imports

Symptom:
- `requests`, `bs4`, `ravendb`, `urllib3`, `tiktoken` unresolved in editor.

Root cause:
- Dependencies not installed into the exact workspace interpreter.

Fix:
- Installed required packages in `.venv`.
- Verified diagnostics cleared for the scraper file.

---

## Embeddings and Vector Hygiene

Issue discovered:
- Old vectors were generated with non-embedding settings, contaminating retrieval quality.

Reset strategy:
- Remove polluted embedding outputs.
- Regenerate embeddings with proper tasks and source text paths.
- Ensure the Multi-Map index points to the regenerated, correct vectors.

Important guideline:
- Prefer embedding `SearchableContent` for docs collection instead of raw mixed fields.

---

## Final Working Flow

1. Activate environment and verify dependencies.
2. Run sitemap collector with target collection.
3. Let incremental logic skip already-saved docs.
4. Inspect summary and failure reasons.
5. Retry or inspect `scripts/failed_urls.txt` if needed.
6. Run embedding generation tasks.
7. Query through agent + index and verify response quality.

---

## Commands

Install runtime dependencies in project venv:

```powershell
.\.venv\Scripts\python.exe -m pip install --no-cache-dir requests beautifulsoup4 ravendb tiktoken urllib3
```

Run full sitemap collection (all versions):

```powershell
.\.venv\Scripts\python.exe .\scripts\collect_docs_sitemap.py --all-versions --workers 20 --collection "Documentation_Sitemaps"
```

Run extraction unit tests:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_collect_docs_sitemap -v
```

---

## What This Means for Final Project Quality

You now have a real ETL/RAG ingestion pipeline, not just a script:
- Deterministic IDs.
- Incremental and resumable behavior.
- Better extraction quality for legacy docs.
- Measurable failure reasons.
- Embedding-ready metadata.
- Tests guarding extraction regressions.

This is exactly the engineering story to present: from raw scraper to reliable production data pipeline.

---

**Historical Snapshot — Pre-March-18 Version**

The following is the previous version of this document preserved for history and audit. It reflects earlier implementation notes and decisions prior to the March 18 changes. It is included verbatim to preserve context.

# 📖 How We Built It: RavenDB AI Helpdesk
**Project Documentation & Technical Guide**

---

## 🚀 The Mission
Build a Telegram bot that answers technical questions about RavenDB using a local AI model (RAG), avoiding cloud costs and utilizing local hardware (RTX 4060). 
---

## 🛠️ Step 1: Architecture Decisions

### Why Local?
- **Privacy & Cost:** Cloud tiers for AI are expensive.
- **Hardware:** We utilized the existing **NVIDIA RTX 4060 (8GB VRAM)**.
- **Model:** Selected **`llama3.1:8b`** because:
  - It fits in 8GB VRAM (uses ~5GB).
  - It has a large context window (128K) for reading many documents.

---

## 🛠️ Step 2: Data Collection (The Knowledge Base)

We needed data to "feed" the AI.
- **Source:** GitHub Discussions (Official RavenDB repo).
- **Tool:** Python script (`scripts/collect_discussions.py`).
- **Result:** Collected **1,052 discussions** into a JSON file.
- **Challenges:** Handling pagination and API rate limits.

---

## 🛠️ Step 3: Local Infrastructure Setup

1.  **RavenDB Installation:**
  - Installed RavenDB 7.2.0 locally.
  - Port: `8080`.
  - Setup: Unsecure mode (for easy development).

2.  **Licensing (Critical Step):**
  - **Issue:** The free "Community" license blocks AI features.
  - **Solution:** Applied **Developer License** (Ruppin) manually via `settings.json` / Studio.
  - **Outcome:** Unlocked "AI Agent", "GenAI", and "Vector Search".

3.  **OLLAMA Setup:**
    - Installed OLLAMA for Windows.
    - Command: `ollama pull llama3.1:8b`.
    - Verification: `http://localhost:11434` confirms service is running.

---

## 🛠️ Step 4: Connecting the Pieces

1.  **RavenDB -> OLLAMA:**
    - Created an **AI Connection String** in RavenDB Studio.
    - Name: `Local-Ollama`.
    - URL: `http://localhost:11434`.

2.  **Data Ingestion (RAG):**
- **Challenge:** A single 20MB JSON file is too big for AI to read at once.
  - **Solution:** Created `scripts/import_to_ravendb.py`.
  - **Process:** The script split the JSON into **1,052 separate documents** in the `Discussions` collection.
  - **Result:** Efficient Retrieval-Augmented Generation (AI reads only relevant docs).
---

## 🛠️ Step 5: Configuring the AI Agent (Current Status)

We are currently configuring the brain of the system:
1.  **Agent Name:** `RavenDB-Helpdesk`.
2.  **System Prompt:** Defined a strict persona ("RavenDB Expert Support Assistant").
3.  **Next Steps:**
    - Define the **Knowledge Base (RAG)** tool.
    - Test the agent with real questions.

---

## 📂 File Structure & Key Scripts

- `docs/PROJECT_STATUS.md` -> High-level milestones for the presentation.
- `docs/LOCAL_SETUP_GUIDE.md` -> Quick technical checklist for restarting the environment.
- `scripts/import_to_ravendb.py` -> The logic for splitting and uploading data.

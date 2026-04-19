# RavenDB AI Helpdesk — Architecture Document

**Project:** RavenDB AI Helpdesk Agent  
**Team:** Ron Blanky, Idan Dahan  
**Last Updated:** April 19, 2026  
**Status:** Production Pipeline Operational (Documentation + Discussions)

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture Diagram](#2-architecture-diagram)
3. [Data Sources & Collections](#3-data-sources--collections)
4. [Documentation Pipeline (Deep-Dive)](#4-documentation-pipeline-deep-dive)
5. [Discussions Pipeline](#5-discussions-pipeline)
6. [Google Groups Pipeline](#6-google-groups-pipeline)
7. [Azure AI Configuration](#7-azure-ai-configuration)
8. [Embedding Generation Tasks](#8-embedding-generation-tasks)
9. [Semantic Search Indexes](#9-semantic-search-indexes)
10. [AI Agent Configuration](#10-ai-agent-configuration)
11. [Telegram Bot Integration](#11-telegram-bot-integration)
12. [Platform Evolution Log](#12-platform-evolution-log)
13. [Cost Analysis](#13-cost-analysis)

---

## 1. System Overview

The RavenDB AI Helpdesk is a **Retrieval-Augmented Generation (RAG)** system that answers technical questions about RavenDB by searching through three knowledge sources:

- **Official Documentation** — 8,000+ pages scraped from `docs.ravendb.net` across 18 versions
- **GitHub Discussions** — 1,052 community Q&A threads from `ravendb/ravendb`
- **Google Groups Archive** — 112,000+ historical email messages from the `ravendb` Google Group

The system uses **Azure OpenAI** for both chat (answer generation) and text embeddings (semantic search), with **RavenDB 7.2** serving as the document store, vector database, and AI Agent orchestration platform.

---

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA COLLECTION LAYER                        │
│                                                                     │
│  ┌─────────────────┐  ┌──────────────────┐  ┌───────────────────┐  │
│  │  Python Sitemap  │  │  Python GitHub   │  │  C# MboxImporter  │  │
│  │  Scraper         │  │  GraphQL Client  │  │  (MimeKit)        │  │
│  │                  │  │                  │  │                   │  │
│  │  sitemap.xml     │  │  GitHub API v4   │  │  .mbox file       │  │
│  │  → HTTP/BS4      │  │  → GraphQL       │  │  → BulkInsert     │  │
│  │  → tiktoken      │  │  → JSON          │  │                   │  │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬──────────┘  │
│           │                     │                      │             │
└───────────┼─────────────────────┼──────────────────────┼─────────────┘
            │                     │                      │
            ▼                     ▼                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      RAVENDB 7.2 (Document Store)                   │
│                                                                     │
│  ┌─────────────────┐  ┌──────────────────┐  ┌───────────────────┐  │
│  │ Documentation_   │  │   Discussions    │  │ GoogleGroup       │  │
│  │ Sitemaps         │  │                  │  │ Messages          │  │
│  │ (~8,000 docs)    │  │ (1,052 threads)  │  │ (112,190 msgs)   │  │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬──────────┘  │
│           │                     │                      │             │
│           ▼                     ▼                      ▼             │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              Azure AI — Embedding Generation Tasks           │   │
│  │                                                              │   │
│  │  Model: text-embedding-3-small                               │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │   │
│  │  │documentations│  │ discussions  │  │ google-groups    │   │   │
│  │  │SearchableCont│  │ Body         │  │ Body (pending)   │   │   │
│  │  │MarkDownSplit │  │ PlainTextSpl │  │ PlainTextSplit   │   │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────┘   │
│           │                     │                      │             │
│           ▼                     ▼                      ▼             │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │        Semantic Search Index (KnowledgeBase/SemanticSearch)   │   │
│  │                                                              │   │
│  │  Multi-Map Index:                                            │   │
│  │    Documentation_Sitemaps → Title, Body, Category, Url,      │   │
│  │                             Source, BodyVector                │   │
│  │    Discussions            → Title, Body, Category, Url,      │   │
│  │                             Source, BodyVector                │   │
│  │    GoogleGroupMessages    → Title, Body, Category, Url,      │   │
│  │                             Source, BodyVector                │   │
│  └─────────────────────────────┬────────────────────────────────┘   │
│                                │                                     │
│                                ▼                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    AI Agent (RavenDB Expert Assistant)        │   │
│  │                                                              │   │
│  │  Chat Model: Azure gpt-4.1-mini                              │   │
│  │  Query Tool: "Search" → vector.search(BodyVector, $query)    │   │
│  │  Response: { Answer, ReferenceUrls[] }                       │   │
│  └─────────────────────────────┬────────────────────────────────┘   │
│                                │                                     │
└────────────────────────────────┼─────────────────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │     Telegram Bot        │
                    │     (.NET 8 / C#)       │
                    │                        │
                    │  User ↔ Bot ↔ Agent    │
                    └────────────────────────┘
```

---

## 3. Data Sources & Collections

### Summary Table

| Collection | Documents | Source | Ingestion Method | Embedding Field | Status |
|---|---|---|---|---|---|
| `Documentation_Sitemaps` | ~8,000 | `docs.ravendb.net` sitemap | Python ETL (`collect_docs_sitemap.py`) | `SearchableContent` | ✅ Complete |
| `Discussions` | 1,052 | GitHub Discussions API (GraphQL) | Python ETL (`collect_discussions.py`) | `Body` | ✅ Complete |
| `GoogleGroupMessages` | 112,190 | `.mbox` archive export | C# BulkInsert (`MboxImporter.cs`) | `Body` (pending) | ⏳ Embeddings Pending |

### Document Schemas

**Documentation_Sitemaps:**
```json
{
  "Title": "Querying Documents",
  "Url": "https://docs.ravendb.net/article-page/7.2/csharp/client-api/session/querying",
  "Body": "Full text content...",
  "Version": "7.2",
  "Category": "Client Api",
  "Sections": ["Overview", "Basic Queries", "Advanced Queries"],
  "CodeExamples": ["var results = session.Query<User>()..."],
  "Source": "OfficialDocs",
  "SearchableContent": "Querying Documents | Overview, Basic Queries, Advanced Queries | Full text...",
  "WordCount": 1523,
  "ProgrammingLanguage": "csharp",
  "ScrapedAt": "2026-03-18T14:32:45.123456Z",
  "ContentHash": "5d41402abc4b2a76b9719d911017c592",
  "TokenCount": 1247
}
```

**Discussions:**
```json
{
  "GitHubId": "D_kwDOAH...",
  "Number": 42,
  "Title": "How do I use Includes to fix N+1?",
  "Body": "I have a query that loads related documents...",
  "Url": "https://github.com/ravendb/ravendb/discussions/42",
  "CreatedAt": "2024-01-15T10:30:00Z",
  "UpdatedAt": "2024-01-16T08:00:00Z",
  "Author": "johndoe",
  "Category": { "Name": "Q&A", "Emoji": "🙏", "Description": "..." },
  "UpvoteCount": 5,
  "IsAnswered": true,
  "CommentsCount": 3,
  "Comments": [{ "Body": "...", "Author": "...", "IsAnswer": true }],
  "Answer": { "Body": "Use session.Include()...", "Author": "ayende" },
  "SearchableContent": "How do I use Includes to fix N+1? I have a query..."
}
```

**GoogleGroupMessages:**
```json
{
  "Title": "Re: RavenDB performance on large datasets",
  "Body": "The key is to use proper indexing strategies...",
  "Author": "oren@hibernatingrhinos.com",
  "CreatedAt": "2018-05-14T09:22:00+00:00",
  "MessageId": "<abc123@mail.gmail.com>",
  "ThreadId": "<thread-root@mail.gmail.com>",
  "Category": { "Name": "Google Groups", "Emoji": "📧", "Description": "Historical Google Groups archive" },
  "Url": "https://groups.google.com/g/ravendb/search?q=..."
}
```

---

## 4. Documentation Pipeline (Deep-Dive)

This section permanently records the design decisions and engineering work behind the Documentation_Sitemaps pipeline — the most technically complex data source.

### 4.1 URL Discovery Strategy

**Approach:** Sitemap-based discovery (`sitemap.xml`)

We parse the official RavenDB documentation sitemap to discover all URLs. This guarantees **100% coverage** of all published documentation pages across all 18 versions (1.0 through 7.2).

**Why not Crawl4AI?**  
We initially built a `Crawl4AI` scraper using headless Chromium (Playwright). While it produced clean Markdown, it was:
- **50–100x slower** (browser rendering + JavaScript execution)
- **Resource-heavy** (Playwright + Chromium memory footprint)
- **Limited coverage** (3 concurrent workers vs. 20 for HTTP)

The sitemap approach with `requests` + `BeautifulSoup` achieved **48–95 pages/sec** compared to Crawl4AI's ~1 page/sec.

### 4.2 Content Extraction & Quality

**Key engineering decisions:**

1. **Expanded tag support:** The initial extractor only looked at `<p>`, `<h2>`, `<h3>`, `<li>` tags. This missed glossary pages (`<dd>`, `<dt>`), table-heavy pages (`<td>`, `<th>`), and reference-style pages. We expanded to cover all semantic HTML tags.

2. **Fallback extraction:** For pages with unconventional markup, a fallback `get_text()` method captures raw text content, preventing false-negative failures.

3. **Content normalization:** `_normalize_content_lines()` removes duplicates, boilerplate ("Table of Contents", "Next", "Previous"), and whitespace-only lines.

### 4.3 Token Counting with tiktoken

**Problem:** Azure's `text-embedding-3-small` model has a token limit per request. Without knowing exact token counts, we risk:
- API errors from oversized payloads
- Unpredictable embedding costs

**Solution:** We integrated the `tiktoken` library (the same tokenizer used by OpenAI models) to compute exact token counts at scrape time. Each document stores a `TokenCount` field.

```python
import tiktoken
_tokenizer = tiktoken.get_encoding("cl100k_base")

def count_tokens(text):
    return len(_tokenizer.encode(text))
```

**Thread safety:** The tokenizer is initialized globally once and reused across all threads. The `encode()` method is stateless and thread-safe.

### 4.4 The SearchableContent Field

**Problem:** Embedding the raw `Body` field alone loses structural context. A page about "Session Querying" might have generic body text, but its title and section headings carry critical semantic signals.

**Solution:** We combine `Title`, `Sections`, and `Body` into a single `SearchableContent` field:

```
{Title} | {Section1}, {Section2}, ... | {Body text}
```

This field is what gets embedded by the Azure AI task, ensuring the vector captures:
- **What the page is about** (title)
- **What topics it covers** (sections)
- **The detailed content** (body)

### 4.5 Deterministic IDs & Incremental Ingestion

**Document ID format:**
```
Documentation_Sitemaps/{version}/{url-path-slug}
```

Example: `Documentation_Sitemaps/7.2/client-api-session-querying`

**Why deterministic IDs matter:**
- **Idempotent reruns:** Running the scraper twice on the same data produces zero duplicates.
- **Incremental updates:** The script queries RavenDB for existing document IDs and skips them (2-second rerun on 8,000 docs).
- **Collection routing:** RavenDB uses the ID prefix to route documents to the correct collection.

### 4.6 Performance Metrics

| Metric | Value |
|---|---|
| First run (8,000 docs) | ~160 seconds (2.7 minutes) |
| Incremental rerun (no changes) | ~2 seconds |
| Weekly update (50 new docs) | ~3 seconds |
| Throughput | 48–95 pages/sec |
| CPU usage | 25–30% (I/O bound) |
| Memory | ~400 KB for ID checking |

### 4.7 Failure Handling

- **HTTP retries** with exponential backoff via `requests.Session` + `urllib3.Retry`
- **Failure categorization:** Each failed URL gets a reason bucket (timeout, 404, empty content, extraction failure)
- **Failed URL export:** Written to `data_pipelines/failed_urls.txt` for manual review
- **Persistent counters:** `total_saved` tracks actual database writes, not batch buffer sizes

---

## 5. Discussions Pipeline

### Ingestion

**Script:** `collect_discussions.py`  
**API:** GitHub GraphQL API v4  
**Authentication:** GitHub Personal Access Token (`GITHUB_TOKEN`)

The script pages through all discussions in `ravendb/ravendb` (100 per page) via GraphQL, extracting:
- Full discussion body + metadata
- All comments (up to 50 per discussion)
- The accepted answer (if marked)
- Category, labels, upvote count

**Import to RavenDB:** Via `import_to_ravendb.py` which reads the collected JSON and writes documents with deduplication (comparing `UpdatedAt` timestamps).

### Embedding Configuration

- **AI Task:** `discussions`
- **Source field:** `Body`
- **Chunking:** `PlainTextSplit` at 2048 tokens
- **Connection:** `Azure-Text-Embeddings`

---

## 6. Google Groups Pipeline

### Ingestion

**Tool:** `MboxImporter.cs` (C# / .NET 8)  
**Library:** MimeKit for MIME parsing  
**Method:** `BulkInsert` for maximum throughput

The importer reads the `.mbox` archive file (exported from Google Groups) and streams messages directly into RavenDB via `BulkInsert`. Each message is stored as a `GoogleGroupMessage` document.

**Current status:** 112,190 messages imported. Embedding generation task pending.

### Data Quality Considerations

Google Groups messages contain raw email content that may include:
- Quoted reply chains (`> On Monday, John wrote:...`)
- Email signatures and auto-footers
- HTML email artifacts
- Short or empty messages

A preprocessing step to create a `SearchableContent` field (similar to Documentation_Sitemaps) may improve embedding quality.

---

## 7. Azure AI Configuration

### Why Azure AI?

We migrated from **Ollama + Llama 3.1:8b** (local GPU) to **Azure OpenAI** for a critical reason: Azure provides both **Chat** and **Text Embeddings** models through a single integration. The previous Ollama setup lacked a text embeddings model, which is required for the RAG knowledge base pipeline.

### Connection Strings

| Name | Type | Model | Deployment | Endpoint |
|---|---|---|---|---|
| `Azure-Chat` | Chat | `gpt-4.1-mini` | `gpt-4.1-mini` | `https://idan-ravendb-ai-us2.openai.azure.com/` |
| `Azure-Text-Embeddings` | Text Embeddings | `text-embedding-3-small` | `text-embedding-3-small` | `https://idan-ravendb-ai-us2.openai.azure.com/` |

### Budget

- **Available credit:** ~$100 (Azure for Students / sponsored)
- **Embedding cost estimate:** ~$0.02 per 1M tokens
- **Documentation embeddings:** ~10M tokens → ~$0.20
- **Discussions embeddings:** ~1M tokens → ~$0.02
- **Google Groups embeddings:** ~56M tokens → ~$1.12
- **Total estimated:** < $2.00

---

## 8. Embedding Generation Tasks

### Active Tasks

| Task Name | Collection | Source Path | Chunking Method | Max Tokens | Overlap | Connection | Status |
|---|---|---|---|---|---|---|---|
| `documentations` | `Documentation_Sitemaps` | `SearchableContent` | MarkDownSplitParagraphs | 2048 | 0 | Azure-Text-Embeddings | ✅ Active |
| `discussions` | `Discussions` | `Body` | PlainTextSplit | 2048 | 0 | Azure-Text-Embeddings | ✅ Active |
| `google-groups` | `GoogleGroupMessages` | `Body` | PlainTextSplit | 2048 | 0 | Azure-Text-Embeddings | ⏳ Pending |

### Why MarkDownSplitParagraphs for Documentation?

The `SearchableContent` field in Documentation_Sitemaps retains Markdown structure (headings, code blocks, lists). `MarkDownSplitParagraphs` is aware of Markdown boundaries and produces semantically coherent chunks that don't split mid-paragraph or mid-code-block.

### Why PlainTextSplit for Discussions & Google Groups?

Discussion bodies and email messages are freeform text without consistent Markdown structure. `PlainTextSplit` is the appropriate chunking strategy for unstructured content.

---

## 9. Semantic Search Indexes

### Per-Collection Indexes (Current — Studio)

These indexes are configured directly in RavenDB Studio for development and testing:

**Index: `KnowledgeBase/SemanticSearch/Documentations`**
```csharp
docs.Documentation_Sitemaps.Select(doc => new {
    Title = doc.Title,
    Body = doc.SearchableContent,
    Category = doc.Category,
    Url = doc.Url,
    Source = doc.Source,
    BodyVector = LoadVector("SearchableContent", "documentations")
})
```

**Index: `KnowledgeBase/SemanticSearch/Discussions`**
```csharp
docs.Discussions.Select(doc => new {
    Title = doc.Title,
    Body = doc.Body,
    Category = "GitHub Discussion",
    Url = doc.Url,
    Source = "Discussions",
    BodyVector = LoadVector("Body", "discussions")
})
```

### Unified Multi-Map Index (Target — C# Code)

The final production architecture uses a single multi-map index defined in `HelpdeskAgent/Indexes/KnowledgeBase_SemanticSearch.cs` that unifies all three collections:

```csharp
public class KnowledgeBase_SemanticSearch : AbstractMultiMapIndexCreationTask
{
    public KnowledgeBase_SemanticSearch()
    {
        // Map 1: Documentation
        AddMap<Documentation>(docs => from doc in docs
            select new {
                Title = doc.Title,
                Body = doc.Body,
                Category = doc.Category,
                Url = doc.Url,
                Source = "Documentation",
                BodyVector = CreateVector("embed-docs")
            });

        // Map 2: GitHub Discussions
        AddMap<Discussion>(discussions => from doc in discussions
            select new {
                Title = doc.Title,
                Body = doc.Body,
                Category = doc.Category.Name,
                Url = doc.Url,
                Source = "GitHub Discussions",
                BodyVector = CreateVector("embed-discussions")
            });

        // Map 3: Google Groups
        AddMap<GoogleGroupMessage>(messages => from doc in messages
            select new {
                Title = doc.Title,
                Body = doc.Body,
                Category = doc.Category.Name,
                Url = doc.Url,
                Source = "Google Groups",
                BodyVector = CreateVector("embed-google-groups")
            });

        Configuration["Indexing.Static.SearchEngineType"] = "Corax";
    }
}
```

**Key design:** The agent issues a single query (`from index 'KnowledgeBase/SemanticSearch'`) and receives results from all three data sources, ranked by semantic relevance.

---

## 10. AI Agent Configuration

### Agent Definition

| Setting | Value |
|---|---|
| Name | `RavenDB Expert Assistant` |
| Identifier | `raven-helpdesk-assistant` |
| Connection String | `Azure-Chat` (gpt-4.1-mini) |
| Query Tool | `Search` — unified semantic search |

### System Prompt

```
You are an expert RavenDB Support Assistant.
Your job is to answer user questions using the official documentation,
GitHub discussions, and historical Google Group archives.

### Instructions
1. **Analyze the User Query:** Carefully evaluate what the user is asking.
2. **Execute Search:** You MUST use the `Search` tool to perform a semantic
   search on the knowledge base. Formulate effective and concise search terms.
3. **Synthesize Results:** Read the results and construct a helpful answer.
4. **Cite Sources:** Always cite your sources using the Urls from search results.

Format your response in Markdown. Use ticks (`) for identifiers or code.
Do not hallucinate features.
```

### Query Tool Configuration

```sql
from index 'KnowledgeBase/SemanticSearch'
where vector.search(BodyVector, $query)
limit 5
```

**Sample parameters:** `{"query": "Exact keywords to search for in the database"}`

### Response Schema

```json
{
  "Answer": "Detailed explanation of the solution based on the documentation.",
  "ReferenceUrls": ["https://docs.ravendb.net/...", "https://github.com/..."]
}
```

---

## 11. Telegram Bot Integration

The Telegram bot (`TelegramBot/Program.cs`) serves as the user-facing interface:

```
User (Telegram) → Bot (.NET 8) → RavenDB AI Agent → Azure Chat → Response
```

### Features

- `/start` — Welcome message with usage instructions
- `/help` — Example questions and command list
- `/clear` — Reset conversation context
- `/about` — Project credits and tech stack
- Free-text questions routed to the AI Agent
- Markdown response rendering with plain-text fallback
- 4096-character message splitting for long responses
- Daily conversation IDs (`chats/{chatId}/{yyyy-MM-dd}`)

### Configuration (`appsettings.json`)

```json
{
  "RavenDB": {
    "Urls": ["http://127.0.0.1:8080"],
    "Database": "HelpdeskDB",
    "AgentName": "RavenDB-Support"
  },
  "Telegram": {
    "BotToken": "YOUR_TELEGRAM_BOT_TOKEN_HERE"
  }
}
```

---

## 12. Platform Evolution Log

| Date | Change | Reason |
|---|---|---|
| Feb 2026 | Initial setup with RavenDB 7.2 + Ollama + Llama 3.1:8b (local GPU) | Prototype — avoid cloud costs, utilize RTX 4060 |
| Feb 2026 | Applied Ruppin Developer License | Unlocked AI Agent, GenAI, and Vector Search features |
| Feb 2026 | Collected 1,052 GitHub Discussions | First knowledge base source |
| Mar 2026 | Built sitemap-based documentation scraper | Replaced early basic scraper and Crawl4AI approach |
| Mar 2026 | Added `tiktoken` token counting | Prevent Azure API token limit errors |
| Mar 2026 | Created `SearchableContent` field design | Improve embedding quality with structured context |
| Mar 2026 | Fixed RavenDB collection routing bug | Document ID prefix must match collection name |
| Mar 2026 | Imported 112k Google Groups messages via MboxImporter | Third and final knowledge source |
| Apr 2026 | **Migrated from Ollama to Azure OpenAI** | **Azure provides both Chat AND Text Embeddings — Ollama lacked embeddings** |
| Apr 2026 | Configured Azure connection strings (Chat + Embeddings) | `gpt-4.1-mini` for chat, `text-embedding-3-small` for embeddings |
| Apr 2026 | Created embedding tasks for Documentation + Discussions | Vectors now generated via Azure AI |
| Apr 2026 | Created per-collection semantic search indexes | Development/testing indexes in RavenDB Studio |

---

## 13. Cost Analysis

### Embedding Costs (Azure text-embedding-3-small)

| Collection | Est. Documents | Avg. Tokens/Doc | Total Tokens | Cost ($0.02/1M) |
|---|---|---|---|---|
| Documentation_Sitemaps | 8,000 | 1,200 | 9,600,000 | $0.19 |
| Discussions | 1,052 | 800 | 841,600 | $0.02 |
| GoogleGroupMessages | 112,190 | 500 | 56,095,000 | $1.12 |
| **Total** | **121,242** | — | **66,536,600** | **$1.33** |

### Chat Costs (Azure gpt-4.1-mini)

Per-query cost is negligible for development and testing. At ~1,000 tokens per query round-trip, 100 test queries would cost approximately $0.04.

**Total project AI cost:** < $5.00 (well within $100 budget)

---

*This document serves as the permanent architectural record of the RavenDB AI Helpdesk project.*  
*For setup instructions, see `docs/LOCAL_SETUP_GUIDE.md`.*  
*For the AI Agent configuration guide, see `docs/AI_AGENT_GUIDE.md`.*

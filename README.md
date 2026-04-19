# RavenDB AI Helpdesk Agent

An **Retrieval-Augmented Generation (RAG)** helpdesk system built on **RavenDB 7.2**, powered by **Azure OpenAI**. It answers technical questions about RavenDB by semantically searching through 120,000+ knowledge documents spanning official documentation, GitHub discussions, and historical Google Groups archives.

**Team:** Ron Blanky, Idan Dahan  
**Academic:** Final Year Project — Ruppin Academic Center  
**Supervisor:** Oren Eini (CEO, RavenDB / Hibernating Rhinos)

---

## Architecture

```
User (Telegram) → Bot (.NET 8) → RavenDB AI Agent → Azure GPT-4.1-mini → Answer
                                       ↑
                              Semantic Search (vector.search)
                                       ↑
                            ┌──────────┼──────────┐
                            ▼          ▼          ▼
                     Documentation  Discussions  Google Groups
                     (~8,000 docs) (1,052 threads)(112k msgs)
                            │          │          │
                     Azure text-embedding-3-small (embeddings)
```

For the full technical deep-dive, see [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Data Sources

| Source | Collection | Documents | Ingestion |
|---|---|---|---|
| [RavenDB Official Docs](https://docs.ravendb.net) | `Documentation_Sitemaps` | ~8,000 | Python sitemap scraper |
| [GitHub Discussions](https://github.com/ravendb/ravendb/discussions) | `Discussions` | 1,052 | Python GraphQL client |
| [Google Groups Archive](https://groups.google.com/g/ravendb) | `GoogleGroupMessages` | 112,190 | C# MboxImporter |

---

## Technology Stack

| Layer | Technology |
|---|---|
| Document Store & Vector DB | RavenDB 7.2 (Developer License) |
| Chat LLM | Azure OpenAI — `gpt-4.1-mini` |
| Text Embeddings | Azure OpenAI — `text-embedding-3-small` |
| Data Collection | Python 3.10+ (requests, BeautifulSoup, tiktoken) |
| Agent & Bot Runtime | .NET 8 / C# |
| User Interface | Telegram Bot (Telegram.Bot SDK) |
| Embedding Orchestration | RavenDB AI Tasks (built-in) |
| Semantic Search | RavenDB Corax engine with vector indexes |

---

## Repository Structure

```
RavenDB/
├── ARCHITECTURE.md              # Full technical architecture document
├── README.md                    # This file
├── .gitignore
│
├── HelpdeskAgent/               # .NET project: Agent definition + data models
│   ├── Agent/                   #   AI Agent configuration (HelpdeskAssistant.cs)
│   ├── Indexes/                 #   Multi-map semantic search index
│   ├── Model/                   #   Data models (Discussion, Documentation, GoogleGroupMessage)
│   ├── MboxImporter.cs          #   Google Groups .mbox file importer
│   └── Program.cs               #   Entry point: deploys agent + index to RavenDB
│
├── TelegramBot/                 # .NET project: Telegram bot interface
│   ├── Program.cs               #   Bot logic: polling, commands, agent integration
│   └── appsettings.example.json #   Configuration template
│
├── scripts/                     # Python data collection & import scripts
│   ├── collect_docs_sitemap.py  #   Production documentation scraper
│   ├── collect_discussions.py   #   GitHub Discussions collector (GraphQL)
│   ├── import_to_ravendb.py     #   Multi-source RavenDB importer
│   └── .env                     #   Environment variables (gitignored)
│
├── tests/                       # Validation & quality comparison scripts
│   ├── test_collect_docs_sitemap.py        # Unit tests for extraction
│   ├── compare_documentation_collections.py # Quality comparison tool
│   └── README.md
│
├── docs/                        # Project documentation
│   ├── AI_AGENT_GUIDE.md        #   Comprehensive agent configuration guide
│   ├── HOW_WE_DID_IT.md         #   End-to-end technical narrative
│   ├── LOCAL_SETUP_GUIDE.md     #   Environment setup instructions
│   ├── PROJECT_STATUS.md        #   Milestone tracking
│   └── SETTING_UP_VECTORS.md    #   Embedding & vector search workflow
│
├── samples.properties/          # Reference project: PropertySphere by Oren Eini
│   └── (full .NET sample app)   #   Used as reference implementation for Agent + Telegram patterns
│
└── config/                      # Environment configuration (gitignored)
    └── cluster_config.env       #   RavenDB Cloud cluster details
```

---

## Quick Start

### Prerequisites

- **RavenDB 7.2** with Developer License (AI features required)
- **Azure OpenAI** access with `gpt-4.1-mini` and `text-embedding-3-small` deployments
- **.NET 8 SDK**
- **Python 3.10+** with pip
- **Telegram Bot Token** (from [@BotFather](https://t.me/BotFather))

### 1. Start RavenDB

```powershell
cd C:\Users\Ron\Desktop\RavenDB-7.2.0-windows-x64
.\run.ps1
# Studio: http://127.0.0.1:8080
```

### 2. Configure Azure AI Connection Strings

In RavenDB Studio → AI Hub → AI Connection Strings:
- **Azure-Chat**: `gpt-4.1-mini` (Chat type)
- **Azure-Text-Embeddings**: `text-embedding-3-small` (Text Embeddings type)

### 3. Collect Data

```powershell
# Activate Python environment
.\.venv\Scripts\Activate

# Collect documentation (sitemap-based, ~3 minutes)
python scripts\collect_docs_sitemap.py --all-versions --workers 20 --collection "Documentation_Sitemaps"

# Collect GitHub discussions (requires GITHUB_TOKEN)
$env:GITHUB_TOKEN = "ghp_your_token_here"
python scripts\collect_discussions.py
python scripts\import_to_ravendb.py --source discussions
```

### 4. Deploy Agent & Index

```powershell
cd HelpdeskAgent
dotnet run
```

### 5. Start Telegram Bot

```powershell
cd TelegramBot
# Edit appsettings.json with your bot token
dotnet run
```

---

## Documentation

| Document | Description |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Full system architecture, data pipelines, and design decisions |
| [docs/AI_AGENT_GUIDE.md](docs/AI_AGENT_GUIDE.md) | Agent configuration, prompt engineering, and tool setup |
| [docs/HOW_WE_DID_IT.md](docs/HOW_WE_DID_IT.md) | End-to-end technical narrative and bug fixes |
| [docs/LOCAL_SETUP_GUIDE.md](docs/LOCAL_SETUP_GUIDE.md) | Environment setup checklist |
| [docs/SETTING_UP_VECTORS.md](docs/SETTING_UP_VECTORS.md) | Embedding generation and vector search guide |
| [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) | Milestone tracking and current status |

---

## License

This project is developed as part of a final-year academic project at Ruppin Academic Center under the supervision of Oren Eini (Hibernating Rhinos / RavenDB). All data collection from public sources (GitHub Discussions, Google Groups, official documentation) was performed with explicit approval from the RavenDB CEO.

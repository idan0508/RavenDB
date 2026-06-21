# Local Setup Guide — RavenDB AI Helpdesk

**Updated:** June 18, 2026

---

## Current Status

| Component | Status | Details |
|-----------|--------|---------|
| **RavenDB** | ✅ Installed | Running at `http://127.0.0.1:8080` |
| **License** | ✅ Applied | **Developer License** (Ruppin) — AI features unlocked |
| **Azure AI** | ✅ Configured | Chat (`gpt-4.1-mini`) + Embeddings (`text-embedding-3-small`) |
| **Data** | ✅ Ingested | Documentation (~8k), Discussions (1,052), Google Groups (112k) |
| **Agent** | ✅ Defined | `RavenDB Helpdesk Grounded v1` with three source-specific search tools |
| **Telegram Bot** | ✅ Built | Ready to run with valid bot token |

---

## Prerequisites

| Software | Version | Purpose |
|---|---|---|
| RavenDB | 7.2.0 | Document store, vector DB, AI Agent platform |
| .NET SDK | 8.0+ | HelpdeskAgent and TelegramBot projects |
| Python | 3.10+ | Data collection scripts |
| Azure OpenAI | — | Chat and text embedding models |

---

## Step 1: Start RavenDB

```powershell
cd C:\Users\Ron\Desktop\RavenDB-7.2.0-windows-x64
.\run.ps1
```

Studio URL: **http://127.0.0.1:8080**

> If the port changes, RavenDB will display the actual URL in the console output.

---

## Step 2: Verify License

1. Open RavenDB Studio
2. Go to **Settings** → **License** (left sidebar)
3. Confirm **Developer License** is active with AI features unlocked:
   - AI Agent ✅
   - GenAI ✅
   - Vector Search ✅

If the license is missing, apply it:

```json
{
    "Id": "67905d74-6942-409a-832d-e6fef909e536",
    "Name": "Ruppin",
    "Keys": [
        "qanxtbn4Qx3nAl0Q5o231/WwZ",
        "xzpTX+2HI+P7WIvj/qZxPMmuU",
        "sBcOg4kpMfMA7iXyK4zPfziwM",
        "ufst6NlCEWe6/bTHjNd2UclNE",
        "edjKvsIEjsB+Ug9NsN5fg6rtx",
        "QbABb596IPQ2kz91grU6lswld",
        "zUHLG7hs6zHE3sqhfxct1ABYE",
        "DNy4yBSYoSQMqKywtLi8wJzEy",
        "MzQVFjc4OTo7PD0+nwlffJ8Cf",
        "CCfAiEgnwljU8CJCCfAiUgnw",
        "ImlJ8CJyCfAiggnwlpIJ8CKiC",
        "fAisgnwIsIJ8CLSCfAi4gnwIv",
        "IJ8CMCCfAzZAAZ8CQiCfAkMgn",
        "wJEIJ8CRSCfAkYgnwJHIJ8CSC",
        "BDJEQJYgZdnwRBYANd"
    ]
}
```

---

## Step 3: Configure Azure AI Connection Strings

Navigate to **AI Hub** → **AI Connection Strings** in RavenDB Studio.

### Connection 1: Azure-Chat

| Setting | Value |
|---|---|
| Name | `Azure-Chat` |
| Model Type | **Chat** |
| Connector | Azure OpenAI |
| API Key | *(your Azure OpenAI key)* |
| Endpoint | `https://idan-ravendb-ai-us2.openai.azure.com/` |
| Model | `gpt-4.1-mini` |
| Deployment Name | `gpt-4.1-mini` |

### Connection 2: Azure-Text-Embeddings

| Setting | Value |
|---|---|
| Name | `Azure-Text-Embeddings` |
| Model Type | **Text Embeddings** |
| Connector | Azure OpenAI |
| API Key | *(your Azure OpenAI key)* |
| Endpoint | `https://idan-ravendb-ai-us2.openai.azure.com/` |
| Model | `text-embedding-3-small` |
| Deployment Name | `text-embedding-3-small` |

Click **Test Connection** on each to verify.

> **Why Azure instead of Ollama?**  
> Azure provides both Chat and Text Embeddings models through a single API.
> Our previous Ollama/Llama setup only supported chat — it lacked the text embeddings
> component required for the RAG knowledge base pipeline. See [ARCHITECTURE.md](../ARCHITECTURE.md)
> Section 12 for the full evolution log.

---

## Step 4: Verify Database & Collections

1. Open **Databases** in Studio
2. Select **HelpdeskDB**
3. Go to **Documents** tab
4. Verify these collections exist:

| Collection | Expected Documents |
|---|---|
| `Documentation_Sitemaps` | ~8,000 |
| `Discussions` | ~1,052 |
| `GoogleGroupMessages` | ~112,190 |

---

## Step 5: Verify Embedding Tasks

Navigate to **AI Hub** → **Embeddings Generation**.

| Task Name | Collection | Source Path | Status |
|---|---|---|---|
| `documentations` | Documentation_Sitemaps | SearchableContent | Should show ✅ Enabled |
| `discussions` | Discussions | Body | Should show ✅ Enabled |
| `groups` | GoogleGroupMessages | Body, Title | Existing task name: `googlegroups_embeddings` |

---

## Step 6: Verify Semantic Search Indexes

Navigate to **Indexes** in Studio.

Confirm these indexes exist and are not stale:
- `KnowledgeBase/SemanticSearch/Documentations`
- `KnowledgeBase/SemanticSearch/Discussions`
- `KnowledgeBase/SemanticSearch/GoogleGroups`

---

## Step 7: Set Up Python Environment

```powershell
# From the repository root
python -m venv .venv
.\.venv\Scripts\Activate

# Install dependencies
pip install requests beautifulsoup4 ravendb tiktoken urllib3 lxml
```

---

## Step 8: Deploy Agent & Index (C#)

```powershell
cd HelpdeskAgent
dotnet restore
dotnet run
```

This will:
1. Deploy three separate semantic-search indexes matching the Studio configuration
2. Register the `RavenDB Helpdesk Grounded v1` test agent with identifier `ravendb-helpdesk-grounded-v1`
3. Configure the `Grounded`, `NeedsClarification`, and `NotFound` response contract

---

## Step 9: Start Telegram Bot

```powershell
cd TelegramBot

# Create appsettings.json from template
copy appsettings.example.json appsettings.json

# Edit appsettings.json — set your Telegram bot token
# Then run:
dotnet restore
dotnet run
```

---

## Quick Commands Reference

```powershell
# Start RavenDB
cd C:\Users\Ron\Desktop\RavenDB-7.2.0-windows-x64
.\run.ps1

# Activate Python environment
cd C:\Users\Ron\Documents\GitHub\RavenDB
.\.venv\Scripts\Activate

# Run documentation scraper
python scripts\collect_docs_sitemap.py --all-versions --workers 20 --collection "Documentation_Sitemaps"

# Run extraction tests
python -m unittest tests.test_collect_docs_sitemap -v

# Deploy agent + index
cd HelpdeskAgent && dotnet run

# Start Telegram bot
cd TelegramBot && dotnet run
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| RavenDB port changed | Check console output for the actual URL |
| Azure connection test fails | Verify API key and endpoint URL in connection string |
| Agent not found error | Run `dotnet run` in `HelpdeskAgent/` to deploy it |
| Telegram bot token error | Get a new token from @BotFather |
| Python import errors | Activate `.venv` and reinstall dependencies |
| Index is stale | Wait for indexing to complete, or check for embedding task/index errors in Studio |
| Agent gives a generic answer | Verify all three tool index names exist and redeploy `HelpdeskAgent` |
| Telegram shows the not-found response for a good answer | Verify the agent returned `AnswerStatus = Grounded` and at least one exact allowed source URL |

---

## Checklist

- [x] RavenDB 7.2 installed and running
- [x] Developer License applied (AI features unlocked)
- [x] Azure-Chat connection string configured
- [x] Azure-Text-Embeddings connection string configured
- [x] HelpdeskDB database created
- [x] Documentation_Sitemaps collection populated
- [x] Discussions collection populated
- [x] GoogleGroupMessages collection populated
- [x] Embedding tasks created (documentations, discussions)
- [x] Semantic search indexes created
- [x] GoogleGroupMessages embedding task configured or the Google Groups tool intentionally left unavailable
- [x] AI Agent deployed
- [x] Telegram Bot configured

---

*For the full architecture, see [ARCHITECTURE.md](../ARCHITECTURE.md).*  
*For the agent configuration details, see [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md).*

# RavenDB AI Agent — Full Technical Configuration Guide

> **Purpose:** This document explains **every setting** of the RavenDB AI Agent Creator,
> what to put in each field, and **why** each choice matters.
>
> **Updated:** April 19, 2026 — Migrated from Ollama/Llama to Azure OpenAI.

---

## Table of Contents
1. [Architecture Overview](#1-architecture-overview)
2. [Basic Settings](#2-basic-settings)
3. [System Prompt](#3-system-prompt)
4. [Agent Parameters](#4-agent-parameters)
5. [Query Tools (RAG)](#5-query-tools-rag)
6. [Action Tools](#6-action-tools)
7. [Chat Trimming](#7-chat-trimming)
8. [Prompt Engineering Techniques Used](#8-prompt-engineering-techniques-used)
9. [Troubleshooting](#9-troubleshooting)
10. [Historical Notes (Ollama Era)](#10-historical-notes-ollama-era)

---

## 1. Architecture Overview

```
User Question
     │
     ▼
┌──────────────┐
│  AI Agent    │  ◄── System Prompt (personality + rules)
│  (Chat LLM)  │      Azure gpt-4.1-mini
└──────┬───────┘
       │  "I need to search for relevant data..."
       ▼
┌──────────────┐
│  Query Tool  │  ◄── RQL query with vector.search()
│  (Embeddings)│      Azure text-embedding-3-small
└──────┬───────┘
       │  Returns matching documents
       ▼
┌──────────────┐
│  AI Agent    │  ◄── Reads the documents + formulates answer
│  (Chat LLM)  │
└──────────────┘
       │
       ▼
   Final Answer to User
```

**Two connection strings are needed:**

| Connection String | Type | Model | Purpose |
|---|---|---|---|
| `Azure-Chat` | Chat | `gpt-4.1-mini` | The "Mouth" — generates human-readable answers |
| `Azure-Text-Embeddings` | Text Embeddings | `text-embedding-3-small` | The "Librarian" — converts text to vectors for semantic search |

> **Why Azure instead of Ollama?**
>
> We migrated from Ollama + Llama 3.1:8b (local GPU) to Azure OpenAI because:
> - Azure provides **both Chat and Text Embeddings** in a single API
> - Ollama lacked a production-quality text embeddings model
> - Text embeddings are essential for the RAG knowledge base pipeline
> - Azure's `gpt-4.1-mini` is significantly more capable than Llama 3.1:8b for tool-calling
>
> With Azure, the VRAM/GPU constraints and context length tuning from the Ollama era no longer apply.
> The model runs in the cloud with effectively unlimited context.

---

## 2. Basic Settings

These are the top-level fields on the "Create AI Agent" screen.

| Field | Value | Why |
|---|---|---|
| **Agent Name** | `RavenDB Expert Assistant` | Descriptive name shown in Studio |
| **Identifier** | `raven-helpdesk-assistant` | Slug used in API calls and conversation IDs |
| **Agent State** | `Enabled` | Must be Enabled to accept queries |
| **Connection String** | `Azure-Chat` | Select the **Chat** connection (NOT Embeddings). The Agent uses this to generate answers. |

---

## 3. System Prompt

The System Prompt tells the AI **who it is** and **how to behave**.

### Current Production Prompt

```
You are an expert RavenDB Support Assistant.
Your job is to answer user questions using the official documentation,
GitHub discussions, and historical Google Group archives.

### Instructions
1. **Analyze the User Query:** Carefully evaluate what the user is asking about RavenDB.
2. **Execute Search:** You MUST use the `Search` tool to perform a semantic search
   on the knowledge base. Formulate effective and concise search terms derived from
   the user's query.
3. **Synthesize Results:** Read the results from the `Search` tool and construct
   a helpful answer.
4. **Cite Sources:** Always cite your sources using the Urls provided in the search results.

Format your response in Markdown. Make sure to use ticks (`) whenever you discuss
identifiers or code. Do not hallucinate features.
```

### Why This Prompt Works

With Azure's `gpt-4.1-mini`, we can use a natural, instruction-following prompt instead of the aggressive "state machine" prompt required for local 7B/8B models. Key principles:

1. **Tool-First:** The prompt explicitly says "You MUST use the Search tool" — preventing the model from answering from training data.
2. **Source Citation:** Forces the agent to ground answers in retrieved documents.
3. **No Embedded Knowledge:** The prompt contains zero RavenDB-specific knowledge. All knowledge comes from the search results.

> **Lesson Learned:** Our early prompt (v1) included "Golden Rules" with hardcoded RavenDB knowledge
> (N+1, Includes, Stream, etc.). The AI read those rules and answered from memory
> **without ever calling the search tools**. Evidence: `RemainingToolIterations: 16`.
> Fix: Remove all hardcoded knowledge. Force the AI to SEARCH for answers.

### Response Schema

```json
{
  "Answer": "Detailed explanation of the solution based on the documentation.",
  "ReferenceUrls": ["https://docs.ravendb.net/...", "https://github.com/..."]
}
```

---

## 4. Agent Parameters

**Location:** The "Set agent parameters" section below the System Prompt.

Agent Parameters are **fixed values** that the agent injects into Query Tool queries. They act as **security filters** — the AI model **cannot override** these values.

### Our Configuration: **None needed — delete any existing parameters**

Since our Query Tools use the unified `KnowledgeBase/SemanticSearch` index directly, we don't need collection-level parameters.

### When WOULD you need parameters?
Parameters are useful when you want **one query tool to search different collections** dynamically. For example:

```sql
-- This query uses a parameter:
from $collection where vector.search(...)

-- Our query hardcodes the index (no parameter needed):
from index 'KnowledgeBase/SemanticSearch' where vector.search(...)
```

Since we use a multi-map index that already searches all three collections, parameters aren't needed.

---

## 5. Query Tools (RAG)

**Location:** The "Define agent tools" section → "Query tools" tab.

Query Tools are the **hands** of your agent. They let the AI **search your database** for relevant information before answering.

### Tool 1: Semantic Search (Primary)

This is the **primary tool**. It uses embeddings to find documents semantically similar to the user's question across all three knowledge sources.

| Field | Value |
|---|---|
| **Tool Name** | `Search` |
| **Description** | `Searches the unified Knowledge Base consisting of RavenDB documentation, GitHub discussions, and Google Groups.` |

**Query:**
```sql
from index 'KnowledgeBase/SemanticSearch'
where vector.search(BodyVector, $query)
limit 5
```

**Sample parameters object:**
```json
{
    "query": "Exact keywords to search for in the database"
}
```

> **Why one unified tool instead of per-collection tools?**
>
> The multi-map index `KnowledgeBase/SemanticSearch` maps all three collections
> (Documentation, Discussions, Google Groups) into a single searchable index.
> This means the agent issues one query and gets the best results from ANY source,
> ranked by semantic relevance. The `Source` field in results tells the agent
> where each result came from.

### Tool 2: Keyword Search (Optional Fallback)

For cases where the user asks about a specific error message or exact term.

| Field | Value |
|---|---|
| **Tool Name** | `SearchByKeyword` |
| **Description** | `Search for a specific error message, configuration key, or exact term in the Discussions database. Use this when the user mentions a specific error or exact term.` |

**Query:**
```sql
from "Discussions"
where search(Body, $keyword) or search(Title, $keyword)
select Title, Body, Category, Url
limit 5
```

**Sample parameters object:**
```json
{
    "keyword": "InvalidOperationException"
}
```

### Why Two Tools?
- **Semantic Search** finds discussions about the same *topic* even if different words are used (e.g., "backup" finds "snapshot", "export").
- **Keyword Search** finds discussions with an *exact* match (e.g., error code `InvalidOperationException`).

---

## 6. Action Tools

**Location:** The "Define agent tools" section → "Action tools" tab.

Action Tools let the agent **trigger external actions** (like sending an email or creating a support ticket). For now, we don't need any.

### Our Configuration: **Leave empty** (no action tools)

### Why:
- Our agent is **read-only** — it only answers questions.
- Action tools are for scenarios like: "Create a new order", "Send an alert email", etc.
- We can add these later if we build escalation workflows.

---

## 7. Chat Trimming

**Location:** The bottom section "Configure chat trimming".

Chat trimming controls how the agent handles **long conversations** that exceed the model's token limit.

### Our Configuration:

| Setting | Value | Why |
|---|---|---|
| **Trimming Method** | `Summarize chat` | When conversation gets too long, older messages are summarized instead of deleted. Best for maintaining context. |
| **Max tokens before summarization** | **32768** | Azure gpt-4.1-mini supports large context windows. No VRAM constraints with cloud API. |
| **Max tokens after summarization** | `1024` (Default) | The summary of old messages will be compressed to ~1024 tokens. |
| **Enable history** | `OFF` | For a helpdesk bot, each question is independent. No need to remember past conversations across sessions. |

---

## 8. Prompt Engineering Techniques Used

Based on Oren Eini's blog posts, COD#6 video, and NotebookLM analysis:

### Technique 1: Tool-First Architecture
**What:** Force the AI to use database search tools before answering.
**Source:** [Oren's Reranking Agent](https://ayende.com/blog/203171-B/using-ai-agents-for-reranking-in-ravendb) + COD#6.
**Our adaptation:** System Prompt says "You MUST use the Search tool."
**Why it works:** Prevents the AI from answering from training data. Ensures answers come from actual data.

### Technique 2: Explicit Tool Descriptions ("When-to-Use")
**What:** The tool Description field is the instruction the LLM reads to decide WHEN to call a tool.
**Source:** NotebookLM (COD#6): *"The description is meant for the model to understand when and how it should be called."*
**Our adaptation:** Description clearly describes what each tool searches.
**Why it works:** A vague description means the LLM won't call the tool. A clear one triggers it reliably.

### Technique 3: Few-Shot via Sample Objects
**What:** Provide realistic sample values (not descriptions) in parameter objects.
**Source:** Oren's blog: `SampleObject = JsonConvert.SerializeObject(new { ... })`
**Our adaptation:** `"query": "how to use Includes to fix N+1"` instead of `"The user's question..."`
**Why it works:** Shows the model what GOOD input looks like, teaching by example.

### Technique 4: Structured Output via Sample Response
**What:** Force the AI to respond in a specific JSON structure.
**Source:** NotebookLM: *"RavenDB analyzes your sample values... forces the LLM to output valid JSON matching that structure."*
**Our adaptation:** Sample Response with `Answer` + `ReferenceUrls` fields.
**Why it works:** Makes responses predictable and parseable by the application.

### Technique 5: Role Prompting (Minimal)
**What:** Give the AI a short professional identity.
**Our adaptation:** "You are an expert RavenDB Support Assistant." — short but clear.
**Why it works:** The AI adopts the vocabulary and caution level of that role.

### Removed: Embedded Knowledge Base
**What we had:** "Golden Rules" — hardcoded N+1, Includes, Stream rules in the System Prompt.
**Why we removed it:** The AI used these rules as answers WITHOUT searching the database.
**Lesson:** For RAG agents, the knowledge must come from the SEARCH RESULTS, not the prompt.

---

## 9. Troubleshooting

### Problem: Agent returns generic answers without searching
**Cause:** System prompt contains hardcoded knowledge, or tool description is too vague.
**Fix:** Remove all RavenDB-specific knowledge from the prompt. Make tool descriptions explicit ("You MUST use this tool").

### Problem: `System.IO.InvalidDataException: Cannot have a 'T' in this position...`
**Cause:** Mismatch between System Prompt format instructions and Sample Response schema.
**Fix:** Ensure the System Prompt's output format matches the Sample Response JSON structure exactly.

### Problem: Agent not calling any tools
**Cause:** The tool description is too vague, or the model doesn't recognize when to trigger it.
**Fix:** Add explicit trigger language to the tool description: "Use this tool for every question."

### Problem: Empty or irrelevant search results
**Cause:** Embeddings not generated, index is stale, or wrong vector field referenced.
**Fix:** Check embedding task status in AI Hub. Verify index is not stale. Run a test semantic query directly in Studio.

---

## 10. Historical Notes (Ollama Era)

> **This section preserves the original Ollama/Llama configuration for historical reference.**
> These settings are **no longer active** — we migrated to Azure OpenAI in April 2026.

### Previous Connection Strings
| Name | Type | Model |
|---|---|---|
| `Local-Ollama-Chat` | Chat | `llama3.1:8b` via Ollama |
| `Local-Ollama-Embeddings` | Embeddings | `nomic-embed-text` via Ollama |

### Previous VRAM Constraints
- **GPU:** NVIDIA RTX 4060 (8GB VRAM)
- **Model footprint:** ~5.2GB for `llama3.1:8b`
- **Context limit:** 8192 tokens (to avoid CPU offloading)
- **Throughput:** ~40 tokens/sec at 8K context

### Previous System Prompt (State Machine — for 7B/8B models)

Small local models required an aggressive "state machine" prompt with:
- **Semantic Distancing** — long, mechanically descriptive parameter keys to prevent schema bleed
- **Cognitive Buffering** — forcing the model to explain its reasoning before generating search terms
- **Empty response schema** — `""` instead of JSON to prevent the model from confusing tool parameters with response format

This complexity was required because 7B/8B parameter models struggle to simultaneously process JSON tool parameters and JSON response schemas. With Azure's `gpt-4.1-mini` (a much larger, more capable model), none of these workarounds are needed.

---

## Setup Checklist

```
Pre-requisites:
[x] Connection String: Azure-Chat (Chat type) — TESTED ✅
[x] Connection String: Azure-Text-Embeddings (Embeddings type) — TESTED ✅
[x] Azure credit available (~$100)

Agent Configuration:
[x] Agent Name: RavenDB Expert Assistant
[x] Connection String: Azure-Chat selected
[x] System Prompt: Tool-First with citation instructions
[x] Sample Response Object: { Answer, ReferenceUrls[] }
[x] Agent Parameters: Empty (none needed)
[x] Query Tool: Search — unified KnowledgeBase/SemanticSearch index
[x] Action Tools: Empty (none needed)
[x] Chat Trimming: Summarize at 32768 tokens

Verification:
[ ] Test: "How do I handle N+1 query issues?" → Tool was called
[ ] Test: "Show me C# code for Includes" → Answer contains C# code
[ ] Test: "What is InvalidOperationException?" → SearchByKeyword was used
```

---

*Last Updated: April 19, 2026*
*v4 — Updated for Azure OpenAI migration. Ollama-era notes preserved in Section 10.*

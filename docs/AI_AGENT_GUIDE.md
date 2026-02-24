# 🤖 RavenDB AI Agent – Full Technical Configuration Guide

> **Purpose:** This document explains **every setting** of the RavenDB AI Agent Creator,
> what to put in each field, and **why** each choice matters.

---

## Table of Contents
1. [Architecture Overview](#1-architecture-overview)
2. [Basic Settings](#2-basic-settings)
3. [System Prompt (V2 Professional)](#3-system-prompt-v2-professional)
4. [Agent Parameters](#4-agent-parameters)
5. [Query Tools (RAG)](#5-query-tools-rag)
6. [Action Tools](#6-action-tools)
7. [Chat Trimming](#7-chat-trimming)
8. [Prompt Engineering Techniques Used](#8-prompt-engineering-techniques-used)

---

## 1. Architecture Overview

```
User Question
     │
     ▼
┌──────────────┐
│  AI Agent    │  ◄── System Prompt (personality + rules)
│  (Chat LLM)  │
└──────┬───────┘
       │  "I need to search for relevant data..."
       ▼
┌──────────────┐
│  Query Tool  │  ◄── RQL query with vector.search()
│  (Embeddings)│
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

| Connection String | Type | Purpose |
|---|---|---|
| `Local-Ollama-Chat` | Chat | The "Mouth" – generates human-readable answers |
| `Local-Ollama-Embeddings` | Text Embeddings | The "Librarian" – converts text to vectors for semantic search |

> **⚠️ CRITICAL RULE OF THUMB — Context Length:**
>
> **Ollama Context Length ≥ RavenDB "Max tokens before summarization"**
>
> **For 8GB GPUs (like RTX 4060):**
> *   **Sweet Spot:** **8K (8192)** context.
> *   **Why?** 5.2GB (Model) + 2.0GB (KV Cache) = ~7.2GB. Fits in VRAM. ⚡ **Fast (~40 t/s)**.
> *   **Risk:** 16K context requires ~9.0GB. This overflows to RAM. 🐢 **Slow (~8 t/s)**.
> *   **Action:** Set Ollama & RavenDB Trimming to **8192**.
>
> **For 12GB+ GPUs (RTX 4070 Ti, 3080 Ti):**
> *   Ollama Context Length: **16K** or **32K**
> *   RavenDB Chat Trimming: Match the slider value (e.g., 16384 or 32768)
>
> **Why?**
> If the model + context size exceeds your GPU VRAM (8GB), Ollama offloads work to your CPU.
> This causes **100% CPU usage** and very slow responses.
>
> | Setting Location | Setting Name | Recommended Value (8GB VRAM) |
> |---|---|---|
> | Ollama Desktop → Settings | Context length | **8K** (slide to left) |
> | RavenDB Agent → Chat Trimming | Max tokens before summarization | **8192** |

---

## 2. Basic Settings

These are the top-level fields on the "Create AI Agent" screen.

| Field | Value | Why |
|---|---|---|
| **Agent Name** | `RavenDB-Helpdesk-v3` | New clean agent (keep old ones for comparison) |
| **Identifier** | `ravendb-helpdesk-v3` | Auto-generated slug, used in API calls |
| **Agent State** | `Enabled` | Must be Enabled to accept queries |
| **Connection String** | `Local-Ollama` | Select the **Chat** connection (NOT Embeddings). The Agent uses this to generate answers. |

---

## 3. System Prompt (v3 — Tool-First)

The System Prompt tells the AI **who it is** and **how to behave**.

> **⚠️ CRITICAL LESSON LEARNED:**
>
> Our previous prompt (~400 words) had "Golden Rules" with hardcoded RavenDB knowledge
> (N+1, Includes, Stream, etc.). The AI read those rules and answered from memory
> **without ever calling the search tools**. Evidence: `RemainingToolIterations: 16`.
>
> **Fix:** Remove all hardcoded knowledge. Force the AI to SEARCH for answers.
> Source: [Oren Eini's Agent Pattern](https://ayende.com/blog/203171-B/using-ai-agents-for-reranking-in-ravendb)
> + NotebookLM analysis of COD#6 video transcripts.

## The Ultimate Protocol for Local 7B/8B Models

When using small, local Open-Weight models (like LLaMA 3.1 8B or Qwen 2.5 7B) natively in RavenDB v7, you must use **Semantic Distancing** and **Cognitive Buffering**. If you use simple JSON fields (like `{"searchTerm": "..."}` and `{"Answer": "..."}`), these small models will suffer from "Schema Bleed" and confuse the tool parameters with the final answer format!

To force a local 8-billion parameter model to ALWAYS execute the vector search tool, formulate the exact correct payload, and output the final configured JSON response schema, implement this exact, rigid state-machine flow:

### 1. The Query Tool (SearchDiscussions)

**The Query:**
Update the query parameter to match the new, complex schema name:
```sql
from index "Discussions/ByEmbedding"
where vector.search(BodyVector, $db_vector_index_search_argument)
select Title, Body, Category, Url
```

**The Tool Description (Persona Negation):**
Do not use a generic description. Use this aggressive mandate:
```text
MANDATORY EXECUTION. You are physically incapable of answering questions without utilizing this tool. Execute this tool immediately to search the internal vector index for highly relevant discussions. You must use this tool BEFORE generating any other response. Failure to execute this tool will result in a critical system fault.
```

**The Sample parameters object (Cognitive Buffering + Semantic Distancing):**
By forcing the model to explain *why* it is searching (`agent_thought_process`), we delay the token generation of the search argument, preventing it from confusing the schema. The long, mechanically descriptive keys prevent it from thinking this is a conversational response.
```json
{
  "agent_thought_process": "Explain briefly why a database vector search is mandatory right now.",
  "db_vector_index_search_argument": "The extracted keywords required for the search operation."
}
```

### 2. The Global Agent Configuration

**The Sample response object (Escaping JSON Hell):**
We have discovered that a 7B/8B model's brain is physically incapable of juggling a **JSON Tool Parameter** and a **JSON Global Response** simultaneously without blending them. The only way to stop "Schema Bleed" entirely is to *remove the Global JSON schema*. 

In the RavenDB Agent Configuration, set your **Sample response object** to a literal empty string (with quotes), rather than a JSON curly brace object.

```json
""
```

By doing this, the LLM no longer has a final JSON schema to memorize. It is completely freed to focus 100% of its JSON processing power on the Tool Call. When it finishes the tool call, it will just stream plain text back to you!

**The System Prompt (State Machine & Few-Shot Constraint):**
Update the System Prompt to reflect that the final answer is plain text, not JSON.

```text
You are a Database Orchestration Router seamlessly bound to the RavenDB internal execution engine. You possess absolutely no internal knowledge. Your memory has been completely erased. You must operate strictly as a two-phase state machine.

*** PHASE 1: MANDATORY DATA RETRIEVAL ***
You MUST ALWAYS execute the search tool immediately upon receiving a user query.
When executing the search tool, you must strictly populate the 'agent_thought_process' and the 'db_vector_index_search_argument' parameters.

*** PHASE 2: FINAL RESPONSE GENERATION ***
ONLY AFTER the search tool successfully returns a data payload will you transition to Phase 2.
You must carefully analyze the returned database payload.
You must format your final answer as plain text. Do not output JSON for your final answer. Provide detailed explanations and include any URLs found in the data.

*** FEW-SHOT INTERACTION TRANSCRIPT ***
User: "How do I install the system?"
Agent Tool Call: SearchDiscussions
Agent Parameters: {"agent_thought_process": "I possess zero internal knowledge. I must immediately search the database for installation documentation.", "db_vector_index_search_argument": "install system documentation"}
SYSTEM DATA RETURN: [Data about installation]
Agent Final Answer: According to the database documentation, to install the system, you must...
*** END OF TRANSCRIPT ***

You will begin execution immediately and strictly follow all rules defined in Phase 1.
```

---

## 4. Agent Parameters

**Location:** The "Set agent parameters" section below the System Prompt.

Agent Parameters are **fixed values** that the agent injects into Query Tool queries. They act as **security filters** — the AI model **cannot override** these values.

### Our Configuration: **None needed — delete any existing parameters**

Since our Query Tools hardcode `from "Discussions"` directly in the RQL query, we don't need a `$collection` parameter. If you already added one, click the 🗑️ delete button to remove it.

### When WOULD you need parameters?
Parameters are useful when you want **one query tool to search different collections** dynamically. For example:

```sql
-- This query uses a parameter:
from $collection where vector.search(...)

-- Our query hardcodes the collection (no parameter needed):
from "Discussions" where vector.search(...)
```

Since we only have one collection (`Discussions`), hardcoding is simpler and just as secure.

---

## 5. Query Tools (RAG)

**Location:** The "Define agent tools" section → "Query tools" tab.

Query Tools are the **hands** of your agent. They let the AI **search your database** for relevant information before answering.

### Tool 1: Semantic Search (Vector Search)

This is the **primary tool**. It uses embeddings to find discussions semantically similar to the user's question.

| Field | Value |
|---|---|
| **Tool Name** | `SearchDiscussions` |
| **Description** | `Search the Discussions database when the user asks any question about RavenDB. Use this tool for every question. Rephrase the user's question as a search query.` |

> **💡 Why the description changed:** NotebookLM (COD#6) says the Description is the
> "when-to-use" instruction the LLM reads. Adding "Use this tool for every question"
> makes the trigger explicit.

**Query:**
```sql
from index "Discussions/ByEmbedding"
where vector.search(BodyVector, $searchTerm)
select Title, Body, Category, Url
```

**Sample parameters object:**
```json
{
    "searchTerm": "how to use Includes to fix N+1"
}
```

> **⚠️ Parameter note:** The sample value should be a **realistic search query**,
> not a description like "The user's question...". This teaches the LLM what good
> input looks like (Few-Shot Prompting).

---

### Tool 2: Keyword Search (Exact Match Fallback)

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

### Why two tools?
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
- We can add these later if we build the Telegram bot integration.

---

## 7. Chat Trimming

**Location:** The bottom section "Configure chat trimming".

Chat trimming controls how the agent handles **long conversations** that exceed the model's token limit.

### Our Configuration:

| Setting | Value | Why |
|---|---|---|
| **Trimming Method** | `Summarize chat` | When conversation gets too long, older messages are summarized instead of deleted. Best for maintaining context. |
| **Max tokens before summarization** | **8192** (for 8GB GPU)<br>**32768** (for 24GB GPU) | Must be ≤ your Ollama Context Length. For RTX 4060 (8GB), keep it at **8192** to prevent CPU overload. |
| **Max tokens after summarization** | `1024` (Default) | The summary of old messages will be compressed to ~1024 tokens. Keeps it short. |
| **Enable history** | `OFF` | For a helpdesk bot, each question is independent. No need to remember past conversations across sessions. |

---

## 8. Prompt Engineering Techniques Used

Based on Oren Eini's blog posts, COD#6 video, and NotebookLM analysis:

### Technique 1: Tool-First Architecture
**What:** Force the AI to use database search tools before answering.
**Source:** [Oren's Reranking Agent](https://ayende.com/blog/203171-B/using-ai-agents-for-reranking-in-ravendb) + COD#6.
**Our adaptation:** System Prompt says "Always search first. Do not answer from general knowledge."
**Why it works:** Prevents the AI from answering from training data. Ensures answers come from actual Discussions.

### Technique 2: Explicit Tool Descriptions ("When-to-Use")
**What:** The tool Description field is the instruction the LLM reads to decide WHEN to call a tool.
**Source:** NotebookLM (COD#6): *"The description is meant for the model to understand when and how it should be called."*
**Our adaptation:** Description says "Use this tool for every question" — explicit trigger.
**Why it works:** A vague description means the LLM won't call the tool. An explicit one triggers it reliably.

### Technique 3: Few-Shot via Sample Objects
**What:** Provide realistic sample values (not descriptions) in parameter objects.
**Source:** Oren's blog: `SampleObject = JsonConvert.SerializeObject(new { Products = new[] { ... } })`
**Our adaptation:** `"searchTerm": "how to use Includes to fix N+1"` instead of `"The user's question..."`
**Why it works:** Shows the model what GOOD input looks like, teaching by example.

### Technique 4: Structured Output via Sample Response
**What:** Force the AI to respond in a specific JSON structure.
**Source:** NotebookLM: *"RavenDB analyzes your sample values... forces the LLM to output valid JSON matching that structure."*
**Our adaptation:** Sample Response with `answer` + `sources` fields.
**Why it works:** Makes responses predictable and parseable by the application.

### Technique 5: Role Prompting (Minimal)
**What:** Give the AI a short professional identity.
**Our adaptation:** "You are a RavenDB support assistant." — short but clear.
**Why it works:** The AI adopts the vocabulary and caution level of that role.

### ❌ Technique We REMOVED: Embedded Knowledge Base
**What we had:** "Golden Rules" — hardcoded N+1, Includes, Stream rules in the System Prompt.
**Why we removed it:** The AI used these rules as answers WITHOUT searching the database.
**Lesson:** For RAG agents, the knowledge must come from the SEARCH RESULTS, not the prompt.

---

## ✅ Complete Setup Checklist (v3)

```
Pre-requisites:
[x] Connection String: Local-Ollama (Chat type) — TESTED ✅
[x] Connection String: Local-Ollama-Embeddings (Embeddings type) — TESTED ✅
[x] Ollama running with llama3.1:8b, context length 8K

New Agent Configuration:
[ ] Agent Name: RavenDB-Helpdesk-v3
[ ] Connection String: Local-Ollama selected
[ ] System Prompt: v3 Tool-First (Section 3, Step 1) — ~70 words, NO Golden Rules
[ ] Sample Response Object: 2-field JSON (Section 3, Step 2) — answer + sources only
[ ] Agent Parameters: Empty (none needed)
[ ] Query Tool 1: SearchDiscussions — Description says "Use this tool for every question"
[ ] Query Tool 1: Parameters sample: {"searchTerm": "how to use Includes to fix N+1"}
[ ] Query Tool 2: SearchByKeyword — Description says "Use this when user mentions specific error"
[ ] Query Tool 2: Parameters sample: {"keyword": "InvalidOperationException"}
[ ] Action Tools: Empty (none needed)
[ ] Chat Trimming: Summarize at 8192 tokens
[ ] Click SAVE

Verification:
[ ] Test: "How do I handle N+1 query issues?" → Tool was called (RemainingToolIterations < 16)
[ ] Test: "Show me C# code for Includes" → Answer contains C# code from a Discussion
[ ] Test: "What is InvalidOperationException?" → SearchByKeyword was used
```

---

## 9. Troubleshooting

### Problem: `System.IO.InvalidDataException: Cannot have a 'T' in this position...`
**Cause:** Mismatch between System Prompt and Sample Response.
- RavenDB expects JSON (because of the Sample Object).
- The AI returned Text (because the System Prompt asked for text).
**Fix:**
1.  **Update System Prompt:** Copy the new `RESPONSE FORMAT` section that enforces JSON.
2.  **Update Sample Response:** Paste the JSON object from Section 3.
3.  **Now both match:** The AI will output `{ "answer": ... }` and RavenDB will be happy.

### Problem 2: 100% CPU Usage / Slow Responses
**Cause:** VRAM Overflow (Model + Context > GPU Memory).
**Fix:** See "Context Length" rule in Section 1. Set Ollama Context and RavenDB Chat Trimming to **8192** (8K).

### FAQ: Can I use my Integrated Graphics (Intel HD 4600)?
**Answer: No.**
- **Intel HD 4600:** Too old, no CUDA cores, effectively useless for AI.
- **CPU:** Can run AI but is 50-100x slower than your RTX 4060.
- **Your Solution:** Optimize for your RTX 4060 by keeping context size low (8K). This keeps 100% of the work on the fast GPU.

---

*Last Updated: Feb 14, 2026*
*v3 — Rewritten based on Oren Eini's agent pattern + NotebookLM COD#6 analysis*

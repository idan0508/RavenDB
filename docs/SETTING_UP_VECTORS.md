# Setting Up Embeddings and Vector Search

To make the AI Agent genuinely intelligent, it must perform **Semantic Search**. Unlike normal search (which looks for exact words), Semantic Search finds the *meaning* of words using **Vectors** (arrays of numbers representing text).

This guide covers the embedding generation and vector search workflow using **Azure OpenAI**.

**Updated:** April 19, 2026 — Migrated from Ollama to Azure AI.

---

## 1. Connection Strings

Before creating embedding tasks, ensure these connection strings exist in RavenDB Studio → AI Hub → AI Connection Strings:

| Name | Type | Model | Endpoint |
|---|---|---|---|
| `Azure-Chat` | Chat | `gpt-4.1-mini` | `https://idan-ravendb-ai-us2.openai.azure.com/` |
| `Azure-Text-Embeddings` | Text Embeddings | `text-embedding-3-small` | Same endpoint |

Both connection strings use the **Azure OpenAI** connector with your API key.

---

## 2. Collection and Field Conventions

Use the correct source fields for each collection:

| Collection | Recommended Embedding Field | Chunking Method | Reason |
|---|---|---|---|
| `Documentation_Sitemaps` | `SearchableContent` | MarkDownSplitParagraphs | Already normalized for retrieval (title + sections + content). Avoids noise. |
| `Discussions` | `Body` | PlainTextSplit | Freeform text content. Optionally also embed `Title`. |
| `GoogleGroupMessages` | `Body` (or `SearchableContent` if preprocessed) | PlainTextSplit | Raw email text. May benefit from preprocessing to remove noise. |

### Why `SearchableContent` for Documentation?

This field is specifically constructed for embedding quality:
- It combines `Title` + `Sections` + `Body` into a single text
- It preserves deep context that would be lost if embedding `Body` alone
- It avoids noise from navigation elements and boilerplate

---

## 3. Creating Embedding Tasks

Navigate to **AI Hub** → **Embeddings Generation** in RavenDB Studio.

### Task A: Documentation

| Setting | Value |
|---|---|
| Task Name | `documentations` |
| Collection | `Documentation_Sitemaps` |
| Connection String | `Azure-Text-Embeddings` |
| Task State | Enabled |
| Source Path | `SearchableContent` |
| Chunking Method | MarkDownSplitParagraphs |
| Max Tokens per Chunk | 2048 |
| Overlap Tokens | 0 |
| Quantization | Single (no quantization) |
| Embeddings Cache Expiration | 90 days |

### Task B: Discussions

| Setting | Value |
|---|---|
| Task Name | `discussions` |
| Collection | `Discussions` |
| Connection String | `Azure-Text-Embeddings` |
| Task State | Enabled |
| Source Path | `Body` |
| Chunking Method | PlainTextSplit |
| Max Tokens per Chunk | 2048 |
| Overlap Tokens | 0 |

### Task C: Google Groups (Pending)

| Setting | Value |
|---|---|
| Task Name | `google-groups` |
| Collection | `GoogleGroupMessages` |
| Connection String | `Azure-Text-Embeddings` |
| Task State | Enabled |
| Source Path | `Body` |
| Chunking Method | PlainTextSplit |
| Max Tokens per Chunk | 2048 |
| Overlap Tokens | 0 |

> **Note:** Before creating this task, inspect a sample of GoogleGroupMessages documents.
> If the `Body` field contains excessive noise (email signatures, quoted replies),
> consider creating a preprocessing script to generate a clean `SearchableContent` field first.

---

## 4. Creating Semantic Search Indexes

### Option A: Per-Collection Indexes (Development)

Create separate indexes in RavenDB Studio → Indexes → New Index:

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

**Index: `KnowledgeBase/SemanticSearch/GoogleGroups`** (when ready)
```csharp
docs.GoogleGroupMessages.Select(doc => new {
    Title = doc.Title,
    Body = doc.Body,
    Category = "Google Groups",
    Url = doc.Url,
    Source = "Google Groups",
    BodyVector = LoadVector("Body", "google-groups")
})
```

### Option B: Unified Multi-Map Index (Production)

Deploy the `KnowledgeBase_SemanticSearch` index from C# code by running:

```powershell
cd HelpdeskAgent
dotnet run
```

This creates a single index that maps all three collections. The AI Agent queries this one index and gets results from any source, ranked by semantic relevance.

---

## 5. Validation Checklist

After task creation and index deployment:

1. **Verify vectors exist:** Open a document in each collection and check for vector data in its metadata.
2. **Check task status:** AI Hub → Embeddings Generation → verify each task shows "Enabled" and has processed documents.
3. **Check index status:** Indexes page → verify each index is not stale (no yellow warning).
4. **Run test query:** Use Studio's query editor:

```sql
from index 'KnowledgeBase/SemanticSearch/Documentations'
where vector.search(BodyVector, "how to configure session querying")
limit 3
```

5. **Test agent:** Ask a question through the AI Agent or Telegram bot and verify the response includes relevant results with source URLs.

---

## 6. Reset Strategy (If Vectors Are Polluted)

If embeddings were generated with wrong model/task settings:

1. In RavenDB Studio, identify the problematic embedding task.
2. Delete the task.
3. Keep source collections (documents) intact — only embeddings are regenerated.
4. Recreate the embedding task with corrected settings.
5. Enable "Regenerate embeddings for all documents" checkbox.
6. Wait for the task to reprocess all documents.
7. Verify dependent indexes update automatically.

> **Important:** Never delete source document collections unless absolutely necessary. Only reset the embedding outputs.

---

## 7. Cost Estimation

| Collection | Est. Tokens | Cost (text-embedding-3-small @ $0.02/1M tokens) |
|---|---|---|
| Documentation_Sitemaps | ~10M | $0.20 |
| Discussions | ~1M | $0.02 |
| GoogleGroupMessages | ~56M | $1.12 |
| **Total** | **~67M** | **$1.34** |

Well within the ~$100 Azure credit budget.

---

## 8. Common Failure Modes

| Issue | Cause | Fix |
|---|---|---|
| Wrong collection name | ID prefix / collection name mismatch | Ensure document IDs start with collection name |
| Weak search results | Wrong source path for embedding | Embed `SearchableContent` for docs, `Body` for others |
| Inconsistent retrieval | Mixed old/new vectors | Reset and regenerate all embeddings for that collection |
| Index errors | Embedding task name doesn't match `LoadVector()` call | Task identifier must match the second arg of `LoadVector()` |
| Azure API errors | Token limit exceeded | Set max tokens per chunk to 2048 in task config |

---

*For the full system architecture, see [ARCHITECTURE.md](../ARCHITECTURE.md).*  
*For AI Agent configuration details, see [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md).*

# Embeddings and Separate Semantic Search Indexes

**Updated:** June 18, 2026

The helpdesk agent uses three independent embedding tasks and three independent static indexes. Do not replace them with a unified multi-map index; the agent tools intentionally target the three names below.

## AI connection string

Create `Azure-Text-Embeddings` in RavenDB Studio with the Azure OpenAI `text-embedding-3-small` deployment.

## Embedding tasks

| Task identifier | Collection | Source path | Recommended chunking |
|---|---|---|---|
| `documentations` | `Documentation_Sitemaps` | `SearchableContent` | Markdown paragraphs |
| `discussions` | `Discussions` | `Body` | Plain text |
| `groups` | `GoogleGroupMessages` | `Body`, `Title` | Plain text |

The task identifiers must exactly match the second argument passed to `LoadVector(...)` in the index definitions.

## Deployed indexes

Running `dotnet run --project HelpdeskAgent` deploys:

- `KnowledgeBase/SemanticSearch/Documentations`
- `KnowledgeBase/SemanticSearch/Discussions`
- `KnowledgeBase/SemanticSearch/GoogleGroups`

The definitions are stored in `HelpdeskAgent/Indexes/`.

### Documentation map

```csharp
from doc in docs.Documentation_Sitemaps
select new
{
    doc.Title,
    Body = doc.SearchableContent,
    doc.Version,
    doc.Category,
    doc.Url,
    Source = "Official Documentation",
    BodyVector = LoadVector("SearchableContent", "documentations")
}
```

### Discussions map

```csharp
from doc in docs.Discussions
select new
{
    doc.Title,
    Body = doc.SearchableContent ?? doc.Body,
    Answer = doc.Answer != null ? doc.Answer.Body : null,
    doc.IsAnswered,
    doc.UpdatedAt,
    doc.Url,
    Source = "GitHub Discussions",
    BodyVector = LoadVector("Body", "discussions")
}
```

### Google Groups map

```csharp
from doc in docs.GoogleGroupMessages
select new
{
    doc.Title,
    doc.Body,
    doc.CreatedAt,
    doc.Author,
    doc.Url,
    Source = "Google Groups",
    BodyVector = LoadVector("Body", "groups"),
    TitleVector = LoadVector("Title", "groups")
}
```

## Validation

Run one query against each index in Studio:

```rql
from index 'KnowledgeBase/SemanticSearch/Documentations'
where vector.search(BodyVector, "session includes related documents")
limit 3
```

Change the index name to test Discussions and Google Groups. Before testing the agent, verify that every index is non-stale and returns fields such as `Title`, `Body`, and `Url`.

## Common failures

| Failure | Cause |
|---|---|
| Tool returns no results | The tool references an index name that was not deployed |
| Index error around `LoadVector` | Embedding task identifier or source path does not match |
| Documentation quality is weak | `Body` was embedded instead of `SearchableContent` |
| Google Groups tool fails | The `groups` embedding task identifier or its `Body`/`Title` paths do not match |
| Agent answers without evidence | Tool failed, prompt contract is stale, or the client is not enforcing `AnswerStatus` |

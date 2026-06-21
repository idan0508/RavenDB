# RavenDB Helpdesk Agent Deployment

This project deploys the reproducible RavenDB configuration for the grounded helpdesk agent:

- three separate semantic-search indexes;
- three source-specific query tools;
- an evidence-first system prompt;
- structured `Grounded`, `NeedsClarification`, and `NotFound` responses.

## Prerequisites

In `HelpdeskDB`, configure:

- `Azure-Chat` as a Chat AI connection string;
- `Azure-Text-Embeddings` as a Text Embeddings connection string;
- embedding task identifiers `documentations`, `discussions`, and `groups`.

See `docs/SETTING_UP_VECTORS.md` for exact collections and source paths.

## Deploy

```powershell
$env:RAVENDB_URL = "http://127.0.0.1:8080"
$env:RAVENDB_DATABASE = "HelpdeskDB"
dotnet run --project HelpdeskAgent
```

By default this creates or updates only:

- AI Agent identifier `ravendb-helpdesk-grounded-v1`

It reuses the three existing indexes and does not overwrite AI connection strings or secrets.

To explicitly create or update the index definitions:

```powershell
dotnet run --project HelpdeskAgent -- --indexes
```

## Verify

In RavenDB Studio:

1. Check all three indexes are non-stale.
2. Test each vector query independently.
3. Open AI Hub → AI Agents → `RavenDB Helpdesk Grounded v1`.
4. Ask one known question and one unsupported question.

The known answer must include retrieved references. The unsupported answer must say that the knowledge base was searched and no reliable answer was found.

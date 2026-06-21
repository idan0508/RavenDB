# RavenDB Helpdesk AI Agent Configuration

**Updated:** June 18, 2026

This is the reproducible code configuration for the working RavenDB Studio agent shown in the project screenshot. The production design uses three separate semantic-search indexes and three separate query tools.

## Agent

| Setting | Value |
|---|---|
| Name | `RavenDB Helpdesk Grounded v1` |
| Identifier | `ravendb-helpdesk-grounded-v1` |
| State | Enabled |
| Chat connection | `Azure-Chat` |
| Response fields | `Answer`, `AnswerStatus`, `ReferenceUrls` |
| Maximum model iterations | 8 |

The source of truth is `HelpdeskAgent/Agent/HelpdeskAssistant.cs`.

## Response contract

`AnswerStatus` must be one of:

- `Grounded`: the answer is supported by retrieved evidence and has at least one exact documentation or GitHub Discussion URL.
- `NeedsClarification`: a version or other essential detail is required before a reliable search can be completed.
- `NotFound`: the knowledge base did not contain sufficiently relevant evidence.

Example:

```json
{
  "Answer": "The answer supported by retrieved RavenDB documentation.",
  "AnswerStatus": "Grounded",
  "ReferenceUrls": [
    "https://docs.ravendb.net/article-page/7.2/csharp/client-api/session/querying/how-to-query"
  ]
}
```

The Telegram client fails closed: a `Grounded` answer without an allowed source URL is replaced with the standard not-found response.

## Required retrieval order

For every technical question, the agent must:

1. Call `SearchDocumentation`.
2. Call `SearchDiscussions` when documentation is incomplete or the question is about troubleshooting.
3. Call `SearchGoogleGroups` only as a historical fallback.
4. Return `NotFound` instead of using model memory when retrieval does not support an answer.

## Query tools

### SearchDocumentation

```rql
from index 'KnowledgeBase/SemanticSearch/Documentations'
where vector.search(BodyVector, $query)
limit 5
```

### SearchDiscussions

```rql
from index 'KnowledgeBase/SemanticSearch/Discussions'
where vector.search(BodyVector, $query)
limit 5
```

### SearchGoogleGroups

```rql
from index 'KnowledgeBase/SemanticSearch/GoogleGroups'
where vector.search(BodyVector, $query) or vector.search(TitleVector, $query)
limit 5
```

Google Groups results may provide historical context, but their URLs are not returned. A response is not considered grounded unless documentation or a GitHub Discussion also supports it.

For every query tool, `AllowModelQueries` must be `true`. `AddToInitialContext` remains `false` because `$query` must be supplied by the model. Setting both values to `false` disables the tool entirely.

## Why separate indexes

The three-index design matches the configuration that worked in RavenDB Studio and avoids the regression caused by querying names that were never deployed. It also gives the model an explicit source priority and makes each retrieval path independently testable.

## Not-found behavior

When no reliable evidence is found, the user receives:

> I searched the RavenDB knowledge base but could not find a reliable answer to this question.

The follow-up recommends:

- official documentation for normal product/API questions;
- GitHub Discussions for errors, edge cases, unclear behavior, or scenarios that need RavenDB team/community input.

## Validation checklist

- All three embedding generation tasks are enabled.
- All three indexes exist and are non-stale.
- Each tool query returns useful results when tested directly in Studio.
- A known question returns `Grounded` with real URLs.
- A nonsense or unsupported question returns `NotFound`.
- A version-dependent question without a version returns `NeedsClarification`.
- Telegram rejects non-HTTPS, non-RavenDB-docs, and non-RavenDB-Discussion URLs.

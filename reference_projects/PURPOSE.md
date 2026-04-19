# Reference Projects — Purpose & Context

## What Is This Folder?

This folder contains **reference implementation projects** provided by the RavenDB team. These are NOT part of our Helpdesk Agent codebase — they serve as working examples that we studied and adapted patterns from.

---

## PropertySphere (`samples.properties/`)

**PropertySphere** is a complete Property Management System demo application built by **Oren Eini** (CEO of RavenDB / Hibernating Rhinos). It was provided to our team as a reference implementation demonstrating RavenDB's advanced features.

### What We Learned From It

| Pattern | PropertySphere Implementation | Our Adaptation |
|---|---|---|
| **AI Agent Configuration** | `PropertyAgent.cs` — configures agent with query tools, system prompt, and response schema | `HelpdeskAssistant.cs` — same pattern adapted for helpdesk use case |
| **Telegram Bot Integration** | `TelegramPollingService.cs` — processes messages, manages conversations, calls agent | `TelegramBot/Program.cs` — same architecture for our helpdesk bot |
| **Conversation Management** | `GetConversationId()` — generates daily conversation IDs per chat | Adopted the same `chats/{chatId}/{date}` pattern |
| **Agent Response Handling** | `RunAsync<T>()` with typed response objects | Our `AgentReply` class with `Answer` + `Sources` |
| **Markdown Fallback** | Try Markdown parse mode, catch and fall back to plain text | Identical implementation in our bot |

### Key Files Worth Studying

- `Program.cs` — Full ASP.NET Core application setup with RavenDB integration
- `Services/PropertyAgent.cs` — Agent definition with query tools and action tools
- `Services/TelegramPollingService.cs` — Telegram bot with RavenDB AI Agent integration
- `Services/PropertyDescriptionGenerator.cs` — GenAI ETL task for image processing
- `Services/PhotoSubscription.cs` — RavenDB Data Subscriptions for reactive notifications
- `Indexes/` — Spatial and dynamic index examples
- `QUICKSTART.md` — Setup instructions for the PropertySphere demo
- `SUMMARY.md` — Overview of all RavenDB features demonstrated

### RavenDB Features Demonstrated

- AI Agent with RAG (query tools + action tools)
- GenAI ETL (image analysis with OpenAI)
- Data Subscriptions (reactive document processing)
- Spatial Indexing (location-based queries)
- Time Series Data (utility usage tracking)
- Dynamic Indexing

### Important Note

This folder contains its own `.git` directory — it was originally a standalone repository. It is included in our project as a **read-only reference**. Do not modify files in this folder.

---

*PropertySphere was provided to our team by Oren Eini (RavenDB CEO) as part of our final-year project supervision.*

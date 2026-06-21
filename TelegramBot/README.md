# Telegram Bot for RavenDB AI

This project is the Telegram client for the RavenDB Helpdesk AI Agent.

The client applies a final response safety check. It only displays `Grounded` answers that contain at least one HTTPS source from `docs.ravendb.net` or an exact `github.com/ravendb/ravendb/discussions/{number}` URL. Invalid, missing, or unsupported evidence is replaced by the standard not-found guidance.

## Changing the Connected AI Agent

If you have created a new AI Agent in RavenDB (for example, to test new system prompts) and want to link this Telegram bot to it, you need to point the bot to the new `AgentName` (which is the Identifier defined in the agent's C# configuration).

1. Open `appsettings.json` in this folder.
2. Under `"RavenDB"`, change the `"AgentName"` value to match your desired Agent's identifier. 

**Example:**
```json
{
    "RavenDB": {
        "Urls": [
            "http://100.68.0.72:8080"
        ],
        "Database": "HelpdeskDB",
        "AgentName": "ravendb-helpdesk-grounded-v1"
    },
    "Telegram": { ... }
}
```

3. Save the file.
4. Open a terminal, navigate to this folder (`cd C:\Users\Ron\Documents\GitHub\RavenDB\TelegramBot`) and start the bot:
   ```bash
   dotnet run
   ```

# Telegram Bot for RavenDB AI

This project is the Telegram Bot client that connects to the RavenDB Helpdesk AI Agent.

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
        "AgentName": "ravendb-helpdesk-ai-2" // <-- Change this to test the new agent!
    },
    "Telegram": { ... }
}
```

3. Save the file.
4. Open a terminal, navigate to this folder (`cd C:\Users\Ron\Documents\GitHub\RavenDB\TelegramBot`) and start the bot:
   ```bash
   dotnet run
   ```

# RavenDB Helpdesk Agent Configuration

This project contains the configuration and logic to deploy the "RavenDB - HelpDesk AI" Agent directly into your RavenDB database using the "Code as Configuration" pattern. 

## How to Run

1. Open your terminal.
2. Navigate to the project's root folder:
   ```bash
   cd C:\Users\Ron\Documents\GitHub\RavenDB\HelpdeskAgent
   ```
3. Run the deployment script:
   ```bash
   dotnet run
   ```

You will see the console log `Helpdesk Assistant registered successfully`. If you open your RavenDB Studio under the **AI Agents** section, you will see your new Agent fully configured!

## Creating Multiple Agents

If you want to experiment with different agent behaviors simultaneously (e.g., testing different system prompts), you can deploy a *new* agent rather than overwriting the existing one.

To do this:
1. Open `Agent/HelpdeskAssistant.cs`
2. Modify the `AgentId` constant to a new identifier (e.g., `"ravendb-helpdesk-ai-2"`)
3. Run `dotnet run` again. 

You will now have two distinct agents side-by-side in your RavenDB Studio.

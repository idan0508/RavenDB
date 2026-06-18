using System;
using System.Threading.Tasks;
using Raven.Client.Documents;
using Raven.Client.Documents.Operations.AI;
using Raven.Client.Documents.Operations.ConnectionStrings;
using Raven.Client.ServerWide.Operations;
using HelpdeskAgent.Model;
using HelpdeskAgent.Indexes;
using HelpdeskAgent.Agent;

namespace HelpdeskAgent
{
    class Program
    {
        static async Task Main(string[] args)
        {
            var ravenDbUrl = Environment.GetEnvironmentVariable("RAVENDB_URL")
                ?? "http://100.68.0.72:8080";
            var databaseName = Environment.GetEnvironmentVariable("RAVENDB_DATABASE")
                ?? "HelpdeskDB";

            Console.WriteLine($"Connecting to RavenDB at {ravenDbUrl} (Database: {databaseName})...");

            using var store = new DocumentStore
            {
                Urls = new[] { ravenDbUrl },
                Database = databaseName
            };
            store.Initialize();

            // 0. AI Connection String Configuration
            var aiApiKey = Environment.GetEnvironmentVariable("AI_API_KEY");
            if (!string.IsNullOrWhiteSpace(aiApiKey) && aiApiKey != "YOUR_API_KEY_HERE")
            {
                var aiConnection = new AiConnectionString
                {
                    Name = "Azure-Chat",
                    Identifier = "azure-chat",
                    OpenAiSettings = new OpenAiSettings
                    {
                        ApiKey = aiApiKey,
                        Endpoint = "YOUR_ENDPOINT_HERE", // TODO: Replace with your actual endpoint
                        Model = "YOUR_DEPLOYMENT_HERE"   // TODO: Replace with your actual deployment/model name
                    },
                    ModelType = AiModelType.Chat
                };

                store.Maintenance.Send(new PutConnectionStringOperation<AiConnectionString>(aiConnection));
                Console.WriteLine("AI Connection String registered successfully.");
            }
            else
            {
                Console.WriteLine("AI Connection String skipped. (Set AI_API_KEY to deploy it automatically).");
            }

            // 1. Create Indexes
            Console.WriteLine("Deploying Indexes...");
            new KnowledgeBase_SemanticSearch().Execute(store);

            // 2. Create Agent
            Console.WriteLine("Deploying Agent...");
            try
            {
                HelpdeskAssistant.Create(store);
                Console.WriteLine("Helpdesk Assistant registered successfully.");
            }
            catch (Exception e)
            {
                Console.WriteLine($"Error deploying agent: {e.Message}");
                Console.WriteLine(e.StackTrace);
            }

            if (args.Length > 0 && args[0] == "--import-mbox")
            {
                var path = args.Length > 1
                    ? args[1]
                    : Environment.GetEnvironmentVariable("MBOX_PATH")
                        ?? @"C:\Users\Ron\Downloads\ravendb-googlegroups.mbox\ravendb-googlegroups.mbox";
                await MboxImporter.ImportAsync(store, path);
            }

            Console.WriteLine("\n--- Configuration Complete ---");
            Console.WriteLine("You can now go to RavenDB Studio -> AI Agents and use the 'RavenDB - HelpDesk AI'.");
        }
    }
}

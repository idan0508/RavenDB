using System;
using System.Threading.Tasks;
using Raven.Client.Documents;
using HelpdeskAgent.Model;
using HelpdeskAgent.Indexes;
using HelpdeskAgent.Agent;

namespace HelpdeskAgent
{
    class Program
    {
        static async Task Main(string[] args)
        {
            var ravenDbUrl = "http://127.0.0.1:8080";
            var databaseName = "HelpdeskDB";

            Console.WriteLine($"Connecting to RavenDB at {ravenDbUrl} (Database: {databaseName})...");

            using var store = new DocumentStore
            {
                Urls = new[] { ravenDbUrl },
                Database = databaseName
            };
            store.Initialize();



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
                var path = @"C:\Users\Ron\Downloads\ravendb-googlegroups.mbox\ravendb-googlegroups.mbox";
                await MboxImporter.ImportAsync(store, path);
            }

            Console.WriteLine("\n--- Configuration Complete ---");
            Console.WriteLine("You can now go to RavenDB Studio -> AI Agents and use the 'RavenDB Expert Assistant'.");
        }
    }
}

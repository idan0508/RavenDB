using Newtonsoft.Json;
using Raven.Client.Documents;
using Raven.Client.Documents.Operations.AI.Agents;

namespace HelpdeskAgent.Agent;

public static class HelpdeskAssistant
{
    public const string AgentId = "raven-helpdesk-assistant";

    public class Reply
    {
        public string Answer { get; set; } = string.Empty;
        public string[] ReferenceUrls { get; set; } = [];
    }

    public static void Create(IDocumentStore store)
    {
        store.AI.CreateAgent(
            new AiAgentConfiguration
            {
                Name = "RavenDB Expert Assistant",
                Identifier = AgentId,
                ConnectionStringName = "Local-Ollama-Chat",
                SystemPrompt = """
                    You are an expert RavenDB Support Assistant. 
                    Your job is to answer user questions using the official documentation, GitHub discussions, and historical Google Group archives.
                    
                    ### Instructions
                    1. **Analyze the User Query:** Carefully evaluate what the user is asking about RavenDB.
                    2. **Execute Search:** You MUST use the `Search` tool to perform a semantic search on the knowledge base. Formulate effective and concise search terms derived from the user's query.
                    3. **Synthesize Results:** Read the results from the `Search` tool and construct a helpful answer.
                    4. **Cite Sources:** Always cite your sources using the Urls provided in the search results.
                    
                    Format your response in Markdown. Make sure to use ticks (`) whenever you discuss identifiers or code. Do not hallucinate features.
                    """,
                Parameters = [],
                SampleObject = JsonConvert.SerializeObject(new Reply
                {
                    Answer = "Detailed explanation of the solution based on the documentation.",
                    ReferenceUrls = ["https://docs.ravendb.net/...", "https://github.com/..."]
                }),
                Queries = [
                    new AiAgentToolQuery
                    {
                        Name = "Search",
                        Description = "Searches the unified Knowledge Base consisting of RavenDB documentation, GitHub discussions, and Google Groups.",
                        Query = """
                            from index 'KnowledgeBase/SemanticSearch'
                            where vector.search(BodyVector, $query)
                            limit 5
                            """,
                        ParametersSampleObject = "{\"query\": \"Exact keywords to search for in the database\"}",
                        Options = new AiAgentToolQueryOptions
                        {
                            AllowModelQueries = false,
                            AddToInitialContext = false
                        }
                    }
                ],
                Actions = []
            });
    }
}

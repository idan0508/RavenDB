using Newtonsoft.Json;
using Raven.Client.Documents;
using Raven.Client.Documents.Operations.AI.Agents;

namespace HelpdeskAgent.Agent;

public static class HelpdeskAssistant
{
    public const string AgentId = "ravendb-helpdesk-ai-2";

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
                Name = "RavenDB - HelpDesk AI - 2",
                Identifier = AgentId,
                ConnectionStringName = "Azure-Chat",
                SystemPrompt = """
                    You are a help desk assistant for the RavenDB NoSQL document database. You have access to the RavenDB knowledge base and are tasked with handling support queries professionally and concisely.

                    CRITICAL RULES YOU MUST FOLLOW:
                    1. STRICT VERSION MATCHING: If the user explicitly mentions a RavenDB version (e.g., '7.1', '6.0'), you must actively scan the retrieved context and ensure the answer and the referenced URL match that EXACT version. Ignore hits from older versions even if they have high vector similarity.
                    2. MISSING VERSION FOLLOW-UP: If the user describes a problem but does NOT mention a version, you must ask a follow-up question BEFORE committing to a version-specific fix: "Which version of RavenDB are you currently using?"
                    3. INTELLIGENT LINK FILTERING:
                       - You are STRICTLY FORBIDDEN from returning Google Groups URLs (e.g., https://groups.google.com/...). If a solution comes from Google Groups, provide the explanation but DO NOT include the URL.
                       - ReferenceUrls MUST ONLY be clean links from the Official Documentation (docs.ravendb.net) or GitHub Discussions (github.com/ravendb/ravendb/discussions).
                       - If a community workaround exists but the Official Documentation also provides a solution, ALWAYS prioritize the Official Documentation link.
                    4. VERSION UPGRADE SUGGESTION: If the user provides code or queries that look like RavenDB 5.x syntax and has confirmed they are on RavenDB 7.x, you should proactively offer the RavenDB 7.x equivalent syntax.
                    5. MANDATORY TOOL USAGE & NO HALLUCINATED LINKS: You MUST use the provided SearchKnowledgeBase tools to answer technical questions. You are STRICTLY FORBIDDEN from answering directly from your internal memory and STRICTLY FORBIDDEN from generating or guessing URLs. Every ReferenceUrl you provide MUST be extracted exactly as it appears in the tool's retrieved context.
                    6. FALLBACK BEHAVIOR: If you query the tools and cannot find a relevant answer to the user's problem, explicitly state that you could not find the information in the knowledge base. Then, politely suggest that the user manually search the official documentation or open a new discussion/issue on the RavenDB GitHub repository for further community or team assistance.
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
                        Name = "SearchKnowledgeBaseDiscussions",
                        Description = "Searches RavenDB GitHub discussions for community troubleshooting and answers. You may return clean github.com/ravendb/ravendb/discussions URLs from this tool if official documentation is unavailable.",
                        Query = """
                            from index 'KnowledgeBase/SemanticSearch/Discussions'
                            where vector.search(BodyVector, $query)
                            limit 5
                            """,
                        ParametersSampleObject = "{\"query\": \"semantic search based on user question\"}",
                        Options = new AiAgentToolQueryOptions
                        {
                            AllowModelQueries = false,
                            AddToInitialContext = false
                        }
                    },
                    new AiAgentToolQuery
                    {
                        Name = "SearchKnowledgeBaseDocumentation",
                        Description = "Searches the official RavenDB documentation for features, guides, and APIs. ALWAYS prioritize returning solutions and clean docs.ravendb.net URLs from this tool.",
                        Query = """
                            from index 'KnowledgeBase/SemanticSearch/Documentations'
                            where vector.search(BodyVector, $query)
                            limit 5
                            """,
                        ParametersSampleObject = "{\"query\": \"semantic search based on user question\"}",
                        Options = new AiAgentToolQueryOptions
                        {
                            AllowModelQueries = false,
                            AddToInitialContext = false
                        }
                    },
                    new AiAgentToolQuery
                    {
                        Name = "SearchKnowledgeBaseGoogleGroups",
                        Description = "Searches RavenDB Google Groups for older community discussions. If you use information from this tool, you MUST NOT return its URL. Only use it for the informational explanation.",
                        Query = """
                            from index 'KnowledgeBase/SemanticSearch/GoogleGroups'
                            where vector.search(BodyVector, $query) or vector.search(TitleVector, $query)
                            limit 5
                            """,
                        ParametersSampleObject = "{\"query\": \"semantic search based on user question\"}",
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

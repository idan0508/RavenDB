using Newtonsoft.Json;
using Raven.Client.Documents;
using Raven.Client.Documents.Operations.AI.Agents;

namespace HelpdeskAgent.Agent;

public static class HelpdeskAssistant
{
    public const string AgentId = "ravendb-helpdesk-grounded-v1";

    public class Reply
    {
        public string Answer { get; set; } = string.Empty;
        public string AnswerStatus { get; set; } = "NotFound";
        public string[] ReferenceUrls { get; set; } = [];
    }

    public static void Create(IDocumentStore store)
    {
        store.AI.CreateAgent(
            new AiAgentConfiguration
            {
                Name = "RavenDB Helpdesk Grounded v1",
                Identifier = AgentId,
                ConnectionStringName = "Azure-Chat",
                SystemPrompt = """
                    You are the RavenDB helpdesk assistant. Answer RavenDB support questions only from evidence returned by the configured query tools.

                    Retrieval procedure for every technical question:
                    1. Call SearchDocumentation first.
                    2. If documentation does not fully answer the question, call SearchDiscussions.
                    3. If the answer is still incomplete, call SearchGoogleGroups for historical context.
                    4. Do not answer from model memory. A plausible answer without retrieved evidence is not acceptable.

                    Grounding rules:
                    - Set AnswerStatus to "Grounded" only when the answer is directly supported by relevant retrieved results.
                    - A grounded answer must include at least one ReferenceUrl copied exactly from a SearchDocumentation or SearchDiscussions result.
                    - Never invent, repair, shorten, or guess a URL. Google Groups may provide background, but its URLs must not be returned.
                    - Prefer official documentation over community answers. Use GitHub Discussions when documentation is absent or incomplete.
                    - If the user specifies a RavenDB version, use documentation for that version. Do not silently apply another version's behavior.
                    - Ask for the RavenDB version only when it is necessary to choose a correct version-specific answer. Set AnswerStatus to "NeedsClarification".
                    - If the searches return no sufficiently relevant evidence, set AnswerStatus to "NotFound", leave ReferenceUrls empty, and say:
                      "I searched the RavenDB knowledge base but could not find a reliable answer to this question."
                      Then recommend searching the official documentation or opening a GitHub Discussion, whichever is more appropriate.
                    - Do not claim that a feature, API, configuration key, fix, or URL exists unless the retrieved evidence says so.

                    Keep answers concise and professional. Use Markdown and backticks for code and identifiers.
                    """,
                Parameters = [],
                SampleObject = JsonConvert.SerializeObject(new Reply
                {
                    Answer = "Detailed explanation of the solution based on the documentation.",
                    AnswerStatus = "Grounded",
                    ReferenceUrls =
                    [
                        "https://docs.ravendb.net/7.0/server/storage/directory-structure",
                        "https://github.com/ravendb/ravendb/discussions/22266"
                    ]
                }),
                Queries = [
                    new AiAgentToolQuery
                    {
                        Name = "SearchDocumentation",
                        Description = "MANDATORY first search for every RavenDB technical question. Searches official RavenDB documentation. Copy any cited Url exactly from these results.",
                        Query = """
                            from index 'KnowledgeBase/SemanticSearch/Documentations'
                            where vector.search(BodyVector, $query)
                            limit 5
                            """,
                        ParametersSampleObject = "{\"query\": \"concise RavenDB concepts and error terms from the user's question\"}",
                        Options = new AiAgentToolQueryOptions
                        {
                            AllowModelQueries = true,
                            AddToInitialContext = false
                        }
                    },
                    new AiAgentToolQuery
                    {
                        Name = "SearchDiscussions",
                        Description = "Search RavenDB GitHub Discussions when official documentation is incomplete or when the question is about an error, edge case, upgrade, or troubleshooting scenario. Copy any cited Url exactly from these results.",
                        Query = """
                            from index 'KnowledgeBase/SemanticSearch/Discussions'
                            where vector.search(BodyVector, $query)
                            limit 5
                            """,
                        ParametersSampleObject = "{\"query\": \"specific RavenDB error, behavior, or troubleshooting terms\"}",
                        Options = new AiAgentToolQueryOptions
                        {
                            AllowModelQueries = true,
                            AddToInitialContext = false
                        }
                    },
                    new AiAgentToolQuery
                    {
                        Name = "SearchGoogleGroups",
                        Description = "Last-resort historical search for older RavenDB behavior. Use only after documentation and GitHub Discussions are insufficient. Never return a Google Groups Url, and do not mark an answer Grounded unless documentation or a GitHub Discussion also supports it.",
                        Query = """
                            from index 'KnowledgeBase/SemanticSearch/GoogleGroups'
                            where vector.search(BodyVector, $query) or vector.search(TitleVector, $query)
                            limit 5
                            """,
                        ParametersSampleObject = "{\"query\": \"historical RavenDB behavior or legacy error terms\"}",
                        Options = new AiAgentToolQueryOptions
                        {
                            AllowModelQueries = true,
                            AddToInitialContext = false
                        }
                    }
                ],
                MaxModelIterationsPerCall = 8,
                Actions = []
            });
    }
}

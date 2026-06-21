using Raven.Client.Documents.Indexes;
using Raven.Client.Documents;
using Raven.Client.Documents.Operations.Indexes;

namespace HelpdeskAgent.Indexes;

public static class KnowledgeBase_SemanticSearch_Documentations
{
    public static void Execute(IDocumentStore store)
    {
        store.Maintenance.Send(new PutIndexesOperation(
        [
            new IndexDefinition
            {
                Name = "KnowledgeBase/SemanticSearch/Documentations",
                Maps =
                [
                    """
                    from doc in docs.Documentation_Sitemaps
                    select new
                    {
                        doc.Title,
                        Body = doc.SearchableContent,
                        doc.Version,
                        doc.Category,
                        doc.Url,
                        Source = "Official Documentation",
                        BodyVector = LoadVector("SearchableContent", "documentations")
                    }
                    """
                ],
                Configuration =
                {
                    ["Indexing.Static.SearchEngineType"] = "Corax"
                }
            }
        ]));
    }
}

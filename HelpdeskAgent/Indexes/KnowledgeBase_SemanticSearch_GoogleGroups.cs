using Raven.Client.Documents.Indexes;
using Raven.Client.Documents;
using Raven.Client.Documents.Operations.Indexes;

namespace HelpdeskAgent.Indexes;

public static class KnowledgeBase_SemanticSearch_GoogleGroups
{
    public static void Execute(IDocumentStore store)
    {
        store.Maintenance.Send(new PutIndexesOperation(
        [
            new IndexDefinition
            {
                Name = "KnowledgeBase/SemanticSearch/GoogleGroups",
                Maps =
                [
                    """
                    from doc in docs.GoogleGroupMessages
                    select new
                    {
                        doc.Title,
                        doc.Body,
                        doc.CreatedAt,
                        doc.Author,
                        doc.Url,
                        Source = "Google Groups",
                        BodyVector = LoadVector("Body", "groups"),
                        TitleVector = LoadVector("Title", "groups")
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

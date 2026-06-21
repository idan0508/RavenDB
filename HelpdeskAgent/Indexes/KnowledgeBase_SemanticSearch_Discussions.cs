using Raven.Client.Documents.Indexes;
using Raven.Client.Documents;
using Raven.Client.Documents.Operations.Indexes;

namespace HelpdeskAgent.Indexes;

public static class KnowledgeBase_SemanticSearch_Discussions
{
    public static void Execute(IDocumentStore store)
    {
        store.Maintenance.Send(new PutIndexesOperation(
        [
            new IndexDefinition
            {
                Name = "KnowledgeBase/SemanticSearch/Discussions",
                Maps =
                [
                    """
                    from doc in docs.Discussions
                    select new
                    {
                        doc.Title,
                        Body = doc.SearchableContent ?? doc.Body,
                        Answer = doc.Answer != null ? doc.Answer.Body : null,
                        doc.IsAnswered,
                        doc.UpdatedAt,
                        doc.Url,
                        Source = "GitHub Discussions",
                        BodyVector = LoadVector("Body", "discussions")
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

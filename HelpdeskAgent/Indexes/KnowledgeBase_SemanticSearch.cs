using Raven.Client.Documents.Indexes;
using HelpdeskAgent.Model;

namespace HelpdeskAgent.Indexes;

public class KnowledgeBase_SemanticSearch : AbstractMultiMapIndexCreationTask
{
    public KnowledgeBase_SemanticSearch()
    {
        AddMap<Documentation>(docs => from doc in docs
            select new
            {
                Title = doc.Title,
                Body = doc.Body,
                Category = doc.Category,
                Url = doc.Url,
                Source = "Documentation",
                BodyVector = CreateVector("embed-docs")
            });

        AddMap<Discussion>(discussions => from doc in discussions
            select new
            {
                Title = doc.Title,
                Body = doc.Body,
                Category = doc.Category.Name,
                Url = doc.Url,
                Source = "GitHub Discussions",
                BodyVector = CreateVector("embed-discussions")
            });

        AddMap<GoogleGroupMessage>(messages => from doc in messages
            select new
            {
                Title = doc.Title,
                Body = doc.Body,
                Category = doc.Category.Name,
                Url = doc.Url,
                Source = "Google Groups",
                BodyVector = CreateVector("embed-google-groups")
            });

        // Use Corax for Vector Search
        Configuration["Indexing.Static.SearchEngineType"] = "Corax";
    }
}

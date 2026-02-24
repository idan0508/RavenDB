// To be added as a Static Index in RavenDB Studio -> Indexes -> New Index
// Name: Discussions/ByEmbedding

from doc in docs.Discussions
select new {
    Title = doc.Title,
    Body = doc.Body,
    Category = doc.Category.Name,
    Url = doc.Url,
    BodyVector = LoadVector("Body", "embed-discussions")
}

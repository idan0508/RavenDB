using System;
using System.Collections.Generic;

namespace HelpdeskAgent.Model;

public class Discussion
{
    public string Id { get; set; }
    public string GitHubId { get; set; }
    public int Number { get; set; }
    public string Title { get; set; }
    public string Body { get; set; }
    public string Url { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
    public DateTimeOffset UpdatedAt { get; set; }
    public string Author { get; set; }
    public int UpvoteCount { get; set; }
    public bool? IsAnswered { get; set; }
    public int CommentsCount { get; set; }
    public List<Comment> Comments { get; set; } = new();
    public Comment Answer { get; set; }
    public string SearchableContent { get; set; }
    public Category Category { get; set; }

    public class Comment
    {
        public string Body { get; set; }
        public string Author { get; set; }
        public DateTimeOffset CreatedAt { get; set; }
        public bool IsAnswer { get; set; }
    }
}

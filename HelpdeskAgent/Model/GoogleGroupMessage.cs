using System;

namespace HelpdeskAgent.Model
{
    public class GoogleGroupMessage
    {
        public string Id { get; set; }
        public string Title { get; set; }
        public string Body { get; set; }
        public Category Category { get; set; }
        public string Url { get; set; }
        public DateTimeOffset CreatedAt { get; set; }
        public string Author { get; set; }
        public string MessageId { get; set; }
        public string ThreadId { get; set; }
    }

    public class Category
    {
        public string Name { get; set; }
        public string Emoji { get; set; }
        public string Description { get; set; }
    }
}

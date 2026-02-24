using System;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using MimeKit;
using Raven.Client.Documents;
using HelpdeskAgent.Model;

namespace HelpdeskAgent
{
    public static class MboxImporter
    {
        public static async Task ImportAsync(IDocumentStore store, string mboxFilePath)
        {
            if (!File.Exists(mboxFilePath))
            {
                Console.WriteLine($"Mbox file not found at: {mboxFilePath}");
                return;
            }

            Console.WriteLine($"Starting import of {mboxFilePath} using BulkInsert...");
            
            using var stream = File.OpenRead(mboxFilePath);
            var parser = new MimeParser(stream, MimeFormat.Mbox);

            var count = 0;
            using (var bulkInsert = store.BulkInsert())
            {
                while (!parser.IsEndOfStream)
                {
                    var message = await parser.ParseMessageAsync();
                    
                    var body = message.TextBody ?? message.HtmlBody ?? "";
                    if (string.IsNullOrWhiteSpace(body))
                        continue; // Skip empty messages

                    var discussion = new GoogleGroupMessage
                    {
                        Title = message.Subject ?? "No Subject",
                        Body = body,
                        Author = message.From?.ToString(),
                        CreatedAt = message.Date,
                        MessageId = message.MessageId,
                        ThreadId = message.InReplyTo ?? message.References?.FirstOrDefault() ?? message.MessageId,
                        Category = new Category 
                        { 
                            Name = "Google Groups", 
                            Emoji = "📧", 
                            Description = "Historical Google Groups archive" 
                        },
                        Url = string.IsNullOrWhiteSpace(message.MessageId) 
                            ? "" 
                            : $"https://groups.google.com/g/ravendb/search?q={Uri.EscapeDataString(message.MessageId)}"
                    };

                    await bulkInsert.StoreAsync(discussion);
                    count++;

                    if (count % 5000 == 0)
                    {
                        Console.WriteLine($"Imported {count} messages...");
                    }
                }
            }

            Console.WriteLine($"Import complete! Total messages imported: {count}");
        }
    }
}

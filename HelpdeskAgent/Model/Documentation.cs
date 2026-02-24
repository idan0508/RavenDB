using System;
using System.Collections.Generic;

namespace HelpdeskAgent.Model;

public class Documentation
{
    public string Id { get; set; }
    public string Title { get; set; }
    public string Url { get; set; }
    public string Body { get; set; }
    public string Version { get; set; }
    public string Category { get; set; }
    public string Source { get; set; }
    public List<string> Sections { get; set; }
    public List<string> CodeExamples { get; set; }
}

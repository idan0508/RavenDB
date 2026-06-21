public static class AgentResponseSafety
{
    public const string NotFoundMessage =
        "I searched the RavenDB knowledge base but could not find a reliable answer to this question.\n\n" +
        "Try searching the official RavenDB documentation. If this is a specific error, edge case, or unsupported scenario, open a GitHub Discussion and include your RavenDB version, environment, code, and full error message.";

    public static string FormatForUser(AgentReply reply)
    {
        var status = reply.AnswerStatus?.Trim();

        if (string.Equals(status, "NotFound", StringComparison.OrdinalIgnoreCase))
            return NotFoundMessage;

        if (string.Equals(status, "NeedsClarification", StringComparison.OrdinalIgnoreCase))
        {
            return string.IsNullOrWhiteSpace(reply.Answer)
                ? "I need your RavenDB version and the exact error or behavior before I can search for a reliable answer."
                : reply.Answer.Trim();
        }

        if (!string.Equals(status, "Grounded", StringComparison.OrdinalIgnoreCase))
            return NotFoundMessage;

        var safeUrls = (reply.ReferenceUrls ?? [])
            .Where(IsAllowedKnowledgeBaseUrl)
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToArray();

        if (string.IsNullOrWhiteSpace(reply.Answer) || safeUrls.Length == 0)
            return NotFoundMessage;

        return $"{reply.Answer.Trim()}\n\n📎 **Sources:**\n{string.Join("\n", safeUrls.Select(url => $"• {url}"))}";
    }

    internal static bool IsAllowedKnowledgeBaseUrl(string? value)
    {
        if (!Uri.TryCreate(value, UriKind.Absolute, out var uri) ||
            uri.Scheme != Uri.UriSchemeHttps ||
            !string.IsNullOrEmpty(uri.UserInfo))
        {
            return false;
        }

        if (uri.Host.Equals("docs.ravendb.net", StringComparison.OrdinalIgnoreCase))
            return uri.AbsolutePath.Length > 1;

        if (!uri.Host.Equals("github.com", StringComparison.OrdinalIgnoreCase))
            return false;

        var segments = uri.AbsolutePath.Split('/', StringSplitOptions.RemoveEmptyEntries);

        return segments.Length == 4 &&
               segments[0].Equals("ravendb", StringComparison.OrdinalIgnoreCase) &&
               segments[1].Equals("ravendb", StringComparison.OrdinalIgnoreCase) &&
               segments[2].Equals("discussions", StringComparison.OrdinalIgnoreCase) &&
               int.TryParse(segments[3], out _);
    }
}

/*
 * RavenDB Helpdesk Telegram Bot
 * ==============================
 * A Telegram bot that answers RavenDB questions
 * using the RavenDB AI Agent (RAG over GitHub Discussions).
 *
 * Based on the PropertySphere sample by Ayende Rahien (RavenDB CEO).
 * Adapted for the RavenDB Helpdesk use case.
 *
 * Architecture:
 *   User (Telegram) → This Bot → RavenDB AI Agent → Azure OpenAI → Response
 *
 * Setup:
 *   1. Create a bot via @BotFather on Telegram → get the token
 *   2. Put the token in appsettings.json
 *   3. Make sure RavenDB is running with the AI Agent configured
 *   4. Run: dotnet run
 *
 * Authors: Ron Blanki, Idan Dahan
 * Project: RavenDB AI Helpdesk - Final Year Project
 */

using System.Collections.Concurrent;
using Microsoft.Extensions.Configuration;
using Raven.Client.Documents;
using Raven.Client.Documents.AI;
using Telegram.Bot;
using Telegram.Bot.Polling;
using Telegram.Bot.Types;
using Telegram.Bot.Types.Enums;

// ====== LOAD CONFIGURATION ======
var config = new ConfigurationBuilder()
    .SetBasePath(Directory.GetCurrentDirectory())
    .AddJsonFile("appsettings.json", optional: false)
    .Build();

var ravenUrls = config.GetSection("RavenDB:Urls").Get<string[]>()
    ?? new[] { "http://127.0.0.1:8080" };
var ravenDatabase = config["RavenDB:Database"] ?? "HelpdeskDB";
var agentName = config["RavenDB:AgentName"] ?? "RavenDB-Support";
var telegramToken = config["Telegram:BotToken"] ?? "";

if (string.IsNullOrWhiteSpace(telegramToken) || telegramToken == "YOUR_TELEGRAM_BOT_TOKEN_HERE")
{
    Console.ForegroundColor = ConsoleColor.Red;
    Console.WriteLine("❌ ERROR: Telegram Bot Token is not configured!");
    Console.ResetColor();
    Console.WriteLine();
    Console.WriteLine("Steps to fix:");
    Console.WriteLine("  1. Open Telegram and message @BotFather");
    Console.WriteLine("  2. Send /newbot and follow the instructions");
    Console.WriteLine("  3. Copy the bot token");
    Console.WriteLine("  4. Paste it in appsettings.json under Telegram:BotToken");
    Console.WriteLine();
    return;
}

// ====== INITIALIZE RAVENDB ======
Console.WriteLine("=".PadRight(60, '='));
Console.WriteLine("🤖 RavenDB Helpdesk Telegram Bot");
Console.WriteLine("=".PadRight(60, '='));
Console.WriteLine($"RavenDB:  {string.Join(", ", ravenUrls)}");
Console.WriteLine($"Database: {ravenDatabase}");
Console.WriteLine($"Agent:    {agentName}");
Console.WriteLine();

using var store = new DocumentStore
{
    Urls = ravenUrls,
    Database = ravenDatabase,
};
store.Initialize();

// Verify RavenDB connection
try
{
    var stats = store.Maintenance.Send(new Raven.Client.Documents.Operations.GetStatisticsOperation());
    Console.WriteLine($"✅ Connected to RavenDB! Documents: {stats.CountOfDocuments}");
}
catch (Exception ex)
{
    Console.ForegroundColor = ConsoleColor.Red;
    Console.WriteLine($"❌ Cannot connect to RavenDB: {ex.Message}");
    Console.ResetColor();
    Console.WriteLine("Make sure RavenDB is running and HelpdeskDB exists.");
    return;
}

// ====== CONVERSATION TRACKING ======
// Track conversation IDs per Telegram chat for continuity (like PropertySphere's GetConversationId)
static string GetConversationId(long chatId) => $"chats/{chatId}/{DateTime.Today:yyyy-MM-dd}";

// ====== INITIALIZE TELEGRAM BOT ======
var bot = new TelegramBotClient(telegramToken);
var me = await bot.GetMe();
Console.WriteLine($"✅ Telegram bot: @{me.Username} ({me.FirstName})");
Console.WriteLine();
Console.WriteLine("🚀 Bot is running! Send a message to your bot on Telegram.");
Console.WriteLine("   Press Ctrl+C to stop.");
Console.WriteLine();

using var cts = new CancellationTokenSource();
Console.CancelKeyPress += (_, e) =>
{
    e.Cancel = true;
    cts.Cancel();
};

// ====== START POLLING ======
bot.StartReceiving(
    updateHandler: HandleUpdateAsync,
    errorHandler: HandleErrorAsync,
    receiverOptions: new ReceiverOptions
    {
        AllowedUpdates = new[] { UpdateType.Message },
    },
    cancellationToken: cts.Token
);

// Keep running until Ctrl+C
try
{
    await Task.Delay(Timeout.Infinite, cts.Token);
}
catch (TaskCanceledException)
{
    Console.WriteLine("\n👋 Bot stopped. Goodbye!");
}

// ====== HANDLERS ======

async Task HandleUpdateAsync(ITelegramBotClient botClient, Update update, CancellationToken ct)
{
    if (update.Message is not { Text: { } messageText } message)
        return;

    var chatId = message.Chat.Id;
    var userName = message.From?.FirstName ?? "User";

    Console.WriteLine($"📩 [{userName}] {messageText}");

    // Handle commands
    if (messageText.StartsWith("/"))
    {
        await HandleCommandAsync(botClient, message, ct);
        return;
    }

    // Show "typing..." indicator
    await botClient.SendChatAction(chatId, ChatAction.Typing, cancellationToken: ct);

    try
    {
        // Get conversation ID for this chat (same pattern as PropertySphere)
        var conversationId = GetConversationId(chatId);

        // Call RavenDB AI Agent (modeled after PropertySphere's ProcessMessageAsync)
        var response = await AskAgentAsync(messageText, conversationId, ct);

        // Send response with Markdown, falling back to plain text
        await SendMessageSafeAsync(botClient, chatId, response, ct);

        Console.WriteLine($"📤 [RavenDB AI Agent] Response sent ({response.Length} chars)");
    }
    catch (Exception ex)
    {
        Console.ForegroundColor = ConsoleColor.Red;
        Console.WriteLine($"❌ Error processing message: {ex.Message}");
        Console.ResetColor();

        await botClient.SendMessage(
            chatId,
            "⚠️ Sorry, I encountered an error processing your question. Please try again.",
            cancellationToken: ct
        );
    }
}

async Task HandleCommandAsync(ITelegramBotClient botClient, Message message, CancellationToken ct)
{
    var chatId = message.Chat.Id;
    var command = message.Text!.Split(' ')[0].ToLower();

    switch (command)
    {
        case "/start":
            await botClient.SendMessage(chatId,
                "👋 Welcome to the **RavenDB Helpdesk Bot**!\n\n" +
                "I can answer questions about RavenDB by searching through GitHub Discussions and documentation.\n\n" +
                "Just type your question and I'll find the best answer.\n\n" +
                "**Commands:**\n" +
                "/help - Show help\n" +
                "/clear - Start a new conversation\n" +
                "/about - About this bot",
                parseMode: ParseMode.Markdown,
                cancellationToken: ct);
            break;

        case "/help":
            await botClient.SendMessage(chatId,
                "🔍 **How to use this bot:**\n\n" +
                "1. Ask any question about RavenDB\n" +
                "2. I'll search GitHub Discussions & docs\n" +
                "3. You'll get an answer with sources\n\n" +
                "**Example questions:**\n" +
                "• How to upgrade from RavenDB 5.4 to 7.2?\n" +
                "• How to use Includes to fix N+1 queries?\n" +
                "• What is the Session pattern in RavenDB?\n\n" +
                "**Commands:**\n" +
                "/clear - Start a fresh conversation\n" +
                "/about - About this bot",
                parseMode: ParseMode.Markdown,
                cancellationToken: ct);
            break;

        case "/clear":
            // Delete the conversation document (same as PropertySphere)
            using (var session = store.OpenAsyncSession())
            {
                var conversationId = GetConversationId(chatId);
                session.Delete(conversationId);
                await session.SaveChangesAsync(ct);
            }
            await botClient.SendMessage(chatId,
                "🔄 Conversation cleared! Ask me anything about RavenDB.",
                cancellationToken: ct);
            break;

        case "/about":
            await botClient.SendMessage(chatId,
                "ℹ️ **RavenDB Helpdesk Bot**\n\n" +
                "Built as a Final Year Project by:\n" +
                "• Ron Blanki\n" +
                "• Idan Dahan\n\n" +
                "**Tech Stack:**\n" +
                "• RavenDB 7.2 (AI Agent)\n" +
                "• Azure OpenAI + GPT-4.1\n" +
                "• .NET 8 + Telegram.Bot\n\n" +
                "**Data Sources:**\n" +
                "• 1,052 GitHub Discussions\n" +
                "• 112,190 Google Groups messages\n" +
                "• 8,000+ pages of official documentation",
                parseMode: ParseMode.Markdown,
                cancellationToken: ct);
            break;

        default:
            await botClient.SendMessage(chatId,
                "❓ Unknown command. Type /help for available commands.",
                cancellationToken: ct);
            break;
    }
}

Task HandleErrorAsync(ITelegramBotClient botClient, Exception exception, CancellationToken ct)
{
    Console.ForegroundColor = ConsoleColor.Red;
    Console.WriteLine($"❌ Telegram error: {exception.Message}");
    Console.ResetColor();
    return Task.CompletedTask;
}

// ====== RAVENDB AI AGENT ======
// Modeled directly after PropertySphere's TelegramPollingService.ProcessMessageAsync

async Task<string> AskAgentAsync(string question, string conversationId, CancellationToken ct)
{
    try
    {
        // Create conversation — same API as PropertySphere
        var conversation = store.AI.Conversation(
            agentName,
            conversationId,
            new AiConversationCreationOptions());

        // Set user prompt
        conversation.SetUserPrompt(question);

        // Run and get response (same as PropertySphere line 288)
        var result = await conversation.RunAsync<AgentReply>(ct);

        // Format response
        var answer = result.Answer.Answer;

        // Append sources if available
        if (result.Answer.ReferenceUrls is { Length: > 0 })
        {
            answer += "\n\n📎 **Sources:**\n";
            foreach (var url in result.Answer.ReferenceUrls)
            {
                answer += $"• {url}\n";
            }
        }

        return string.IsNullOrWhiteSpace(answer)
            ? "I couldn't find a relevant answer. Please try rephrasing your question."
            : answer;
    }
    catch (Raven.Client.Exceptions.RavenException ex)
    {
        Console.ForegroundColor = ConsoleColor.Yellow;
        Console.WriteLine($"⚠️ RavenDB Agent error: {ex.Message}");
        Console.ResetColor();

        if (ex.Message.Contains("agent", StringComparison.OrdinalIgnoreCase))
        {
            return $"⚠️ The AI Agent '{agentName}' could not be found or is not configured. " +
                   "Please check RavenDB Studio → AI Hub → AI Agents.";
        }

        if (ex.Message.Contains("connection", StringComparison.OrdinalIgnoreCase) ||
            ex.Message.Contains("timeout", StringComparison.OrdinalIgnoreCase))
        {
            return "⚠️ The LLM (Azure OpenAI) took too long to respond. " +
                   "Please try your question again in a moment.";
        }

        return $"⚠️ Error from RavenDB: {ex.Message}";
    }
}

// ====== TELEGRAM HELPERS ======
// Safe message sending with Markdown fallback (from PropertySphere)

async Task SendMessageSafeAsync(ITelegramBotClient botClient, long chatId, string text, CancellationToken ct)
{
    // Split for Telegram's 4096 character limit
    if (text.Length > 4096)
    {
        for (int i = 0; i < text.Length; i += 4000)
        {
            var chunk = text.Substring(i, Math.Min(4000, text.Length - i));
            await SendSingleMessageSafeAsync(botClient, chatId, chunk, ct);
            await Task.Delay(500, ct);
        }
    }
    else
    {
        await SendSingleMessageSafeAsync(botClient, chatId, text, ct);
    }
}

async Task SendSingleMessageSafeAsync(ITelegramBotClient botClient, long chatId, string text, CancellationToken ct)
{
    try
    {
        // Try Markdown first (like PropertySphere)
        await botClient.SendMessage(chatId, text, parseMode: ParseMode.Markdown, cancellationToken: ct);
    }
    catch (Telegram.Bot.Exceptions.ApiRequestException)
    {
        // If Markdown parsing fails, send as plain text
        await botClient.SendMessage(chatId, text, cancellationToken: ct);
    }
}

// ====== RESPONSE MODEL ======
// Matches the SampleObject configured in the RavenDB AI Agent
// Must be at the bottom in a top-level program
public class AgentReply
{
    public string Answer { get; set; } = string.Empty;
    public string[] ReferenceUrls { get; set; } = [];
}


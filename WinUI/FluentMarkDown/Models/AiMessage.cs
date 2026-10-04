using System.Text.Json;
using System.Text.Json.Serialization;

namespace FluentMarkDown.Models;

/// <summary>
/// AI 对话消息
/// </summary>
public class AiMessage
{
    [JsonPropertyName("role")]
    public string Role { get; set; } = "user"; // system | user | assistant

    [JsonPropertyName("content")]
    public string Content { get; set; } = string.Empty;

    public static AiMessage System(string content) => new() { Role = "system", Content = content };
    public static AiMessage User(string content) => new() { Role = "user", Content = content };
    public static AiMessage Assistant(string content) => new() { Role = "assistant", Content = content };
}

/// <summary>
/// AI 聊天请求
/// </summary>
public class AiChatRequest
{
    [JsonPropertyName("model")]
    public string Model { get; set; } = string.Empty;

    [JsonPropertyName("messages")]
    public List<AiMessage> Messages { get; set; } = new();

    [JsonPropertyName("stream")]
    public bool Stream { get; set; } = true;

    [JsonPropertyName("temperature")]
    public double Temperature { get; set; } = 0.7;
}

/// <summary>
/// AI 聊天响应（SSE chunk）
/// </summary>
public class AiChatChunk
{
    [JsonPropertyName("choices")]
    public List<AiChoice>? Choices { get; set; }
}

public class AiChoice
{
    [JsonPropertyName("delta")]
    public AiDelta? Delta { get; set; }

    [JsonPropertyName("finish_reason")]
    public string? FinishReason { get; set; }
}

public class AiDelta
{
    [JsonPropertyName("content")]
    public string? Content { get; set; }
}

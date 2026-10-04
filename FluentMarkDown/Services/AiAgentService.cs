using System.Net.Http;
using System.Net.Http.Headers;
using System.Runtime.CompilerServices;
using System.Text;
using System.Text.Json;
using FluentMarkDown.Models;

namespace FluentMarkDown.Services;

/// <summary>
/// AI Agent 服务 —— 支持 OpenAI 兼容 API（含 Azure、Ollama 等）
/// </summary>
public class AiAgentService
{
    private readonly HttpClient _httpClient;
    private readonly AppSettings _settings;

    public AiAgentService(HttpClient httpClient, AppSettings settings)
    {
        _httpClient = httpClient;
        _settings = settings;
    }

    /// <summary>
    /// 流式发送聊天请求，逐 token 返回
    /// </summary>
    public async IAsyncEnumerable<string> ChatStreamAsync(
        List<AiMessage> messages,
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        var request = new AiChatRequest
        {
            Model = _settings.AiModel,
            Messages = messages,
            Stream = true,
            Temperature = 0.7,
        };

        var json = JsonSerializer.Serialize(request);
        var content = new StringContent(json, Encoding.UTF8, "application/json");

        using var httpRequest = new HttpRequestMessage(HttpMethod.Post,
            $"{_settings.AiApiEndpoint.TrimEnd('/')}/chat/completions");
        httpRequest.Content = content;

        if (!string.IsNullOrEmpty(_settings.AiApiKey))
        {
            httpRequest.Headers.Authorization =
                new AuthenticationHeaderValue("Bearer", _settings.AiApiKey);
        }

        using var response = await _httpClient.SendAsync(httpRequest,
            HttpCompletionOption.ResponseHeadersRead, cancellationToken);
        response.EnsureSuccessStatusCode();

        using var stream = await response.Content.ReadAsStreamAsync(cancellationToken);
        using var reader = new StreamReader(stream);

        while (!reader.EndOfStream)
        {
            cancellationToken.ThrowIfCancellationRequested();

            var line = await reader.ReadLineAsync(cancellationToken);
            if (string.IsNullOrEmpty(line)) continue;
            if (!line.StartsWith("data: ")) continue;

            var data = line["data: ".Length..].Trim();
            if (data == "[DONE]") yield break;

            AiChatChunk? chunk;
            try
            {
                chunk = JsonSerializer.Deserialize<AiChatChunk>(data);
            }
            catch { continue; }

            var delta = chunk?.Choices?.FirstOrDefault()?.Delta?.Content;
            if (!string.IsNullOrEmpty(delta))
            {
                yield return delta;
            }
        }
    }

    /// <summary>
    /// 非流式一次性请求
    /// </summary>
    public async Task<string> ChatAsync(List<AiMessage> messages, CancellationToken cancellationToken = default)
    {
        var sb = new StringBuilder();
        await foreach (var token in ChatStreamAsync(messages, cancellationToken))
        {
            sb.Append(token);
        }
        return sb.ToString();
    }
}

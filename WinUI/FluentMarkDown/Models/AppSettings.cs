using System.Text.Json;
using System.Text.Json.Serialization;

namespace FluentMarkDown.Models;

/// <summary>
/// 应用设置，持久化到 JSON
/// </summary>
public class AppSettings
{
    private static readonly string SettingsPath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
        "FluentMarkDown", "settings.json");

    // ── 编辑器 ──
    public string EditorTheme { get; set; } = "vs-dark";
    public int FontSize { get; set; } = 14;
    public string FontFamily { get; set; } = "Cascadia Code, Consolas, 'Courier New', monospace";
    public bool WordWrap { get; set; } = true;
    public bool Minimap { get; set; } = false;
    public int TabSize { get; set; } = 4;

    // ── 预览 ──
    public string PreviewTheme { get; set; } = "default";
    public bool SyncScroll { get; set; } = true;

    // ── AI ──
    public string AiProvider { get; set; } = "openai"; // openai | azure | ollama
    public string AiApiEndpoint { get; set; } = "https://api.openai.com/v1";
    public string AiApiKey { get; set; } = string.Empty;
    public string AiModel { get; set; } = "gpt-4o";
    public string AiSystemPrompt { get; set; } =
        "你是一个专业的 Markdown 编辑助手。用户会向你描述需求，你生成高质量的 Markdown 内容。" +
        "直接输出 Markdown 文本，不要包裹在代码块中。";

    // ── 自动保存 ──
    public bool AutoSave { get; set; } = true;
    public int AutoSaveIntervalSeconds { get; set; } = 30;

    // ── 持久化 ──

    public static AppSettings Load()
    {
        try
        {
            if (File.Exists(SettingsPath))
            {
                var json = File.ReadAllText(SettingsPath);
                return JsonSerializer.Deserialize<AppSettings>(json, JsonOptions) ?? new();
            }
        }
        catch { /* 配置损坏则使用默认值 */ }
        return new();
    }

    public void Save()
    {
        try
        {
            var dir = Path.GetDirectoryName(SettingsPath)!;
            Directory.CreateDirectory(dir);
            var json = JsonSerializer.Serialize(this, JsonOptions);
            File.WriteAllText(SettingsPath, json);
        }
        catch { /* 保存失败静默处理 */ }
    }

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
    };
}

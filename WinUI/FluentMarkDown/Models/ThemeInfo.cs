namespace FluentMarkDown.Models;

/// <summary>
/// 预览主题配置
/// </summary>
public record ThemeInfo(string Id, string Name, bool IsDark);

/// <summary>
/// 内置预览主题列表
/// </summary>
public static class PreviewThemes
{
    public static IReadOnlyList<ThemeInfo> All { get; } = new List<ThemeInfo>
    {
        new("default",    "默认",     false),
        new("dark",       "深色",     true),
        new("github",     "GitHub",   false),
        new("solarized",  "Solarized", false),
        new("nord",       "Nord",     true),
        new("dracula",    "Dracula",  true),
        new("monokai",    "Monokai",  true),
        new("one-dark",   "One Dark", true),
    };

    public static ThemeInfo Get(string id) =>
        All.FirstOrDefault(t => t.Id == id) ?? All[0];
}

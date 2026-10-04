using Markdig;

namespace FluentMarkDown.Services;

/// <summary>
/// Markdown 转 HTML 服务，基于 Markdig
/// </summary>
public class MarkdownService
{
    private readonly MarkdownPipeline _pipeline;

    public MarkdownService()
    {
        _pipeline = new MarkdownPipelineBuilder()
            .UseAdvancedExtensions()       // 表格、任务列表、脚注、定义列表等
            .UseAutoLinks()                // 自动识别 URL
            .UseEmojiAndSmiley()           // 表情符号 :)
            .UseMathematics()              // LaTeX 数学公式
            .UseDiagrams()                 // Mermaid 图表
            .UseYamlFrontMatter()          // YAML Front Matter
            .UseGenericAttributes()        // 通用属性 {.class #id}
            .Build();
    }

    /// <summary>
    /// 将 Markdown 文本转换为 HTML
    /// </summary>
    public string ToHtml(string markdown)
    {
        if (string.IsNullOrEmpty(markdown))
            return string.Empty;
        return Markdown.ToHtml(markdown, _pipeline);
    }
}

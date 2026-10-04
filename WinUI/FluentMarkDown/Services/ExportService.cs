using DocumentFormat.OpenXml;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Wordprocessing;
using Markdig;
using Markdig.Syntax;
using Markdig.Syntax.Inlines;
using QuestPDF.Fluent;
using QuestPDF.Helpers;
using QuestPDF.Infrastructure;
using A = DocumentFormat.OpenXml.Wordprocessing;

namespace FluentMarkDown.Services;

/// <summary>
/// 导出服务 —— 支持 PDF（QuestPDF）和 Word（OpenXML）
/// </summary>
public class ExportService
{
    private readonly MarkdownService _markdownService;

    public ExportService(MarkdownService markdownService)
    {
        _markdownService = markdownService;
        QuestPDF.Settings.License = LicenseType.Community;
    }

    // ──────────────────────────── PDF ────────────────────────────

    public void ExportPdf(string outputPath, string markdown)
    {
        var document = Markdown.Parse(markdown,
            new MarkdownPipelineBuilder().UseAdvancedExtensions().Build());

        Document.Create(container =>
        {
            container.Page(page =>
            {
                page.Size(PageSizes.A4);
                page.Margin(50);
                page.DefaultTextStyle(x => x.FontSize(11));

                page.Content().Column(col =>
                {
                    col.Spacing(8);
                    foreach (var block in document)
                    {
                        RenderBlock(col, block);
                    }
                });

                page.Footer().AlignCenter().Text(t =>
                {
                    t.Span("Page ");
                    t.CurrentPageNumber();
                    t.Span(" / ");
                    t.TotalPages();
                });
            });
        }).GeneratePdf(outputPath);
    }

    private void RenderBlock(ColumnDescriptor col, Markdig.Syntax.Block block)
    {
        switch (block)
        {
            case HeadingBlock heading:
                var level = heading.Level;
                col.Item().PaddingVertical(6).Text(GetPlainText(heading))
                    .FontSize(level switch { 1 => 24, 2 => 20, 3 => 16, _ => 13 })
                    .Bold();
                if (level <= 2)
                    col.Item().LineHorizontal(1).LineColor(Colors.Grey.Lighten2);
                break;

            case ParagraphBlock para:
                col.Item().Text(GetPlainText(para));
                break;

            case FencedCodeBlock code:
                var codeText = GetFencedCodeText(code);
                col.Item().Background(Colors.Grey.Lighten4)
                    .Padding(10).BorderRadius(4)
                    .Text(codeText).FontFamily("Consolas").FontSize(9);
                break;

            case QuoteBlock quote:
                col.Item().BorderLeft(3).BorderColor(Colors.Blue.Lighten2)
                    .PaddingLeft(12).Background(Colors.Grey.Lighten5)
                    .Column(inner =>
                    {
                        foreach (var child in quote)
                            RenderBlock(inner, child);
                    });
                break;

            case ListBlock list:
                col.Item().PaddingLeft(16).Column(inner =>
                {
                    int idx = 1;
                    foreach (ListItemBlock item in list)
                    {
                        var prefix = list.IsOrdered ? $"{idx++}. " : "• ";
                        inner.Item().Row(row =>
                        {
                            row.AutoItem().Text(prefix).FontSize(11);
                            row.RelativeItem().Column(ic =>
                            {
                                foreach (var child in item)
                                    RenderBlock(ic, child);
                            });
                        });
                    }
                });
                break;

            case ThematicBreakBlock:
                col.Item().PaddingVertical(4).LineHorizontal(1).LineColor(Colors.Grey.Lighten2);
                break;
        }
    }

    private static string GetPlainText(Markdig.Syntax.Block block)
    {
        if (block is LeafBlock leaf && leaf.Inline != null)
        {
            var sb = new System.Text.StringBuilder();
            foreach (var inline in leaf.Inline)
            {
                if (inline is LiteralInline literal)
                    sb.Append(literal.Content);
                else if (inline is CodeInline code)
                    sb.Append(code.Content);
            }
            return sb.ToString();
        }
        return block.ToString() ?? string.Empty;
    }

    private static string GetFencedCodeText(FencedCodeBlock code)
    {
        if (code.Lines.Count == 0) return string.Empty;
        var sb = new System.Text.StringBuilder();
        for (int i = 0; i < code.Lines.Count; i++)
        {
            if (i > 0) sb.AppendLine();
            sb.Append(code.Lines.Lines[i].Slice.Text?
                .Substring(code.Lines.Lines[i].Slice.Start, code.Lines.Lines[i].Slice.Length) ?? "");
        }
        return sb.ToString();
    }

    // ──────────────────────────── Word ────────────────────────────

    public void ExportWord(string outputPath, string markdown)
    {
        using var doc = WordprocessingDocument.Create(outputPath, WordprocessingDocumentType.Document);
        var mainPart = doc.AddMainDocumentPart();
        mainPart.Document = new Document(new Body());
        var body = mainPart.Document.Body!;

        var mdDoc = Markdown.Parse(markdown,
            new MarkdownPipelineBuilder().UseAdvancedExtensions().Build());

        foreach (var block in mdDoc)
        {
            switch (block)
            {
                case HeadingBlock heading:
                    body.AppendChild(new A.Paragraph(
                        new A.ParagraphProperties(
                            new A.ParagraphStyleId { Val = $"Heading{heading.Level}" }),
                        new A.Run(new A.Text(GetPlainText(heading)))));
                    break;

                case ParagraphBlock para:
                    body.AppendChild(new A.Paragraph(
                        new A.Run(new A.Text(GetPlainText(para)))));
                    break;

                case FencedCodeBlock code:
                    body.AppendChild(new A.Paragraph(
                        new A.ParagraphProperties(
                            new A.Shading { Val = ShadingPatternValues.Clear, Fill = "F5F5F5" }),
                        new A.Run(
                            new A.RunProperties(new A.RunFonts { Ascii = "Consolas", HighAnsi = "Consolas" }),
                            new A.Text(GetFencedCodeText(code)) { Space = SpaceProcessingModeValues.Preserve })));
                    break;

                case ListBlock list:
                    int idx = 1;
                    foreach (ListItemBlock item in list)
                    {
                        var prefix = list.IsOrdered ? $"{idx++}. " : "• ";
                        var text = item.Descendants<ParagraphBlock>()
                            .Select(GetPlainText)
                            .FirstOrDefault() ?? "";
                        body.AppendChild(new A.Paragraph(
                            new A.Run(new A.Text(prefix + text))));
                    }
                    break;

                case ThematicBreakBlock:
                    body.AppendChild(new A.Paragraph(
                        new A.ParagraphProperties(
                            new A.BottomBorder { Val = BorderValues.Single, Size = 6, Color = "CCCCCC" })));
                    break;
            }
        }
    }

    // ──────────────────────────── HTML ────────────────────────────

    public void ExportHtml(string outputPath, string markdown)
    {
        var html = _markdownService.ToHtml(markdown);
        var fullHtml = $"""
            <!DOCTYPE html>
            <html>
            <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Exported Document</title>
            <style>
            body {{ font-family: -apple-system, "Segoe UI", sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; line-height: 1.7; color: #333; }}
            h1,h2,h3 {{ color: #2c3e50; }}
            code {{ background: #f5f5f5; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }}
            pre {{ background: #f5f5f5; padding: 16px; border-radius: 8px; overflow-x: auto; }}
            pre code {{ background: transparent; }}
            blockquote {{ border-left: 4px solid #3498db; padding: 12px 16px; margin: 12px 0; background: #f9f9f9; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #e8e8e8; padding: 8px 12px; }}
            th {{ background: #f5f5f5; }}
            img {{ max-width: 100%; }}
            </style>
            </head>
            <body>
            {html}
            </body>
            </html>
            """;
        File.WriteAllText(outputPath, fullHtml);
    }
}

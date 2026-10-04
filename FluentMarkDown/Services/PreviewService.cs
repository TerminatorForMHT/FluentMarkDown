namespace FluentMarkDown.Services;

/// <summary>
/// 预览 HTML 模板构建器 —— 将 Markdown HTML 包装成完整预览页面
/// </summary>
public class PreviewService
{
    private readonly MarkdownService _markdownService;

    public PreviewService(MarkdownService markdownService)
    {
        _markdownService = markdownService;
    }

    /// <summary>
    /// 构建完整预览 HTML（首次加载用）
    /// </summary>
    public string BuildFullPreview(string markdown, string themeId = "default", bool isDark = false)
    {
        var bodyHtml = _markdownService.ToHtml(markdown);
        return BuildPage(bodyHtml, themeId, isDark);
    }

    /// <summary>
    /// 仅获取 Markdown 转换后的 HTML body（增量更新用）
    /// </summary>
    public string GetBodyHtml(string markdown)
    {
        return _markdownService.ToHtml(markdown);
    }

    private static string BuildPage(string bodyHtml, string themeId, bool isDark)
    {
        var theme = GetThemeCss(themeId, isDark);
        var hljsTheme = isDark
            ? "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css"
            : "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css";
        var mermaidTheme = isDark ? "dark" : "default";

        return $"""
            <!DOCTYPE html>
            <html>
            <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="stylesheet" href="{hljsTheme}">
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.css">
            <script>
              if (typeof structuredClone === "undefined") {{
                window.structuredClone = function(obj) {{ return JSON.parse(JSON.stringify(obj)); }};
              }}
            </script>
            <script defer src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
            <script defer src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
            <script defer src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.js"></script>
            <script defer src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/contrib/auto-render.min.js"></script>
            <style>
            {BaseCss()}
            {theme}
            </style>
            </head>
            <body>
              <button class="outline-toggle" id="outlineToggle" title="大纲">&#9776;</button>
              <div class="outline-panel" id="outlinePanel">
                <div class="outline-title">大纲</div>
                <div id="outlineList"></div>
              </div>
              <div class="content">
                <div class="scroll" id="scrollContainer">
                  {bodyHtml}
                </div>
              </div>
              {InitScript(mermaidTheme)}
            </body>
            </html>
            """;
    }

    private static string BaseCss() => """
        html, body {
            margin: 0; padding: 0; height: 100%; overflow: hidden;
            background: transparent !important;
            font-family: -apple-system, "Segoe UI Variable", "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
            font-size: 15px; line-height: 1.7;
        }
        .content { height: 100%; overflow: hidden; }
        .scroll {
            height: 100%; overflow-y: auto;
            box-sizing: border-box; padding: 24px 28px 48px 28px;
        }
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: var(--scrollbar-track); border-radius: 4px; }
        ::-webkit-scrollbar-thumb { background: var(--scrollbar-thumb); border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--scrollbar-thumb-hover); }
        h1,h2,h3,h4,h5,h6 { margin: 24px 0 12px; line-height: 1.3; }
        h1 { font-size: 2em; border-bottom: 1px solid var(--border); padding-bottom: 8px; }
        h2 { font-size: 1.5em; border-bottom: 1px solid var(--border); padding-bottom: 6px; }
        p { margin: 0 0 12px; }
        img { max-width: 100%; height: auto; border-radius: 6px; margin: 12px 0; }
        a { text-decoration: none; }
        a:hover { text-decoration: underline; }
        blockquote {
            border-left: 4px solid var(--accent);
            margin: 12px 0; padding: 12px 16px;
            background: var(--blockquote-bg);
            border-radius: 0 6px 6px 0;
        }
        table { border-collapse: collapse; width: 100%; margin: 12px 0; }
        th, td { border: 1px solid var(--border); padding: 8px 12px; text-align: left; }
        th { background: var(--code-bg); font-weight: 600; }
        tr:nth-child(even) { background: var(--table-stripe); }
        code {
            background: var(--code-bg); padding: 2px 6px; border-radius: 4px;
            font-family: "Cascadia Code", "Fira Code", Consolas, monospace;
            font-size: 0.9em;
        }
        pre {
            position: relative; background: var(--code-bg);
            padding: 16px; border-radius: 8px; overflow-x: auto; margin: 12px 0;
        }
        pre code { background: transparent; padding: 0; border-radius: 0; font-size: 0.85em; }
        pre code.hljs { background: transparent; padding: 0; }
        .copy-button {
            position: absolute; top: 8px; right: 8px;
            background: var(--btn-bg); border: 1px solid var(--border);
            border-radius: 4px; padding: 3px 10px; font-size: 12px;
            cursor: pointer; color: var(--text); z-index: 10; opacity: 0;
            transition: opacity 0.15s;
        }
        pre:hover .copy-button { opacity: 1; }
        .copy-button:hover { background: var(--btn-hover); }
        .copy-button.copied { background: #4caf50; color: white; border-color: #4caf50; }
        .mermaid { text-align: center; margin: 16px 0; }
        .mermaid svg { max-width: 100%; }
        .katex-display { overflow-x: auto; padding: 8px 0; }
        .task-list-item { list-style: none; }
        .task-list-item input[type="checkbox"] { margin-right: 6px; }
        /* 大纲 */
        .outline-panel {
            display: none; position: fixed;
            left: 0; top: 0; bottom: 0; width: 240px;
            background: var(--bg); border-right: 1px solid var(--border);
            overflow-y: auto; padding: 16px 0; z-index: 1000;
            backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
        }
        .outline-panel.visible { display: block; }
        .outline-title {
            font-size: 12px; font-weight: 700; text-transform: uppercase;
            letter-spacing: 1px; padding: 0 16px 12px; color: var(--text-muted);
        }
        .outline-item {
            display: block; padding: 6px 16px; cursor: pointer;
            color: var(--text); font-size: 13px; text-decoration: none;
            border-left: 2px solid transparent;
            transition: background 0.15s, border-color 0.15s;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .outline-item:hover { background: var(--hover-bg); }
        .outline-item.active { border-left-color: var(--accent); color: var(--accent); }
        .outline-item.level-2 { padding-left: 28px; }
        .outline-item.level-3 { padding-left: 40px; font-size: 12px; }
        .outline-item.level-4 { padding-left: 52px; font-size: 12px; }
        .outline-toggle {
            display: none; position: fixed; left: 12px; top: 12px; z-index: 1001;
            width: 32px; height: 32px; border-radius: 6px;
            background: var(--btn-bg); border: 1px solid var(--border);
            color: var(--text); font-size: 16px; cursor: pointer;
            align-items: center; justify-content: center;
        }
        .outline-toggle:hover { background: var(--btn-hover); }
        .outline-toggle.visible { display: flex; }
        body.has-outline .content { margin-left: 240px; }
        body.has-outline .outline-toggle { left: 252px; }
        """;

    private static string GetThemeCss(string themeId, bool isDark)
    {
        return themeId switch
        {
            "dark" => """
                :root {
                    --bg: #1e1e1e; --text: #d4d4d4; --text-muted: #858585;
                    --heading: #ffffff; --accent: #569cd6; --link: #4fc1ff;
                    --code-bg: rgba(255,255,255,0.06); --blockquote-bg: rgba(255,255,255,0.04);
                    --border: rgba(255,255,255,0.1); --table-stripe: rgba(255,255,255,0.02);
                    --btn-bg: rgba(255,255,255,0.08); --btn-hover: rgba(255,255,255,0.12);
                    --hover-bg: rgba(255,255,255,0.04);
                    --scrollbar-track: #2d2d2d; --scrollbar-thumb: #424242; --scrollbar-thumb-hover: #555;
                }
                """,
            "github" => """
                :root {
                    --bg: #ffffff; --text: #24292e; --text-muted: #6a737d;
                    --heading: #24292e; --accent: #0366d6; --link: #0366d6;
                    --code-bg: #f6f8fa; --blockquote-bg: #f6f8fa;
                    --border: #e1e4e8; --table-stripe: #f6f8fa;
                    --btn-bg: #f6f8fa; --btn-hover: #e1e4e8;
                    --hover-bg: rgba(0,0,0,0.04);
                    --scrollbar-track: #f1f1f1; --scrollbar-thumb: #c1c1c1; --scrollbar-thumb-hover: #a8a8a8;
                }
                """,
            "solarized" => """
                :root {
                    --bg: #fdf6e3; --text: #657b83; --text-muted: #93a1a1;
                    --heading: #586e75; --accent: #268bd2; --link: #268bd2;
                    --code-bg: #eee8d5; --blockquote-bg: #eee8d5;
                    --border: #d3cbb7; --table-stripe: #eee8d5;
                    --btn-bg: #eee8d5; --btn-hover: #d3cbb7;
                    --hover-bg: rgba(0,0,0,0.04);
                    --scrollbar-track: #e6dfc2; --scrollbar-thumb: #d3ceb8; --scrollbar-thumb-hover: #c7c2b0;
                }
                """,
            "nord" => """
                :root {
                    --bg: #2e3440; --text: #d8dee9; --text-muted: #616e88;
                    --heading: #eceff4; --accent: #88c0d0; --link: #88c0d0;
                    --code-bg: #3b4252; --blockquote-bg: #3b4252;
                    --border: #434c5e; --table-stripe: #3b4252;
                    --btn-bg: #3b4252; --btn-hover: #434c5e;
                    --hover-bg: rgba(255,255,255,0.04);
                    --scrollbar-track: #3b4252; --scrollbar-thumb: #4c566a; --scrollbar-thumb-hover: #616e88;
                }
                """,
            "dracula" => """
                :root {
                    --bg: #282a36; --text: #f8f8f2; --text-muted: #6272a4;
                    --heading: #bd93f9; --accent: #ff79c6; --link: #8be9fd;
                    --code-bg: #44475a; --blockquote-bg: #44475a;
                    --border: #44475a; --table-stripe: #343746;
                    --btn-bg: #44475a; --btn-hover: #6272a4;
                    --hover-bg: rgba(255,255,255,0.05);
                    --scrollbar-track: #343746; --scrollbar-thumb: #6272a4; --scrollbar-thumb-hover: #8be9fd;
                }
                """,
            "monokai" => """
                :root {
                    --bg: #272822; --text: #f8f8f2; --text-muted: #75715e;
                    --heading: #a6e22e; --accent: #f92672; --link: #66d9ef;
                    --code-bg: #3e3d32; --blockquote-bg: #3e3d32;
                    --border: #49483e; --table-stripe: #3e3d32;
                    --btn-bg: #3e3d32; --btn-hover: #49483e;
                    --hover-bg: rgba(255,255,255,0.04);
                    --scrollbar-track: #3e3d32; --scrollbar-thumb: #75715e; --scrollbar-thumb-hover: #a6e22e;
                }
                """,
            "one-dark" => """
                :root {
                    --bg: #282c34; --text: #abb2bf; --text-muted: #5c6370;
                    --heading: #e06c75; --accent: #61afef; --link: #61afef;
                    --code-bg: #2c313c; --blockquote-bg: #2c313c;
                    --border: #3e4451; --table-stripe: #2c313c;
                    --btn-bg: #2c313c; --btn-hover: #3e4451;
                    --hover-bg: rgba(255,255,255,0.04);
                    --scrollbar-track: #2c313c; --scrollbar-thumb: #4b5263; --scrollbar-thumb-hover: #61afef;
                }
                """,
            _ => """
                :root {
                    --bg: #ffffff; --text: #333333; --text-muted: #888888;
                    --heading: #2c3e50; --accent: #3498db; --link: #3498db;
                    --code-bg: #f5f5f5; --blockquote-bg: #f9f9f9;
                    --border: #e8e8e8; --table-stripe: #fafafa;
                    --btn-bg: #f0f0f0; --btn-hover: #e0e0e0;
                    --hover-bg: rgba(0,0,0,0.03);
                    --scrollbar-track: #f1f1f1; --scrollbar-thumb: #c1c1c1; --scrollbar-thumb-hover: #a8a8a8;
                }
                """
        };
    }

    private static string InitScript(string mermaidTheme) => """
        <script>
        document.addEventListener("DOMContentLoaded", function() {
            // highlight.js
            document.querySelectorAll("pre code").forEach(function(block) {
                if (!block.classList.contains("language-mermaid")) {
                    try { hljs.highlightElement(block); } catch(e) {}
                }
            });

            // Mermaid
            var mermaidBlocks = document.querySelectorAll("pre code.language-mermaid");
            if (mermaidBlocks.length > 0) {
                try {
                    mermaid.initialize({ startOnLoad: false, theme: "__MERMAID_THEME__" });
                    mermaidBlocks.forEach(function(block, idx) {
                        var pre = block.parentElement;
                        var container = document.createElement("div");
                        container.className = "mermaid";
                        container.id = "mermaid-" + idx;
                        container.textContent = block.textContent;
                        pre.replaceWith(container);
                    });
                    mermaid.run();
                } catch(e) { console.warn("Mermaid init failed:", e); }
            }

            // KaTeX auto-render
            if (typeof renderMathInElement !== "undefined") {
                renderMathInElement(document.body, {
                    delimiters: [
                        {left: "$$", right: "$$", display: true},
                        {left: "$", right: "$", display: false},
                        {left: "\\(", right: "\\)", display: false},
                        {left: "\\[", right: "\\]", display: true}
                    ]
                });
            }

            // Copy buttons
            document.querySelectorAll("pre").forEach(function(pre) {
                var btn = document.createElement("button");
                btn.className = "copy-button";
                btn.textContent = "复制";
                pre.appendChild(btn);
                btn.addEventListener("click", function() {
                    var code = pre.querySelector("code");
                    if (!code) return;
                    navigator.clipboard.writeText(code.textContent).then(function() {
                        btn.textContent = "已复制";
                        btn.classList.add("copied");
                        setTimeout(function() { btn.textContent = "复制"; btn.classList.remove("copied"); }, 2000);
                    });
                });
            });

            // Outline
            buildOutline();
        });

        function syncScrollTo(ratio) {
            var el = document.querySelector(".scroll");
            if (el) { el.scrollTop = (el.scrollHeight - el.clientHeight) * ratio; }
        }

        function updateContent(html) {
            var el = document.getElementById("scrollContainer");
            if (!el) return;
            var ratio = el.scrollTop / Math.max(1, el.scrollHeight - el.clientHeight);
            el.innerHTML = html;
            // Re-run highlight
            document.querySelectorAll("pre code").forEach(function(block) {
                if (!block.classList.contains("language-mermaid")) {
                    try { hljs.highlightElement(block); } catch(e) {}
                }
            });
            // Re-run KaTeX
            if (typeof renderMathInElement !== "undefined") {
                renderMathInElement(el, {
                    delimiters: [
                        {left: "$$", right: "$$", display: true},
                        {left: "$", right: "$", display: false},
                        {left: "\\(", right: "\\)", display: false},
                        {left: "\\[", right: "\\]", display: true}
                    ]
                });
            }
            // Re-run copy buttons
            el.querySelectorAll("pre").forEach(function(pre) {
                if (pre.querySelector(".copy-button")) return;
                var btn = document.createElement("button");
                btn.className = "copy-button";
                btn.textContent = "复制";
                pre.appendChild(btn);
                btn.addEventListener("click", function() {
                    var code = pre.querySelector("code");
                    if (!code) return;
                    navigator.clipboard.writeText(code.textContent).then(function() {
                        btn.textContent = "已复制"; btn.classList.add("copied");
                        setTimeout(function() { btn.textContent = "复制"; btn.classList.remove("copied"); }, 2000);
                    });
                });
            });
            var maxScroll = el.scrollHeight - el.clientHeight;
            el.scrollTop = maxScroll * ratio;
            buildOutline();
        }

        function buildOutline() {
            var headings = document.querySelectorAll(".scroll h1, .scroll h2, .scroll h3, .scroll h4");
            var list = document.getElementById("outlineList");
            if (!list || headings.length === 0) return;
            list.innerHTML = "";
            headings.forEach(function(h, idx) {
                h.id = h.id || ("heading-" + idx);
                var level = parseInt(h.tagName.charAt(1));
                var a = document.createElement("a");
                a.className = "outline-item level-" + level;
                a.textContent = h.textContent;
                a.href = "#" + h.id;
                a.addEventListener("click", function(e) {
                    e.preventDefault();
                    h.scrollIntoView({ behavior: "smooth", block: "start" });
                    document.querySelectorAll(".outline-item.active").forEach(function(el) { el.classList.remove("active"); });
                    a.classList.add("active");
                });
                list.appendChild(a);
            });
        }

        function toggleOutline() {
            var panel = document.getElementById("outlinePanel");
            var btn = document.getElementById("outlineToggle");
            if (panel.classList.contains("visible")) {
                panel.classList.remove("visible");
                document.body.classList.remove("has-outline");
            } else {
                panel.classList.add("visible");
                document.body.classList.add("has-outline");
            }
        }
        document.getElementById("outlineToggle").addEventListener("click", toggleOutline);
        </script>
        """.Replace("__MERMAID_THEME__", mermaidTheme);
}

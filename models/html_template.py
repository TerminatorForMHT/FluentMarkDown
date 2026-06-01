"""预览 HTML 模板构建器"""


class PreviewHtmlBuilder:
    """将 Markdown 渲染后的 HTML 包装成完整的预览页面。

    Parameters
    ----------
    theme_styles : dict
        主题样式字典，包含 text_color / background_color / heading_color 等。
    font_size : int
        正文字号（px）。
    is_dark : bool
        是否暗色模式。
    border_radius : int
        预览容器圆角（px），默认 8。
    """

    HIGHLIGHT_CDN = "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0"
    MERMAID_CDN = "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"

    def __init__(self, theme_styles, font_size=16, is_dark=False, border_radius=8):
        self.ts = theme_styles
        self.font_size = font_size
        self.is_dark = is_dark
        self.radius = border_radius

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    def build(self, body_html):
        """构建完整的 HTML 页面字符串。"""
        return (
            self._head()
            + self._body(body_html)
            + self._scripts()
            + "\n</html>"
        )

    # ------------------------------------------------------------------
    # 私有：各段落构建
    # ------------------------------------------------------------------

    def _head(self):
        ts, dark = self.ts, self.is_dark
        hljs_theme = "github-dark" if dark else "github"
        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="{self.HIGHLIGHT_CDN}/styles/{hljs_theme}.min.css">
<script>
  if (typeof structuredClone === "undefined") {{
    window.structuredClone = function(obj) {{ return JSON.parse(JSON.stringify(obj)); }};
  }}
</script>
<script defer src="{self.HIGHLIGHT_CDN}/highlight.min.js"></script>
<script defer src="{self.MERMAID_CDN}"></script>
<style>
{self._css_base()}
{self._css_typography()}
{self._css_code()}
{self._css_misc()}
{self._css_outline()}
</style>
</head>"""

    def _body(self, body_html):
        return f"""
<body>
  <button class="outline-toggle" id="outlineToggle" title="大纲">☰</button>
  <div class="outline-panel" id="outlinePanel">
    <div class="outline-title">大纲</div>
    <div id="outlineList"></div>
  </div>
  <div class="content">
    <div class="scroll">
      {body_html}
    </div>
  </div>
</body>"""

    def _scripts(self):
        mermaid_theme = "dark" if self.is_dark else "default"
        return f"""
<script>
  document.addEventListener("DOMContentLoaded", function() {{
    // highlight.js
    document.querySelectorAll("pre code").forEach(function(block) {{
      if (!block.classList.contains("language-mermaid")) {{
        try {{ hljs.highlightElement(block); }} catch(e) {{}}
      }}
    }});

    // Mermaid
    var mermaidBlocks = document.querySelectorAll("pre code.language-mermaid");
    if (mermaidBlocks.length > 0) {{
      try {{
        mermaid.initialize({{ startOnLoad: false, theme: "{mermaid_theme}" }});
        mermaidBlocks.forEach(function(block, idx) {{
          var pre = block.parentElement;
          var container = document.createElement("div");
          container.className = "mermaid";
          container.id = "mermaid-" + idx;
          container.textContent = block.textContent;
          pre.replaceWith(container);
        }});
        mermaid.run();
      }} catch(e) {{ console.warn("Mermaid init failed:", e); }}
    }}

    // 复制按钮
    document.querySelectorAll("pre").forEach(function(pre) {{
      var btn = document.createElement("button");
      btn.className = "copy-button";
      btn.textContent = "复制";
      pre.appendChild(btn);
      btn.addEventListener("click", function() {{
        var code = pre.querySelector("code");
        if (!code) return;
        var ta = document.createElement("textarea");
        ta.value = code.textContent;
        ta.style.cssText = "position:fixed;left:-9999px;top:-9999px";
        document.body.appendChild(ta);
        ta.select();
        try {{
          document.execCommand("copy");
          btn.textContent = "已复制";
          btn.classList.add("copied");
        }} catch(e) {{ btn.textContent = "失败"; }}
        document.body.removeChild(ta);
        setTimeout(function() {{ btn.textContent = "复制"; btn.classList.remove("copied"); }}, 2000);
      }});
    }});
  }});

  function syncScrollTo(ratio) {{
    var el = document.querySelector(".scroll");
    if (el) {{ el.scrollTop = (el.scrollHeight - el.clientHeight) * ratio; }}
  }}

  function buildOutline() {{
    var headings = document.querySelectorAll(".scroll h1, .scroll h2, .scroll h3, .scroll h4");
    var list = document.getElementById("outlineList");
    if (!list || headings.length === 0) return;
    list.innerHTML = "";
    headings.forEach(function(h, idx) {{
      h.id = h.id || ("heading-" + idx);
      var level = parseInt(h.tagName.charAt(1));
      var a = document.createElement("a");
      a.className = "outline-item level-" + level;
      a.textContent = h.textContent;
      a.href = "#" + h.id;
      a.addEventListener("click", function(e) {{
        e.preventDefault();
        h.scrollIntoView({{ behavior: "smooth", block: "start" }});
        document.querySelectorAll(".outline-item.active").forEach(function(el) {{ el.classList.remove("active"); }});
        a.classList.add("active");
      }});
      list.appendChild(a);
    }});
  }}

  function showOutline() {{
    buildOutline();
    var panel = document.getElementById("outlinePanel");
    var btn = document.getElementById("outlineToggle");
    if (panel) {{ panel.classList.add("visible"); document.body.classList.add("has-outline"); }}
    if (btn) btn.classList.add("visible");
  }}
  function hideOutline() {{
    var panel = document.getElementById("outlinePanel");
    if (panel) {{ panel.classList.remove("visible"); document.body.classList.remove("has-outline"); }}
  }}
  function toggleOutline() {{
    var panel = document.getElementById("outlinePanel");
    if (panel && panel.classList.contains("visible")) {{ hideOutline(); }} else {{ showOutline(); }}
  }}
  document.getElementById("outlineToggle").addEventListener("click", toggleOutline);
</script>"""

    # ------------------------------------------------------------------
    # CSS 片段
    # ------------------------------------------------------------------

    def _css_base(self):
        ts, r = self.ts, self.radius
        return f"""
  html, body {{
    margin: 0; padding: 0; height: 100%; overflow: hidden;
    background: transparent !important;
    color: {ts["text_color"]};
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
    font-size: {self.font_size}px;
  }}
  .content {{
    height: 100%;
    background: {ts["background_color"]};
    border-top-right-radius: {r}px;
    border-bottom-right-radius: {r}px;
    overflow: hidden;
  }}
  .scroll {{
    height: 100%; overflow-y: auto;
    box-sizing: border-box; padding: 20px 20px 36px 20px;
  }}
  ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
  ::-webkit-scrollbar-track {{ background: {ts["scrollbar_track"]}; border-radius: 4px; }}
  ::-webkit-scrollbar-thumb {{ background: {ts["scrollbar_thumb"]}; border-radius: 4px; }}
  ::-webkit-scrollbar-thumb:hover {{ background: {ts["scrollbar_thumb_hover"]}; }}"""

    def _css_typography(self):
        ts = self.ts
        return f"""
  h1,h2,h3,h4,h5,h6 {{ color: {ts["heading_color"]}; margin: 20px 0 10px; }}
  p {{ margin: 0 0 10px; }}
  img {{ max-width: 100%; height: auto; border-radius: 4px; margin: 10px 0; }}
  a {{ color: {ts["link_color"]}; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  blockquote {{
    border-left: 4px solid rgba(100,149,237,0.5);
    margin: 10px 0; padding: 10px 15px;
    background: {ts["blockquote_bg"]};
  }}
  table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
  th, td {{ border: 1px solid rgba(0,0,0,0.12); padding: 8px; text-align: left; }}
  th {{ background: {ts["code_bg"]}; }}"""

    def _css_code(self):
        ts = self.ts
        return f"""
  code {{ background: {ts["code_bg"]}; padding: 2px 4px; border-radius: 3px; color: {ts["text_color"]}; }}
  pre {{ position: relative; background: {ts["code_bg"]}; padding: 10px; border-radius: 5px; overflow-x: auto; margin: 10px 0; color: {ts["text_color"]}; }}
  pre code {{ background: transparent; padding: 0; border-radius: 0; }}
  pre code.hljs {{ background: transparent; padding: 0; }}
  .copy-button {{ position: absolute; top: 5px; right: 5px; background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.3); border-radius: 3px; padding: 2px 6px; font-size: 12px; cursor: pointer; color: {ts["text_color"]}; z-index: 10; }}
  .copy-button:hover {{ background: rgba(255,255,255,0.3); }}
  .copy-button.copied {{ background: rgba(76,175,80,0.7); color: white; }}
  .mermaid {{ text-align: center; margin: 16px 0; }}
  .mermaid svg {{ max-width: 100%; }}"""

    def _css_misc(self):
        return ""

    def _d(self, dark_val, light_val):
        """暗色/亮色快捷选择"""
        return dark_val if self.is_dark else light_val

    def _css_outline(self):
        ts, d = self.ts, self._d
        return f"""
  .outline-panel {{
    display: none; position: fixed;
    left: 0; top: 0; bottom: 0; width: 240px;
    background: {ts["background_color"]};
    border-right: 1px solid {d("rgba(255,255,255,0.08)", "rgba(0,0,0,0.08)")};
    overflow-y: auto; padding: 16px 0; z-index: 1000;
    backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
    transition: transform 0.2s ease;
  }}
  .outline-panel.visible {{ display: block; }}
  .outline-title {{
    font-size: 13px; font-weight: 600;
    color: {d("rgba(255,255,255,0.5)", "rgba(0,0,0,0.4)")};
    padding: 0 16px 8px; text-transform: uppercase; letter-spacing: 0.5px;
  }}
  .outline-item {{
    display: block; padding: 5px 16px; cursor: pointer;
    color: {ts["text_color"]}; font-size: 13px; text-decoration: none;
    border-left: 2px solid transparent;
    transition: background 0.15s, border-color 0.15s;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }}
  .outline-item:hover {{ background: {d("rgba(255,255,255,0.06)", "rgba(0,0,0,0.04)")}; }}
  .outline-item.active {{
    border-left-color: {ts["link_color"]}; color: {ts["link_color"]};
    background: {d("rgba(255,255,255,0.04)", "rgba(0,0,0,0.02)")};
  }}
  .outline-item.level-2 {{ padding-left: 28px; }}
  .outline-item.level-3 {{ padding-left: 40px; font-size: 12px; }}
  .outline-item.level-4 {{ padding-left: 52px; font-size: 12px; }}
  .outline-toggle {{
    display: none; position: fixed; left: 12px; top: 12px; z-index: 1001;
    width: 32px; height: 32px; border-radius: 6px;
    background: {d("rgba(50,50,50,0.9)", "rgba(255,255,255,0.9)")};
    border: 1px solid {d("rgba(255,255,255,0.1)", "rgba(0,0,0,0.08)")};
    color: {ts["text_color"]}; font-size: 16px; cursor: pointer;
    align-items: center; justify-content: center;
    backdrop-filter: blur(10px); transition: background 0.15s;
  }}
  .outline-toggle:hover {{ background: {d("rgba(70,70,70,0.9)", "rgba(240,240,240,0.9)")}; }}
  .outline-toggle.visible {{ display: flex; }}
  body.has-outline .content {{ margin-left: 240px; }}
  body.has-outline .outline-toggle {{ left: 252px; }}
  .outline-panel::-webkit-scrollbar {{ width: 4px; }}
  .outline-panel::-webkit-scrollbar-track {{ background: transparent; }}
  .outline-panel::-webkit-scrollbar-thumb {{ background: {ts["scrollbar_thumb"]}; border-radius: 2px; }}"""

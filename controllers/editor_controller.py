import markdown
import os
import re


class EditorController:
    def __init__(self, document):
        self.document = document
        self.preview_theme = "light"
        self.font_size = 16
        self._last_md5 = None
        self._cached_html_template = None

    def set_content(self, content):
        self.document.content = content
        self.document.is_modified = True

    def get_content(self):
        return self.document.content

    def set_theme(self, theme):
        self.preview_theme = theme
        self._last_md5 = None
        self._cached_html_template = None

    def set_font_size(self, size):
        self.font_size = size
        self._last_md5 = None
        self._cached_html_template = None

    def _convert_image_paths(self, html):
        """将 HTML 中的图片路径转换为 file:// 协议"""
        from PyQt5.QtCore import QUrl
        
        # 获取当前文档所在目录
        base_dir = os.path.dirname(self.document.file_path) if self.document.file_path else os.getcwd()
        
        # 匹配 <img> 标签的 src 属性
        def replace_path(match):
            src = match.group(1)
            # 如果已经是 http/https/data 协议，保持原样
            if src.startswith(('http://', 'https://', 'data:', 'file://')):
                return f'<img src="{src}"'
            
            # 如果是绝对路径（Windows 或 Unix）
            if os.path.isabs(src):
                file_url = QUrl.fromLocalFile(src).toString()
                return f'<img src="{file_url}"'
            
            # 如果是相对路径，基于文档目录解析
            full_path = os.path.normpath(os.path.join(base_dir, src))
            if os.path.exists(full_path):
                file_url = QUrl.fromLocalFile(full_path).toString()
                return f'<img src="{file_url}"'
            
            # 如果路径不存在，保持原样
            return f'<img src="{src}"'
        
        # 使用正则替换图片路径
        html = re.sub(r'<img\s+src="([^"]+)"', replace_path, html)
        return html

    def render_preview(self, is_dark=False):
        ts = self._get_theme_styles(is_dark)
        # 添加更多扩展支持图片和其他格式
        html = markdown.markdown(self.document.content, extensions=['fenced_code', 'extra', 'tables'])
        # 转换图片路径为 file:// 协议
        html = self._convert_image_paths(html)
        return self._build_html(html, ts, is_dark)

    def _get_theme_styles(self, is_dark):
        from models.themes import PreviewThemes
        ts = PreviewThemes.get_theme_styles(self.preview_theme)
        
        if self.preview_theme == "light" and is_dark:
            ts["text_color"] = "#e0e0e0"
            ts["heading_color"] = "#ffffff"
            ts["code_bg"] = "rgba(255, 255, 255, 0.1)"
            ts["blockquote_bg"] = "rgba(255, 255, 255, 0.05)"
            ts["scrollbar_track"] = "#3d3d3d"
            ts["scrollbar_thumb"] = "#5d5d5d"
            ts["scrollbar_thumb_hover"] = "#7d7d7d"
            ts["link_color"] = "#64b5f6"
        
        return ts

    def _build_html(self, html, ts, is_dark=False):
        r = 8
        styled_html = '''
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/''' + ('github-dark' if is_dark else 'github') + '''.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<style>
  html, body {
    margin: 0;
    padding: 0;
    height: 100%;
    overflow: hidden;
    background: transparent !important;
    color: ''' + ts["text_color"] + ''';
    font-family: Arial, sans-serif;
    font-size: ''' + str(self.font_size) + '''px;
  }

  .content {
    height: 100%;
    background: ''' + ts["background_color"] + ''';
    border-top-right-radius: ''' + str(r) + '''px;
    border-bottom-right-radius: ''' + str(r) + '''px;
    overflow: hidden;
  }

  .scroll {
    height: 100%;
    overflow-y: auto;
    box-sizing: border-box;
    padding: 20px 20px 36px 20px;
  }

  ::-webkit-scrollbar { width: 8px; height: 8px; }
  ::-webkit-scrollbar-track { background: ''' + ts["scrollbar_track"] + '''; border-radius: 4px; }
  ::-webkit-scrollbar-thumb { background: ''' + ts["scrollbar_thumb"] + '''; border-radius: 4px; }
  ::-webkit-scrollbar-thumb:hover { background: ''' + ts["scrollbar_thumb_hover"] + '''; }

  h1,h2,h3,h4,h5,h6 { color: ''' + ts["heading_color"] + '''; margin: 20px 0 10px; }
  p { margin: 0 0 10px; }
  img { max-width: 100%; height: auto; border-radius: 4px; margin: 10px 0; }

  code { background: ''' + ts["code_bg"] + '''; padding: 2px 4px; border-radius: 3px; color: ''' + ts["text_color"] + '''; }
  pre { position: relative; background: ''' + ts["code_bg"] + '''; padding: 10px; border-radius: 5px; overflow-x: auto; margin: 10px 0; color: ''' + ts["text_color"] + '''; }
  pre code { background: transparent; padding: 0; border-radius: 0; }
  pre code.hljs { background: transparent; padding: 0; }
  .copy-button { position: absolute; top: 5px; right: 5px; background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.3); border-radius: 3px; padding: 2px 6px; font-size: 12px; cursor: pointer; color: ''' + ts["text_color"] + '''; z-index: 10; }
  .copy-button:hover { background: rgba(255,255,255,0.3); }
  .copy-button.copied { background: rgba(76,175,80,0.7); color: white; }
  .mermaid { text-align: center; margin: 16px 0; }
  .mermaid svg { max-width: 100%; }

  blockquote {
    border-left: 4px solid rgba(100,149,237,0.5);
    margin: 10px 0;
    padding: 10px 15px;
    background: ''' + ts["blockquote_bg"] + ''';
  }

  a { color: ''' + ts["link_color"] + '''; text-decoration: none; }
  a:hover { text-decoration: underline; }

  table { border-collapse: collapse; width: 100%; margin: 10px 0; }
  th, td { border: 1px solid rgba(0,0,0,0.12); padding: 8px; text-align: left; }
  th { background: ''' + ts["code_bg"] + '''; }
</style>
</head>
<body>
  <div class="content">
    <div class="scroll">
      ''' + html + '''
    </div>
  </div>
</body>
<script>
  document.addEventListener("DOMContentLoaded", function() {
    // --- highlight.js: 代码块语法高亮 ---
    document.querySelectorAll("pre code").forEach(function(block) {
      if (!block.classList.contains("language-mermaid")) {
        try { hljs.highlightElement(block); } catch(e) {}
      }
    });

    // --- Mermaid: 图表渲染 ---
    var mermaidBlocks = document.querySelectorAll("pre code.language-mermaid");
    if (mermaidBlocks.length > 0) {
      try {
        mermaid.initialize({ startOnLoad: false, theme: "''' + ('dark' if is_dark else 'default') + '''" });
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

    // --- 复制按钮 ---
    document.querySelectorAll("pre").forEach(function(pre) {
      var btn = document.createElement("button");
      btn.className = "copy-button";
      btn.textContent = "复制";
      pre.appendChild(btn);
      btn.addEventListener("click", function() {
        var code = pre.querySelector("code");
        if (!code) return;
        var text = code.textContent;
        var ta = document.createElement("textarea");
        ta.value = text;
        ta.style.cssText = "position:fixed;left:-9999px;top:-9999px";
        document.body.appendChild(ta);
        ta.select();
        try {
          document.execCommand("copy");
          btn.textContent = "已复制";
          btn.classList.add("copied");
        } catch(e) {
          btn.textContent = "失败";
        }
        document.body.removeChild(ta);
        setTimeout(function() { btn.textContent = "复制"; btn.classList.remove("copied"); }, 2000);
      });
    });
  });

  // --- 同步滚动：接收来自 Qt 的滚动比例 ---
  function syncScrollTo(ratio) {
    var el = document.querySelector(".scroll");
    if (el) {
      var maxScroll = el.scrollHeight - el.clientHeight;
      el.scrollTop = maxScroll * ratio;
    }
  }
</script>
</html>
'''
        return styled_html

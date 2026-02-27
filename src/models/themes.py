class PreviewThemes:
    """
    预览窗口主题配置
    """

    @staticmethod
    def get_theme_styles(theme_name):
        """
        获取主题样式
        Args:
            theme_name: 主题名称 (light, dark, github, solarized, ...)
        Returns:
            dict
        """
        themes = {
            "light": {
                "name": "浅色",
                "background_color": "transparent",
                "text_color": "#333333",
                "heading_color": "#2c3e50",
                "code_bg": "rgba(240, 240, 240, 0.8)",
                "blockquote_bg": "rgba(240, 240, 240, 0.5)",
                "scrollbar_track": "#f1f1f1",
                "scrollbar_thumb": "#c1c1c1",
                "scrollbar_thumb_hover": "#a8a8a8",
                "link_color": "#3498db"
            },
            "dark": {
                "name": "深色",
                "background_color": "#2d2d2d",
                "text_color": "#e0e0e0",
                "heading_color": "#ffffff",
                "code_bg": "rgba(255, 255, 255, 0.1)",
                "blockquote_bg": "rgba(255, 255, 255, 0.05)",
                "scrollbar_track": "#3d3d3d",
                "scrollbar_thumb": "#5d5d5d",
                "scrollbar_thumb_hover": "#7d7d7d",
                "link_color": "#64b5f6"
            },
            "github": {
                "name": "GitHub",
                "background_color": "#ffffff",
                "text_color": "#24292e",
                "heading_color": "#24292e",
                "code_bg": "#f6f8fa",
                "blockquote_bg": "#f6f8fa",
                "scrollbar_track": "#f1f1f1",
                "scrollbar_thumb": "#c1c1c1",
                "scrollbar_thumb_hover": "#a8a8a8",
                "link_color": "#0366d6"
            },
            "solarized": {
                "name": "Solarized",
                "background_color": "#fdf6e3",
                "text_color": "#657b83",
                "heading_color": "#586e75",
                "code_bg": "#eee8d5",
                "blockquote_bg": "#eee8d5",
                "scrollbar_track": "#e6dfc2",
                "scrollbar_thumb": "#d3ceb8",
                "scrollbar_thumb_hover": "#c7c2b0",
                "link_color": "#268bd2"
            },
            "chinese": {
                "name": "国风",
                "background_color": "#f9f2e8",
                "text_color": "#8b4513",
                "heading_color": "#a0522d",
                "code_bg": "rgba(160, 82, 45, 0.1)",
                "blockquote_bg": "rgba(160, 82, 45, 0.05)",
                "scrollbar_track": "#f0e6d2",
                "scrollbar_thumb": "#d4a76a",
                "scrollbar_thumb_hover": "#b8860b",
                "link_color": "#cd853f"
            },
            "midnight": {
                "name": "午夜蓝",
                "background_color": "#1a237e",
                "text_color": "#e3f2fd",
                "heading_color": "#ffffff",
                "code_bg": "rgba(255, 255, 255, 0.1)",
                "blockquote_bg": "rgba(255, 255, 255, 0.05)",
                "scrollbar_track": "#283593",
                "scrollbar_thumb": "#3949ab",
                "scrollbar_thumb_hover": "#303f9f",
                "link_color": "#82b1ff"
            },
            "forest": {
                "name": "森林绿",
                "background_color": "#1b5e20",
                "text_color": "#e8f5e8",
                "heading_color": "#ffffff",
                "code_bg": "rgba(255, 255, 255, 0.1)",
                "blockquote_bg": "rgba(255, 255, 255, 0.05)",
                "scrollbar_track": "#2e7d32",
                "scrollbar_thumb": "#388e3c",
                "scrollbar_thumb_hover": "#2e7d32",
                "link_color": "#81c784"
            },
            "ocean": {
                "name": "海洋蓝",
                "background_color": "#01579b",
                "text_color": "#e1f5fe",
                "heading_color": "#ffffff",
                "code_bg": "rgba(255, 255, 255, 0.1)",
                "blockquote_bg": "rgba(255, 255, 255, 0.05)",
                "scrollbar_track": "#0277bd",
                "scrollbar_thumb": "#0288d1",
                "scrollbar_thumb_hover": "#039be5",
                "link_color": "#4fc3f7"
            },
            "purple": {
                "name": "紫色调",
                "background_color": "#4a148c",
                "text_color": "#f3e5f5",
                "heading_color": "#ffffff",
                "code_bg": "rgba(255, 255, 255, 0.1)",
                "blockquote_bg": "rgba(255, 255, 255, 0.05)",
                "scrollbar_track": "#6a1b9a",
                "scrollbar_thumb": "#7b1fa2",
                "scrollbar_thumb_hover": "#4a148c",
                "link_color": "#ba68c8"
            },
            "neon": {
                "name": "霓虹",
                "background_color": "#1a1a2e",
                "text_color": "#f0f0f0",
                "heading_color": "#00ffea",
                "code_bg": "rgba(0, 255, 234, 0.1)",
                "blockquote_bg": "rgba(0, 255, 234, 0.05)",
                "scrollbar_track": "#16213e",
                "scrollbar_thumb": "#0f3460",
                "scrollbar_thumb_hover": "#1a1a2e",
                "link_color": "#00ffea"
            }
        }

        return themes.get(theme_name, themes["light"])

    @staticmethod
    def get_available_themes():
        return ["light", "dark", "github", "solarized", "chinese", "midnight", "forest", "ocean", "purple", "neon"]

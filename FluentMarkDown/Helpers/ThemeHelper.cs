using Microsoft.UI.Xaml;

namespace FluentMarkDown.Helpers;

/// <summary>
/// WinUI 3 主题切换辅助
/// </summary>
public static class ThemeHelper
{
    public static ElementTheme GetCurrentTheme()
    {
        if (Application.Current is App app)
        {
            return app.RequestedAppTheme switch
            {
                ApplicationTheme.Dark => ElementTheme.Dark,
                ApplicationTheme.Light => ElementTheme.Light,
                _ => ElementTheme.Default,
            };
        }
        return ElementTheme.Default;
    }

    public static bool IsDarkMode()
    {
        var theme = GetCurrentTheme();
        if (theme == ElementTheme.Default)
        {
            // 跟随系统
            return Application.Current.RequestedTheme == ApplicationTheme.Dark;
        }
        return theme == ElementTheme.Dark;
    }
}

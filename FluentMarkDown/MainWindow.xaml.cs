using System.Text.Json;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Input;
using Microsoft.Web.WebView2.Core;
using FluentMarkDown.ViewModels;
using Windows.System;

namespace FluentMarkDown;

public sealed partial class MainWindow : Window
{
    public MainViewModel ViewModel { get; }

    private bool _editorReady;
    private bool _previewReady;
    private bool _isSplitterDragging;
    private double _dragStartX;
    private DispatcherTimer? _previewDebounce;
    private string _pendingContent = string.Empty;

    public MainWindow(MainViewModel viewModel)
    {
        ViewModel = viewModel;
        InitializeComponent();

        // 自定义标题栏
        ExtendsContentIntoTitleBar = true;
        SetTitleBar(AppTitleBar);

        // 窗口大小
        AppWindow.Resize(new Windows.Graphics.SizeInt32(1280, 800));

        // 快捷键
        var accelerator = new KeyboardAccelerator();
        // 快捷键通过 KeyDown 事件处理更灵活

        // 初始化 WebView2
        _ = InitializeEditorAsync();
        _ = InitializePreviewAsync();

        // 预览防抖定时器
        _previewDebounce = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(300) };
        _previewDebounce.Tick += OnPreviewDebounceTick;

        // 监听 AI 插入事件
        ViewModel.PropertyChanged += OnViewModelPropertyChanged;

        // 窗口关闭事件
        AppWindow.Closing += OnWindowClosing;
    }

    // ══════════════════════════ WebView2 初始化 ══════════════════════════

    private async Task InitializeEditorAsync()
    {
        await EditorWebView.EnsureCoreWebView2Async();

        var coreWebView = EditorWebView.CoreWebView2;
        coreWebView.Settings.AreDefaultContextMenusEnabled = false;
        coreWebView.Settings.IsStatusBarEnabled = false;

        // 监听来自 Monaco 的消息
        coreWebView.WebMessageReceived += OnEditorMessageReceived;

        // 加载 Monaco Editor HTML
        var monacoHtml = Path.Combine(AppContext.BaseDirectory, "Assets", "WebView", "monaco", "index.html");
        if (File.Exists(monacoHtml))
        {
            var html = await File.ReadAllTextAsync(monacoHtml);
            coreWebView.NavigateToString(html);
        }

        _editorReady = true;
    }

    private async Task InitializePreviewAsync()
    {
        await PreviewWebView.EnsureCoreWebView2Async();

        var coreWebView = PreviewWebView.CoreWebView2;
        coreWebView.Settings.AreDefaultContextMenusEnabled = false;
        coreWebView.Settings.IsStatusBarEnabled = false;

        // 外部链接用系统浏览器打开
        coreWebView.NewWindowRequested += (_, args) =>
        {
            args.Handled = true;
            _ = Launcher.LaunchUriAsync(new Uri(args.Uri));
        };

        _previewReady = true;
    }

    // ══════════════════════════ Monaco 通信 ══════════════════════════

    private void OnEditorMessageReceived(CoreWebView2 sender, CoreWebView2WebMessageReceivedEventArgs args)
    {
        var json = args.WebMessageAsJson;
        using var doc = JsonDocument.Parse(json);
        var root = doc.RootElement;

        if (!root.TryGetProperty("type", out var typeEl)) return;
        var type = typeEl.GetString();

        switch (type)
        {
            case "contentChanged":
                if (root.TryGetProperty("content", out var contentEl))
                {
                    var content = contentEl.GetString() ?? string.Empty;
                    _pendingContent = content;

                    if (ViewModel.HasContentChanged(content))
                    {
                        _previewDebounce!.Stop();
                        _previewDebounce.Start();
                    }

                    ViewModel.OnContentChanged(content);
                }
                break;

            case "ready":
                // Monaco 加载完成，如果有文档内容则设置
                if (ViewModel.HasDocument && !string.IsNullOrEmpty(ViewModel.Document.Content))
                {
                    SetEditorContent(ViewModel.Document.Content);
                }
                break;
        }
    }

    private void SetEditorContent(string content)
    {
        if (!_editorReady) return;
        var escaped = content
            .Replace("\\", "\\\\")
            .Replace("`", "\\`")
            .Replace("$", "\\$");
        EditorWebView.CoreWebView2.PostWebMessageAsJson(
            $$"""{"type":"setContent","content":`{{escaped}}`}""");
    }

    private void ExecuteEditorCommand(string command)
    {
        if (!_editorReady) return;
        EditorWebView.CoreWebView2.PostWebMessageAsJson(
            $$"""{"type":"command","command":"{{command}}"}""");
    }

    // ══════════════════════════ 预览更新 ══════════════════════════

    private void OnPreviewDebounceTick(object? sender, object e)
    {
        _previewDebounce!.Stop();
        UpdatePreview(_pendingContent);
    }

    private void UpdatePreview(string content)
    {
        if (!_previewReady) return;

        if (string.IsNullOrEmpty(ViewModel.Document.FilePath) && content == ViewModel.Document.Content
            && ViewModel.CharCount == 0)
        {
            // 首次加载，完整渲染
            var html = ViewModel.BuildFullPreview();
            PreviewWebView.CoreWebView2.NavigateToString(html);
        }
        else
        {
            // 增量更新：通过 JS 替换 DOM
            var bodyHtml = ViewModel.GetIncrementalHtml();
            var escaped = bodyHtml
                .Replace("\\", "\\\\")
                .Replace("`", "\\`")
                .Replace("$", "\\$");
            var js = $"updateContent(`{escaped}`);";
            _ = PreviewWebView.CoreWebView2.ExecuteScriptAsync(js);
        }
    }

    /// <summary>
    /// 强制完整刷新预览（主题切换时调用）
    /// </summary>
    private void FullRefreshPreview()
    {
        if (!_previewReady) return;
        var html = ViewModel.BuildFullPreview();
        PreviewWebView.CoreWebView2.NavigateToString(html);
    }

    // ══════════════════════════ 编辑器滚动同步 ══════════════════════════

    private void SyncPreviewScroll(double ratio)
    {
        if (!_previewReady) return;
        _ = PreviewWebView.CoreWebView2.ExecuteScriptAsync($"syncScrollTo({ratio});");
    }

    // ══════════════════════════ 命令栏事件 ══════════════════════════

    private void OnOpenFileClick(object sender, RoutedEventArgs e) => _ = ViewModel.OpenFileAsync();
    private void OnSaveFileClick(object sender, RoutedEventArgs e) => _ = ViewModel.SaveFileAsync();
    private void OnSaveAsClick(object sender, RoutedEventArgs e) => _ = ViewModel.SaveFileAsync(saveAs: true);
    private void OnExportClick(object sender, RoutedEventArgs e) => _ = ViewModel.ExportAsync();
    private void OnFindClick(object sender, RoutedEventArgs e) => ExecuteEditorCommand("find");

    private void OnBoldClick(object sender, RoutedEventArgs e) => ExecuteEditorCommand("bold");
    private void OnItalicClick(object sender, RoutedEventArgs e) => ExecuteEditorCommand("italic");
    private void OnCodeClick(object sender, RoutedEventArgs e) => ExecuteEditorCommand("code");
    private void OnLinkClick(object sender, RoutedEventArgs e) => ExecuteEditorCommand("link");

    private void OnThemeChanged(object sender, SelectionChangedEventArgs e)
    {
        if (ViewModel.HasDocument)
        {
            FullRefreshPreview();
        }
    }

    private void OnSettingsClick(object sender, RoutedEventArgs e)
    {
        // TODO: 打开设置 Flyout 或新窗口
    }

    private void OnAboutClick(object sender, RoutedEventArgs e)
    {
        // TODO: 关于对话框
    }

    // ══════════════════════════ AI 面板 ══════════════════════════

    private void OnClearAiClick(object sender, RoutedEventArgs e) => ViewModel.ClearAiHistoryCommand.Execute(null);
    private void OnCloseAiClick(object sender, RoutedEventArgs e) => ViewModel.IsAiPanelOpen = false;

    private void OnViewModelPropertyChanged(object? sender, System.ComponentModel.PropertyChangedEventArgs e)
    {
        if (e.PropertyName == nameof(ViewModel.AiInsertContent) && !string.IsNullOrEmpty(ViewModel.AiInsertContent))
        {
            // 将 AI 输出插入到编辑器光标位置
            ExecuteEditorCommand("insert:" + ViewModel.AiInsertContent);
            ViewModel.AiInsertContent = string.Empty;
        }

        if (e.PropertyName == nameof(ViewModel.HasDocument))
        {
            WelcomePanel.Visibility = ViewModel.HasDocument ? Visibility.Collapsed : Visibility.Visible;
            EditorPanel.Visibility = ViewModel.HasDocument ? Visibility.Visible : Visibility.Collapsed;

            if (ViewModel.HasDocument)
            {
                SetEditorContent(ViewModel.Document.Content);
                FullRefreshPreview();
            }
        }

        if (e.PropertyName == nameof(ViewModel.IsEditorFullscreen))
        {
            if (ViewModel.IsEditorFullscreen)
            {
                PreviewColumn.Width = new GridLength(0);
            }
            else if (!ViewModel.IsPreviewFullscreen)
            {
                EditorColumn.Width = new GridLength(1, GridUnitType.Star);
                PreviewColumn.Width = new GridLength(1, GridUnitType.Star);
            }
        }

        if (e.PropertyName == nameof(ViewModel.IsPreviewFullscreen))
        {
            if (ViewModel.IsPreviewFullscreen)
            {
                EditorColumn.Width = new GridLength(0);
            }
            else if (!ViewModel.IsEditorFullscreen)
            {
                EditorColumn.Width = new GridLength(1, GridUnitType.Star);
                PreviewColumn.Width = new GridLength(1, GridUnitType.Star);
            }
        }
    }

    // ══════════════════════════ 分割条拖拽 ══════════════════════════

    private void OnSplitterPointerPressed(object sender, PointerRoutedEventArgs e)
    {
        _isSplitterDragging = true;
        _dragStartX = e.GetCurrentPoint(EditorPanel).Position.X;
        ((UIElement)sender).CapturePointer(e.Pointer);
    }

    private void OnSplitterPointerMoved(object sender, PointerRoutedEventArgs e)
    {
        if (!_isSplitterDragging) return;
        var currentX = e.GetCurrentPoint(EditorPanel).Position.X;
        var totalWidth = EditorPanel.ActualWidth;
        if (totalWidth <= 0) return;

        var ratio = Math.Clamp(currentX / totalWidth, 0.2, 0.8);
        EditorColumn.Width = new GridLength(ratio, GridUnitType.Star);
        PreviewColumn.Width = new GridLength(1 - ratio, GridUnitType.Star);
    }

    private void OnSplitterPointerReleased(object sender, PointerRoutedEventArgs e)
    {
        _isSplitterDragging = false;
        ((UIElement)sender).ReleasePointerCapture(e.Pointer);
    }

    // ══════════════════════════ 窗口关闭 ══════════════════════════

    private async void OnWindowClosing(Microsoft.UI.Windowing.AppWindow sender,
        Microsoft.UI.Windowing.AppWindowClosingEventArgs args)
    {
        if (ViewModel.Document.IsModified)
        {
            args.Cancel = true;
            var canClose = await ViewModel.CheckSaveOnCloseAsync();
            if (canClose)
            {
                ViewModel.StopAutoSave();
                App.Current.Exit();
            }
        }
        else
        {
            ViewModel.StopAutoSave();
        }
    }

    // ══════════════════════════ 导航拦截 ══════════════════════════

    private void OnEditorNavigationStarting(CoreWebView2 sender, CoreWebView2NavigationStartingEventArgs args)
    {
        // 仅允许初始本地页面加载
        if (args.Uri is not null && !args.Uri.StartsWith("about:"))
        {
            args.Cancel = true;
        }
    }

    // ══════════════════════════ 快捷键 ══════════════════════════

    // WinUI 3 的全局快捷键通过 InputKeyboardSource 或在 App 层注册
    // 这里通过 WebView2 的 AcceleratorKeyPressed 处理
}

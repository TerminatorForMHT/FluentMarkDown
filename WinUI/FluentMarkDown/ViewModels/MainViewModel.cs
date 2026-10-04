using System.Collections.ObjectModel;
using System.Text;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using FluentMarkDown.Models;
using FluentMarkDown.Services;
using Windows.Storage.Pickers;
using Microsoft.UI.Xaml;

namespace FluentMarkDown.ViewModels;

/// <summary>
/// 主视图模型 —— 协调编辑器、预览、AI 和文件操作
/// </summary>
public partial class MainViewModel : ObservableObject
{
    private readonly DocumentModel _document;
    private readonly AppSettings _settings;
    private readonly PreviewService _previewService;
    private readonly ExportService _exportService;
    private readonly AiAgentService _aiService;
    private readonly RecentFilesManager _recentFiles;

    // ── 可观察属性 ──

    [ObservableProperty] private string _title = "FluentMarkDown";
    [ObservableProperty] private bool _hasDocument;
    [ObservableProperty] private string _statusText = "就绪";
    [ObservableProperty] private int _charCount;
    [ObservableProperty] private int _lineCount;
    [ObservableProperty] private int _selectedCount;
    [ObservableProperty] private string _currentTheme = "default";
    [ObservableProperty] private bool _isPreviewVisible = true;
    [ObservableProperty] private bool _isEditorFullscreen;
    [ObservableProperty] private bool _isPreviewFullscreen;
    [ObservableProperty] private double _splitterPosition = 0.5;

    // ── AI 相关 ──
    [ObservableProperty] private bool _isAiPanelOpen;
    [ObservableProperty] private string _aiInput = string.Empty;
    [ObservableProperty] private string _aiOutput = string.Empty;
    [ObservableProperty] private bool _isAiBusy;
    [ObservableProperty] private ObservableCollection<string> _aiHistory = new();

    private readonly List<AiMessage> _aiMessages = new();
    private string _lastContentMd5 = string.Empty;
    private DispatcherTimer? _autoSaveTimer;
    private CancellationTokenSource? _aiCts;

    public MainViewModel(
        DocumentModel document,
        AppSettings settings,
        PreviewService previewService,
        ExportService exportService,
        AiAgentService aiService,
        RecentFilesManager recentFiles)
    {
        _document = document;
        _settings = settings;
        _previewService = previewService;
        _exportService = exportService;
        _aiService = aiService;
        _recentFiles = recentFiles;

        CurrentTheme = _settings.PreviewTheme;
        InitAiMessages();
    }

    public DocumentModel Document => _document;
    public AppSettings Settings => _settings;
    public RecentFilesManager RecentFiles => _recentFiles;
    public IReadOnlyList<ThemeInfo> Themes => PreviewThemes.All;

    // ══════════════════════════ 文件操作 ══════════════════════════

    [RelayCommand]
    private void NewFile()
    {
        _document.New();
        HasDocument = true;
        UpdateTitle();
        StartAutoSave();
    }

    public async Task OpenFileAsync(string? filePath = null)
    {
        if (filePath is null)
        {
            var picker = new FileOpenPicker();
            var hwnd = WinRT.Interop.WindowNative.GetWindowHandle(App.MainWindow);
            WinRT.Interop.InitializeWithWindow.Initialize(picker, hwnd);
            picker.FileTypeFilter.Add(".md");
            picker.FileTypeFilter.Add(".markdown");
            picker.FileTypeFilter.Add("*");
            var file = await picker.PickSingleFileAsync();
            if (file is null) return;
            filePath = file.Path;
        }

        if (_document.Load(filePath))
        {
            _recentFiles.Add(filePath);
            HasDocument = true;
            _lastContentMd5 = string.Empty; // 强制刷新预览
            UpdateTitle();
            StartAutoSave();
            StatusText = $"已打开: {Path.GetFileName(filePath)}";
        }
        else
        {
            StatusText = "打开文件失败";
        }
    }

    public async Task SaveFileAsync(bool saveAs = false)
    {
        if (!_document.HasFile) return;

        if (saveAs || _document.FilePath is null)
        {
            var picker = new FileSavePicker();
            var hwnd = WinRT.Interop.WindowNative.GetWindowHandle(App.MainWindow);
            WinRT.Interop.InitializeWithWindow.Initialize(picker, hwnd);
            picker.FileTypeChoices.Add("Markdown", new List<string> { ".md" });
            picker.FileTypeChoices.Add("所有文件", new List<string> { ".*" });
            picker.SuggestedFileName = _document.FileName;
            var file = await picker.PickSaveFileAsync();
            if (file is null) return;
            _document.Save(file.Path);
            _recentFiles.Add(file.Path);
        }
        else
        {
            _document.Save();
        }

        _lastContentMd5 = string.Empty;
        UpdateTitle();
        StatusText = "已保存";
    }

    public async Task<bool> CheckSaveOnCloseAsync()
    {
        if (!_document.HasFile || !_document.IsModified) return true;

        var dialog = new Microsoft.UI.Xaml.Controls.ContentDialog
        {
            Title = "文件已修改",
            Content = $"是否保存对 {_document.FileName} 的更改？",
            PrimaryButtonText = "保存",
            SecondaryButtonText = "不保存",
            CloseButtonText = "取消",
            XamlRoot = App.MainWindow.Content.XamlRoot,
        };

        var result = await dialog.ShowAsync();
        if (result == Microsoft.UI.Xaml.Controls.ContentDialogResult.Primary)
        {
            await SaveFileAsync();
            return true;
        }
        if (result == Microsoft.UI.Xaml.Controls.ContentDialogResult.Secondary)
            return true;
        return false; // 取消
    }

    // ══════════════════════════ 编辑器事件 ══════════════════════════

    /// <summary>
    /// 当 Monaco 编辑器内容变化时由 View 层调用
    /// </summary>
    public void OnContentChanged(string newContent)
    {
        _document.Content = newContent;
        _document.IsModified = true;
        CharCount = newContent.Length;
        LineCount = newContent.Split('\n').Length;
        UpdateTitle();
    }

    /// <summary>
    /// 判断内容是否真的变化了（MD5 去重）
    /// </summary>
    public bool HasContentChanged(string content)
    {
        var md5 = Helpers.HashHelper.Md5(content);
        if (md5 == _lastContentMd5) return false;
        _lastContentMd5 = md5;
        return true;
    }

    // ══════════════════════════ 预览 ══════════════════════════

    /// <summary>
    /// 构建完整预览 HTML（首次加载 / 主题切换）
    /// </summary>
    public string BuildFullPreview()
    {
        var isDark = Helpers.ThemeHelper.IsDarkMode();
        return _previewService.BuildFullPreview(_document.Content, CurrentTheme, isDark);
    }

    /// <summary>
    /// 增量更新 —— 仅返回 body HTML
    /// </summary>
    public string GetIncrementalHtml()
    {
        return _previewService.GetBodyHtml(_document.Content);
    }

    [RelayCommand]
    private void ChangeTheme(string themeId)
    {
        CurrentTheme = themeId;
        _settings.PreviewTheme = themeId;
        _settings.Save();
        _lastContentMd5 = string.Empty; // 强制完整刷新
    }

    [RelayCommand]
    private void TogglePreview()
    {
        IsPreviewVisible = !IsPreviewVisible;
        IsEditorFullscreen = !IsPreviewVisible;
        IsPreviewFullscreen = false;
    }

    [RelayCommand]
    private void ToggleEditorFullscreen()
    {
        IsEditorFullscreen = !IsEditorFullscreen;
        if (IsEditorFullscreen) IsPreviewFullscreen = false;
    }

    [RelayCommand]
    private void TogglePreviewFullscreen()
    {
        IsPreviewFullscreen = !IsPreviewFullscreen;
        if (IsPreviewFullscreen) IsEditorFullscreen = false;
    }

    // ══════════════════════════ 导出 ══════════════════════════

    public async Task ExportAsync()
    {
        if (!_document.HasFile) return;

        var picker = new FileSavePicker();
        var hwnd = WinRT.Interop.WindowNative.GetWindowHandle(App.MainWindow);
        WinRT.Interop.InitializeWithWindow.Initialize(picker, hwnd);
        picker.FileTypeChoices.Add("PDF", new List<string> { ".pdf" });
        picker.FileTypeChoices.Add("Word", new List<string> { ".docx" });
        picker.FileTypeChoices.Add("HTML", new List<string> { ".html" });
        picker.SuggestedFileName = Path.GetFileNameWithoutExtension(_document.FileName);

        var file = await picker.PickSaveFileAsync();
        if (file is null) return;

        var ext = Path.GetExtension(file.Path).ToLowerInvariant();
        try
        {
            switch (ext)
            {
                case ".pdf":
                    _exportService.ExportPdf(file.Path, _document.Content);
                    break;
                case ".docx":
                    _exportService.ExportWord(file.Path, _document.Content);
                    break;
                case ".html":
                    _exportService.ExportHtml(file.Path, _document.Content);
                    break;
            }
            StatusText = $"导出成功: {file.Name}";
        }
        catch (Exception ex)
        {
            StatusText = $"导出失败: {ex.Message}";
        }
    }

    // ══════════════════════════ AI Agent ══════════════════════════

    [RelayCommand]
    private void ToggleAiPanel()
    {
        IsAiPanelOpen = !IsAiPanelOpen;
    }

    [RelayCommand]
    private async Task SendAiMessageAsync()
    {
        if (string.IsNullOrWhiteSpace(AiInput) || IsAiBusy) return;

        var userMsg = AiInput.Trim();
        AiInput = string.Empty;
        IsAiBusy = true;
        AiOutput = string.Empty;

        _aiMessages.Add(AiMessage.User(userMsg));
        AiHistory.Add($"🧑 {userMsg}");

        try
        {
            _aiCts = new CancellationTokenSource();
            var sb = new StringBuilder();

            await foreach (var token in _aiService.ChatStreamAsync(_aiMessages, _aiCts.Token))
            {
                sb.Append(token);
                AiOutput = sb.ToString();
            }

            _aiMessages.Add(AiMessage.Assistant(AiOutput));
            AiHistory.Add($"🤖 {AiOutput}");
            AiOutput = string.Empty; // 完成后清空实时输出区
        }
        catch (OperationCanceledException)
        {
            AiOutput = "[已取消]";
        }
        catch (Exception ex)
        {
            AiOutput = $"错误: {ex.Message}";
        }
        finally
        {
            IsAiBusy = false;
            _aiCts = null;
        }
    }

    [RelayCommand]
    private void CancelAi()
    {
        _aiCts?.Cancel();
    }

    [RelayCommand]
    private void InsertAiOutput()
    {
        // 将 AI 最后的回复插入到编辑器光标位置
        // View 层监听此属性变化后执行插入
        var lastAssistant = _aiMessages
            .Where(m => m.Role == "assistant")
            .Select(m => m.Content)
            .LastOrDefault();

        if (!string.IsNullOrEmpty(lastAssistant))
        {
            AiInsertContent = lastAssistant;
        }
    }

    [ObservableProperty] private string _aiInsertContent = string.Empty;

    [RelayCommand]
    private void ClearAiHistory()
    {
        AiHistory.Clear();
        InitAiMessages();
    }

    private void InitAiMessages()
    {
        _aiMessages.Clear();
        _aiMessages.Add(AiMessage.System(_settings.AiSystemPrompt));
    }

    // ══════════════════════════ 自动保存 ══════════════════════════

    public void StartAutoSave()
    {
        StopAutoSave();
        if (!_settings.AutoSave) return;

        _autoSaveTimer = new DispatcherTimer
        {
            Interval = TimeSpan.FromSeconds(_settings.AutoSaveIntervalSeconds)
        };
        _autoSaveTimer.Tick += (_, _) => AutoSave();
        _autoSaveTimer.Start();
    }

    public void StopAutoSave()
    {
        _autoSaveTimer?.Stop();
        _autoSaveTimer = null;
    }

    private void AutoSave()
    {
        if (_document.HasFile && _document.IsModified && _document.FilePath is not null)
        {
            try
            {
                _document.Save();
                StatusText = "自动保存完成";
            }
            catch { /* 静默 */ }
        }
    }

    // ══════════════════════════ 辅助 ══════════════════════════

    private void UpdateTitle()
    {
        var modified = _document.IsModified ? " •" : "";
        Title = $"{_document.FileName}{modified} - FluentMarkDown";
    }

    public void SaveSettings()
    {
        _settings.Save();
    }
}

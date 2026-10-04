using Microsoft.Extensions.DependencyInjection;
using Microsoft.UI.Xaml;
using FluentMarkDown.Models;
using FluentMarkDown.Services;
using FluentMarkDown.ViewModels;

namespace FluentMarkDown;

public partial class App : Application
{
    public static Window MainWindow { get; private set; } = null!;
    private readonly ServiceProvider _serviceProvider;

    public App()
    {
        InitializeComponent();

        // ── 依赖注入配置 ──
        var services = new ServiceCollection();

        // 模型（单例）
        services.AddSingleton<AppSettings>(_ => AppSettings.Load());
        services.AddSingleton<DocumentModel>();
        services.AddSingleton<RecentFilesManager>();

        // 服务
        services.AddSingleton<MarkdownService>();
        services.AddSingleton<PreviewService>();
        services.AddSingleton<ExportService>();
        services.AddHttpClient<AiAgentService>((sp, client) =>
        {
            var settings = sp.GetRequiredService<AppSettings>();
            client.BaseAddress = new Uri(settings.AiApiEndpoint);
            client.Timeout = TimeSpan.FromMinutes(5);
        });

        // ViewModel
        services.AddSingleton<MainViewModel>();

        _serviceProvider = services.BuildServiceProvider();
    }

    protected override void OnLaunched(LaunchActivatedEventArgs args)
    {
        var viewModel = _serviceProvider.GetRequiredService<MainViewModel>();
        var window = new MainWindow(viewModel);
        MainWindow = window;
        window.Activate();

        // 应用主题
        if (window.Content is FrameworkElement root)
        {
            root.RequestedTheme = ElementTheme.Default; // 跟随系统
        }
    }
}

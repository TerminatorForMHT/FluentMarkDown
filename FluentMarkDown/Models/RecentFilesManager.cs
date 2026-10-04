using System.Text.Json;

namespace FluentMarkDown.Models;

/// <summary>
/// 最近打开文件的历史记录管理
/// </summary>
public class RecentFilesManager
{
    private const int MaxRecent = 15;
    private static readonly string HistoryPath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
        "FluentMarkDown", "recent_files.json");

    private List<string> _files = new();

    public RecentFilesManager()
    {
        Load();
    }

    public IReadOnlyList<string> Files => _files.AsReadOnly();

    public void Add(string filePath)
    {
        var normalized = Path.GetFullPath(filePath);
        _files.RemoveAll(f => string.Equals(Path.GetFullPath(f), normalized, StringComparison.OrdinalIgnoreCase));
        _files.Insert(0, normalized);
        if (_files.Count > MaxRecent)
            _files = _files.Take(MaxRecent).ToList();
        Save();
    }

    public void Remove(string filePath)
    {
        var normalized = Path.GetFullPath(filePath);
        _files.RemoveAll(f => string.Equals(Path.GetFullPath(f), normalized, StringComparison.OrdinalIgnoreCase));
        Save();
    }

    public void Clear()
    {
        _files.Clear();
        Save();
    }

    private void Load()
    {
        try
        {
            if (File.Exists(HistoryPath))
            {
                var json = File.ReadAllText(HistoryPath);
                _files = JsonSerializer.Deserialize<List<string>>(json) ?? new();
            }
        }
        catch { _files = new(); }
    }

    private void Save()
    {
        try
        {
            var dir = Path.GetDirectoryName(HistoryPath)!;
            Directory.CreateDirectory(dir);
            File.WriteAllText(HistoryPath, JsonSerializer.Serialize(_files, new JsonSerializerOptions { WriteIndented = true }));
        }
        catch { /* 静默 */ }
    }
}

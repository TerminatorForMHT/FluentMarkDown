namespace FluentMarkDown.Models;

/// <summary>
/// 文档模型 —— 管理 Markdown 文件的状态与内容
/// </summary>
public class DocumentModel
{
    public string? FilePath { get; set; }
    public string Content { get; set; } = string.Empty;
    public bool IsModified { get; set; }
    public bool HasFile { get; set; }

    /// <summary>文件名（含扩展名），无文件时返回 "untitled.md"</summary>
    public string FileName =>
        FilePath is not null ? Path.GetFileName(FilePath) : "untitled.md";

    /// <summary>文件所在目录，无文件时返回当前工作目录</summary>
    public string BaseDirectory =>
        FilePath is not null ? Path.GetDirectoryName(FilePath)! : Directory.GetCurrentDirectory();

    public void New()
    {
        FilePath = null;
        Content = string.Empty;
        IsModified = false;
        HasFile = true;
    }

    public bool Load(string path)
    {
        if (string.IsNullOrWhiteSpace(path)) return false;
        try
        {
            Content = File.ReadAllText(path);
            FilePath = path;
            HasFile = true;
            IsModified = false;
            return true;
        }
        catch
        {
            return false;
        }
    }

    public bool Save(string? path = null)
    {
        var savePath = path ?? FilePath;
        if (string.IsNullOrWhiteSpace(savePath)) return false;
        try
        {
            File.WriteAllText(savePath, Content);
            FilePath = savePath;
            IsModified = false;
            HasFile = true;
            return true;
        }
        catch
        {
            return false;
        }
    }
}

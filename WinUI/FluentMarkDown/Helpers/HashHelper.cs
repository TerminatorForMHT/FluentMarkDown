using System.Security.Cryptography;
using System.Text;

namespace FluentMarkDown.Helpers;

/// <summary>
/// 文本内容的 MD5 哈希计算，用于去重渲染
/// </summary>
public static class HashHelper
{
    public static string Md5(string input)
    {
        var bytes = MD5.HashData(Encoding.UTF8.GetBytes(input));
        return Convert.ToHexString(bytes).ToLowerInvariant();
    }
}

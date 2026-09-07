Add-Type @"
using System; using System.Text; using System.Runtime.InteropServices; using System.Collections.Generic;
public class W {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc f, IntPtr l);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  public static List<string> Consoles() {
    var out_ = new List<string>();
    EnumWindows((h, l) => {
      if (!IsWindowVisible(h)) return true;
      var c = new StringBuilder(256); GetClassName(h, c, 256);
      var cls = c.ToString();
      if (cls == "ConsoleWindowClass" || cls == "CASCADIA_HOSTING_WINDOW_CLASS") {
        var t = new StringBuilder(512); GetWindowText(h, t, 512); uint pid; GetWindowThreadProcessId(h, out pid);
        out_.Add(cls + " | pid=" + pid + " | " + t.ToString());
      }
      return true; }, IntPtr.Zero);
    return out_; }
}
"@
"visible console-class windows:"
[W]::Consoles() | ForEach-Object { "  $_" }
"windows terminal / openconsole processes:"
Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('WindowsTerminal.exe','OpenConsole.exe') } | ForEach-Object { "  $($_.Name) pid=$($_.ProcessId) parent=$($_.ParentProcessId)" }

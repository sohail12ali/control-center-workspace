Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
Add-Type @"
using System; using System.Text; using System.Runtime.InteropServices;
public class T {
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x,int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f,uint dx,uint dy,uint d,IntPtr e);
  [DllImport("user32.dll")] public static extern IntPtr FindWindow(string c,string w);
  [DllImport("user32.dll")] public static extern IntPtr SendMessage(IntPtr h,uint m,IntPtr w,IntPtr l);
  [DllImport("user32.dll")] public static extern int GetMenuItemCount(IntPtr m);
  [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int GetMenuStringW(IntPtr m,uint i,StringBuilder s,int n,uint f);
  [DllImport("user32.dll")] public static extern uint GetMenuState(IntPtr m,uint i,uint f);
  [DllImport("user32.dll")] public static extern bool GetMenuItemRect(IntPtr h,IntPtr m,uint i,out RECT r);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h,out RECT r);
  public struct RECT { public int L,T,R,B; }
  public const uint MN_GETHMENU=0x01E1, MF_BYPOSITION=0x400, RD=0x0008, RU=0x0010, LD=0x0002, LU=0x0004;
  public static void Click(int x,int y,bool right){ SetCursorPos(x,y); System.Threading.Thread.Sleep(280);
    mouse_event(right?RD:LD,0,0,0,IntPtr.Zero); System.Threading.Thread.Sleep(70); mouse_event(right?RU:LU,0,0,0,IntPtr.Zero); }
}
"@
[void][T]::SetProcessDPIAware()

function Open-TrayMenu {
  $root = [System.Windows.Automation.AutomationElement]::RootElement
  $chev = $root.FindFirst([System.Windows.Automation.TreeScope]::Descendants,
    (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty,"Show Hidden Icons")))
  if ($chev) { $chev.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke(); Start-Sleep -Milliseconds 1300 }
  $icon = $root.FindFirst([System.Windows.Automation.TreeScope]::Descendants,
    (New-Object System.Windows.Automation.AndCondition(
      (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty,"Delivery Console")),
      (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ClassNameProperty,"SystemTray.NormalButton")))))
  if (-not $icon) { throw "tray icon not found" }
  $r = $icon.Current.BoundingRectangle
  [T]::Click([int]($r.X+$r.Width/2), [int]($r.Y+$r.Height/2), $true)
  Start-Sleep -Milliseconds 1400
  $h = [T]::FindWindow("#32768",$null)
  if ($h -eq [IntPtr]::Zero) { throw "menu did not open" }
  return $h
}

function Read-TrayMenu($h) {
  $hm = [T]::SendMessage($h,[T]::MN_GETHMENU,[IntPtr]::Zero,[IntPtr]::Zero)
  $n = [T]::GetMenuItemCount($hm)
  $items = @()
  for ($i=0; $i -lt $n; $i++) {
    $sb = New-Object System.Text.StringBuilder 512
    [void][T]::GetMenuStringW($hm,[uint32]$i,$sb,512,[T]::MF_BYPOSITION)
    $st = [T]::GetMenuState($hm,[uint32]$i,[T]::MF_BYPOSITION)
    $rc = New-Object T+RECT; $ok = [T]::GetMenuItemRect($h,$hm,[uint32]$i,[ref]$rc)
    $items += [pscustomobject]@{ Index=$i; Text=$sb.ToString(); State=$st
      Checked=[bool]($st -band 0x0008); Disabled=[bool]($st -band 0x0003); Separator=[bool]($st -band 0x0800)
      CX=[int](($rc.L+$rc.R)/2); CY=[int](($rc.T+$rc.B)/2); HasRect=$ok }
  }
  return $items
}

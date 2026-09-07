param([int]$HostPid = 0)
function Tree($p){ $out=@($p); Get-CimInstance Win32_Process -Filter "ParentProcessId=$p" | ForEach-Object { $out += Tree $_.ProcessId }; $out }
$h = Get-Process delivery-console-desktop -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $h) { "HOST NOT RUNNING" } else {
  "host pid=$($h.Id) title=[$($h.MainWindowTitle)]"
  $tree = Tree $h.Id
  "host tree pids: $($tree -join ',')"
  $con = Get-CimInstance Win32_Process -Filter "Name='conhost.exe'" | Where-Object { $tree -contains $_.ParentProcessId }
  foreach ($c in $con) { "  conhost pid=$($c.ProcessId) parent=$($c.ParentProcessId)" }
  "conhost in host tree: $(@($con).Count)"
}
$serve = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*kanban.py serve*' }
foreach ($s in $serve) {
  "serve pid=$($s.ProcessId) parent=$($s.ParentProcessId)"
  $st = Tree $s.ProcessId
  "  serve tree pids: $($st -join ',')"
  Get-CimInstance Win32_Process | Where-Object { $st -contains $_.ProcessId -and $_.ProcessId -ne $s.ProcessId } | ForEach-Object { "    child $($_.Name) pid=$($_.ProcessId) parent=$($_.ParentProcessId)" }
  $sc = Get-CimInstance Win32_Process -Filter "Name='conhost.exe'" | Where-Object { $st -contains $_.ParentProcessId }
  "  conhost in serve tree: $(@($sc).Count)"
}
"serve count: $(@($serve).Count)"
try { $r = Invoke-RestMethod http://127.0.0.1:8790/api/config -TimeoutSec 5; "api/config ok title=$($r.title)" } catch { "api/config FAILED: $($_.Exception.Message)" }

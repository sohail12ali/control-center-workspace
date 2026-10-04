# Tray menu smoke helpers (T-002)

`tray-menu-lib.ps1` is the reusable half: dot-source it and call

- `Open-TrayMenu` — opens **Show Hidden Icons**, right-clicks the
  `Delivery Console` notify icon, returns the `#32768` menu hwnd.
- `Read-TrayMenu $hwnd` — returns one object per row with `Text`, `Checked`,
  `Disabled`, `Separator` and a DPI-correct `CX`/`CY` centre to click.

Why this exists: the tray menu is **invisible to UI Automation** (both the
T-002 pass and the T-003 verifier pass searched the UIA tree and found no
drivable element). It *is* a standard Win32 popup menu, so
`SendMessage(hwnd, MN_GETHMENU)` + `GetMenuStringW` / `GetMenuState` /
`GetMenuItemRect` read it exactly, and a synthetic click at the item's centre
activates it. Call `SetProcessDPIAware()` first or the rects come back halved
on a scaled display.

Later tickets that touch the tray (icon states, listen toggle) should reuse
this instead of re-deriving it.

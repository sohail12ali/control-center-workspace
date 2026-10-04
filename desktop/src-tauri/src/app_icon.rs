//! The taskbar and Alt-Tab icon, at the exact size Windows asks for.
//!
//! ## Why this exists
//!
//! Tauri gives every window `default_window_icon`, and on Windows that is
//! built by `tauri-codegen` from `icons/icon.ico` — as `icon_dir.entries()[0]`,
//! the FIRST frame in the file, not the best fit for the display. One RGBA
//! bitmap then has to serve every size Windows wants: ~48px in the taskbar at
//! 200% scaling, 32px in Alt-Tab, 16px in the window corner. Whatever that one
//! frame is, most of those are a resize, and an UPSCALE is visibly soft.
//!
//! `gen_app_icons.py` now writes the .ico largest-first so that single frame is
//! at least 256px and every use is a downscale. This goes the rest of the way:
//! the .ico is already embedded in the exe as icon resource 32512 (see
//! `build.rs`), with a frame at every size Windows asks for, so we ask Windows
//! to load THAT resource at the metric sizes and hand the results to the
//! window. No scaling, because no scaling is needed — the right pixels already
//! exist in the binary.
//!
//! Windows only. Everywhere else Tauri's own icon is correct: X11 and macOS
//! take a large image and downscale it themselves.

#[cfg(target_os = "windows")]
pub fn apply(window: &tauri::WebviewWindow) {
    use windows_sys::Win32::System::LibraryLoader::GetModuleHandleW;
    use windows_sys::Win32::UI::WindowsAndMessaging::{
        GetSystemMetrics, LoadImageW, SendMessageW, ICON_BIG, ICON_SMALL, IMAGE_ICON,
        LR_DEFAULTCOLOR, SM_CXICON, SM_CXSMICON, SM_CYICON, SM_CYSMICON, WM_SETICON,
    };

    // The id `build.rs`'s generated resource.rc gives the .ico. It is also the
    // IDI_APPLICATION constant, which is why passing a real module handle
    // matters: with a null one, Windows would load its own default icon and
    // this would silently "work" while showing the wrong picture.
    const ICON_RESOURCE_ID: u32 = 32512;

    let hwnd = match window.hwnd() {
        Ok(h) => h.0 as isize,
        Err(e) => {
            log::warn!("app-icon: no HWND yet ({e}); leaving Tauri's icon in place");
            return;
        }
    };

    // SAFETY: every call below is a plain Win32 call with owned arguments.
    // The icons are LR_SHARED-free copies owned by the window from the moment
    // WM_SETICON succeeds, and are released when the window is destroyed.
    unsafe {
        let instance = GetModuleHandleW(std::ptr::null());
        if instance.is_null() {
            log::warn!("app-icon: GetModuleHandleW failed; keeping Tauri's icon");
            return;
        }
        // GetSystemMetrics is DPI-scaled for this process (tao asks for
        // per-monitor v2), so on a 200% display these are 64 and 32 — real
        // frames in the .ico, not sizes something has to invent.
        for (which, cx, cy) in [
            (ICON_BIG, GetSystemMetrics(SM_CXICON), GetSystemMetrics(SM_CYICON)),
            (ICON_SMALL, GetSystemMetrics(SM_CXSMICON), GetSystemMetrics(SM_CYSMICON)),
        ] {
            let icon = LoadImageW(
                instance,
                ICON_RESOURCE_ID as *const u16,
                IMAGE_ICON,
                cx,
                cy,
                LR_DEFAULTCOLOR,
            );
            if icon.is_null() {
                log::warn!("app-icon: LoadImageW({cx}x{cy}) failed; keeping Tauri's icon");
                continue;
            }
            SendMessageW(hwnd as _, WM_SETICON, which as usize, icon as isize);
            log::info!("app-icon: set {cx}x{cy} from the exe's icon resource");
        }
    }
}

#[cfg(not(target_os = "windows"))]
pub fn apply(_window: &tauri::WebviewWindow) {}

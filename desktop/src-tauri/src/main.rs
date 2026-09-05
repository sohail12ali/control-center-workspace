#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod sidecar;
mod tray;

#[cfg(windows)]
mod job;

use std::sync::Mutex;

use sidecar::Handle;
use tauri::{Manager, WebviewUrl, WebviewWindowBuilder};

pub struct ShellState {
    owned: bool,
    pid: Option<u32>,
    repo_root: std::path::PathBuf,
    quitting: bool,
}

fn init_script() -> &'static str {
    #[cfg(target_os = "macos")]
    {
        r#"try{document.documentElement.classList.add("in-shell","os-mac")}catch(e){}"#
    }
    #[cfg(not(target_os = "macos"))]
    {
        r#"try{document.documentElement.classList.add("in-shell")}catch(e){}"#
    }
}

fn alert(msg: &str) {
    #[cfg(windows)]
    {
        use std::os::windows::ffi::OsStrExt;
        use windows_sys::Win32::UI::WindowsAndMessaging::{MessageBoxW, MB_ICONERROR, MB_OK};
        let text: Vec<u16> = std::ffi::OsStr::new(msg)
            .encode_wide()
            .chain(std::iter::once(0))
            .collect();
        let title: Vec<u16> = std::ffi::OsStr::new("Delivery Console")
            .encode_wide()
            .chain(std::iter::once(0))
            .collect();
        unsafe {
            MessageBoxW(
                std::ptr::null_mut(),
                text.as_ptr(),
                title.as_ptr(),
                MB_OK | MB_ICONERROR,
            );
        }
    }
    #[cfg(not(windows))]
    eprintln!("{msg}");
}

fn stop_owned(state: &ShellState) {
    if state.owned {
        if let Some(pid) = state.pid {
            sidecar::stop(&state.repo_root, pid);
        }
    }
}

fn open_window(app: &tauri::App, handle: &Handle) -> Result<(), Box<dyn std::error::Error>> {
    let url = handle.url.parse::<url::Url>().map_err(|e| e.to_string())?;
    let mut builder = WebviewWindowBuilder::new(app, "main", WebviewUrl::External(url))
        .title("Delivery Console")
        .inner_size(1280.0, 800.0)
        .min_inner_size(800.0, 500.0)
        .resizable(true)
        .initialization_script(init_script());

    #[cfg(target_os = "macos")]
    {
        builder = builder
            .hidden_title(true)
            .title_bar_style(tauri::TitleBarStyle::Overlay);
    }
    #[cfg(not(target_os = "macos"))]
    {
        builder = builder.decorations(false).shadow(true);
    }

    builder.build()?;
    Ok(())
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let root = match sidecar::find_repo_root() {
                Ok(r) => r,
                Err(e) => {
                    alert(&e.0);
                    return Err(e.0.into());
                }
            };
            let handle = match sidecar::ensure(&root) {
                Ok(h) => h,
                Err(e) => {
                    alert(&e.0);
                    return Err(e.0.into());
                }
            };

            #[cfg(windows)]
            if handle.owned {
                if let Some(pid) = handle.pid {
                    if let Some(j) = job::Job::new() {
                        let _ = j.add(pid);
                        std::mem::forget(j);
                    }
                }
            }

            app.manage(Mutex::new(ShellState {
                owned: handle.owned,
                pid: handle.pid,
                repo_root: root,
                quitting: false,
            }));

            open_window(app, &handle).map_err(|e| {
                alert(&e.to_string());
                e
            })?;
            tray::attach(app).map_err(|e| {
                alert(&e.to_string());
                e
            })?;
            Ok(())
        })
        .on_window_event(|window, event| match event {
            tauri::WindowEvent::CloseRequested { api, .. } => {
                let quitting = window
                    .try_state::<Mutex<ShellState>>()
                    .and_then(|s| s.inner().lock().ok().map(|g| g.quitting))
                    .unwrap_or(false);
                if !quitting {
                    api.prevent_close();
                    let _ = window.hide();
                }
            }
            tauri::WindowEvent::Destroyed => {
                if let Some(state) = window.try_state::<Mutex<ShellState>>() {
                    if let Ok(s) = state.inner().lock() {
                        stop_owned(&s);
                    }
                }
            }
            _ => {}
        })
        .run(tauri::generate_context!())
        .expect("Delivery Console failed to start");
}

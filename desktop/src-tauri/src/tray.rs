//! System tray skeleton. Ids must match `desktop/features.toml` skeleton rows:
//! session_backend, show_window, new_chat, mute_replies, interrupt, quit.

use serde::Deserialize;
use tauri::menu::{CheckMenuItem, MenuBuilder, MenuItem, PredefinedMenuItem};
use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
use tauri::{AppHandle, Listener, Manager};

use crate::ShellState;
use std::sync::Mutex;

#[derive(Clone)]
pub struct TrayUi {
    pub header: MenuItem<tauri::Wry>,
    pub mute: CheckMenuItem<tauri::Wry>,
}

#[derive(Deserialize)]
struct SessionPayload {
    #[serde(default)]
    backend: String,
    #[serde(default = "default_muted")]
    muted: bool,
}

fn default_muted() -> bool {
    true
}

/// Every `let _ = ...` in this module used to swallow a `tauri::Result`
/// silently; this is the one place that turns a swallowed error into an
/// auditable line, so every call site is one line instead of an inline
/// `if let Err` that a future addition could easily forget.
fn warn_on_err<T, E: std::fmt::Display>(context: &str, result: Result<T, E>) {
    if let Err(e) = result {
        log::warn!("tray: {context} failed: {e}");
    }
}

pub fn show_main(app: &AppHandle) {
    if let Some(w) = app.get_webview_window("main") {
        warn_on_err("show_main show()", w.show());
        warn_on_err("show_main unminimize()", w.unminimize());
        warn_on_err("show_main set_focus()", w.set_focus());
    }
}

fn eval_tray(app: &AppHandle, id: &str) {
    let payload = serde_json::to_string(id).unwrap_or_else(|_| "\"\"".into());
    let js = format!(
        "try{{window.ConsoleAgents&&window.ConsoleAgents.trayAction({payload})}}catch(e){{}}"
    );
    if let Some(w) = app.get_webview_window("main") {
        warn_on_err(&format!("eval_tray({id})"), w.eval(&js));
    }
}

pub fn request_quit(app: &AppHandle) {
    if let Some(state) = app.try_state::<Mutex<ShellState>>() {
        if let Ok(mut s) = state.inner().lock() {
            s.quitting = true;
        }
    }
    if let Some(w) = app.get_webview_window("main") {
        warn_on_err("request_quit close()", w.close());
    }
}

pub fn attach(app: &tauri::App) -> Result<(), Box<dyn std::error::Error>> {
    let handle = app.handle();
    // Disabled header — not a backend picker (features.toml session_backend).
    let header = MenuItem::with_id(handle, "session_backend", "—", false, None::<&str>)?;
    let show = MenuItem::with_id(handle, "show_window", "Show window", true, None::<&str>)?;
    let new_chat = MenuItem::with_id(handle, "new_chat", "New chat", true, None::<&str>)?;
    // autoRead defaults false → muted checked.
    let mute = CheckMenuItem::with_id(
        handle,
        "mute_replies",
        "Mute replies",
        true,
        true,
        None::<&str>,
    )?;
    let interrupt = MenuItem::with_id(
        handle,
        "interrupt",
        "Interrupt current turn",
        true,
        None::<&str>,
    )?;
    let quit = MenuItem::with_id(handle, "quit", "Quit", true, None::<&str>)?;

    let menu = MenuBuilder::new(handle)
        .item(&header)
        .separator()
        .item(&show)
        .item(&new_chat)
        .item(&mute)
        .item(&interrupt)
        .item(&PredefinedMenuItem::separator(handle)?)
        .item(&quit)
        .build()?;

    let ui = TrayUi {
        header: header.clone(),
        mute: mute.clone(),
    };
    app.manage(ui.clone());

    let mut tray = TrayIconBuilder::with_id("main")
        .menu(&menu)
        .tooltip("Delivery Console")
        .show_menu_on_left_click(false)
        .on_menu_event(|app, event| {
            let id = event.id().as_ref();
            match id {
                "show_window" => show_main(app),
                "new_chat" => {
                    show_main(app);
                    eval_tray(app, "new_chat");
                }
                "mute_replies" => {
                    let muted = ui_mute(app).and_then(|m| m.is_checked().ok()).unwrap_or(true);
                    eval_tray(
                        app,
                        if muted {
                            "mute_on"
                        } else {
                            "mute_off"
                        },
                    );
                }
                "interrupt" => {
                    show_main(app);
                    eval_tray(app, "interrupt");
                }
                "quit" => request_quit(app),
                _ => {}
            }
        })
        .on_tray_icon_event(|tray, event| {
            if let TrayIconEvent::Click {
                button: MouseButton::Left,
                button_state: MouseButtonState::Up,
                ..
            } = event
            {
                show_main(tray.app_handle());
            }
        });

    if let Some(icon) = handle.default_window_icon() {
        tray = tray.icon(icon.clone());
    }

    tray.build(handle)?;

    let header_cb = ui.header.clone();
    let mute_cb = ui.mute.clone();
    let _ = handle.listen("desktop-session", move |event| {
        let Ok(payload) = serde_json::from_str::<SessionPayload>(event.payload()) else {
            return;
        };
        let label = {
            let t = payload.backend.trim();
            if t.is_empty() {
                "—".to_string()
            } else {
                t.to_string()
            }
        };
        warn_on_err("header set_text", header_cb.set_text(label));
        warn_on_err("mute set_checked", mute_cb.set_checked(payload.muted));
    });

    Ok(())
}

fn ui_mute(app: &AppHandle) -> Option<CheckMenuItem<tauri::Wry>> {
    app.try_state::<TrayUi>().map(|s| s.inner().mute.clone())
}

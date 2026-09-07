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
    pub hands_free: CheckMenuItem<tauri::Wry>,
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

/// Fold the mute state into the tray's own state machine.
///
/// The webview owns the `autoRead` preference and is told separately; this is
/// what lets the ICON reflect it. Silently does nothing when the state has not
/// been managed yet, which is only true before setup finishes.
fn note_mute(app: &tauri::AppHandle, muted: bool) {
    use std::sync::{Arc, Mutex};
    let Some(state) = app.try_state::<Arc<Mutex<crate::tray_state::Assistant>>>() else {
        return;
    };
    if let Ok(mut assistant) = state.inner().lock() {
        assistant.apply(crate::tray_state::Event::Mute(muted));
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
    // The same action as a left-click on the icon. Present on every platform
    // because it is useful everywhere, and REQUIRED on Linux: libappindicator
    // does not deliver a left-click to the app — any click opens this menu —
    // so without this row the click-to-talk gesture would simply not exist
    // there. Per-platform substitute by design, not a Linux afterthought.
    let talk = MenuItem::with_id(handle, "listen_short_take", "Talk", true, None::<&str>)?;
    // autoRead defaults false → muted checked.
    let mute = CheckMenuItem::with_id(
        handle,
        "mute_replies",
        "Mute replies",
        true,
        true,
        None::<&str>,
    )?;
    // Hands-free is a checkbox, not a command: it is a state you are in, and
    // the tick is how you can tell the microphone is open without waiting for
    // the icon to change.
    let hands_free_item = CheckMenuItem::with_id(
        handle,
        "listen_hands_free",
        "Hands-free listening",
        true,
        false,
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
        .item(&talk)
        .item(&new_chat)
        .item(&mute)
        .item(&hands_free_item)
        .item(&interrupt)
        .item(&PredefinedMenuItem::separator(handle)?)
        .item(&quit)
        .build()?;

    let ui = TrayUi {
        header: header.clone(),
        mute: mute.clone(),
        hands_free: hands_free_item.clone(),
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
                "listen_short_take" => crate::click::act(app),
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
                    // Tell the shell's own state too, not just the webview.
                    // Without this the muted glyph could never appear — the
                    // compiler noticed before anyone did, by reporting
                    // `Event::Mute` as never constructed outside tests.
                    note_mute(app, muted);
                }
                "listen_hands_free" => {
                    // The tick follows the outcome, not the click: starting
                    // can fail, and a ticked box over a closed microphone is
                    // the one state this must never show.
                    let on = crate::toggle_hands_free(app);
                    if let Some(item) = app.try_state::<TrayUi>() {
                        warn_on_err("hands_free set_checked", item.hands_free.set_checked(on));
                    }
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
                // What this does depends on what the assistant is doing —
                // see `click.rs`. It used to be `show_main` unconditionally.
                crate::click::act(tray.app_handle());
            }
        });

    if let Some(icon) = handle.default_window_icon() {
        tray = tray.icon(icon.clone());
    }

    tray.build(handle)?;

    // Hands-free can end without anyone clicking the row — the session time
    // cap expires, or the microphone goes away. This keeps the tick honest in
    // those cases; without it the menu would claim an open microphone that had
    // already closed itself.
    {
        let app_for_sync = handle.clone();
        let watched = ui.hands_free.clone();
        let mut shown = false;
        let _ = std::thread::Builder::new()
            .name("hands-free-tick".into())
            .spawn(move || loop {
                std::thread::sleep(std::time::Duration::from_secs(2));
                let on = crate::hands_free::running();
                if on != shown {
                    shown = on;
                    let item = watched.clone();
                    warn_on_err(
                        "hands_free tick sync",
                        app_for_sync.run_on_main_thread(move || {
                            let _ = item.set_checked(on);
                        }),
                    );
                }
            });
    }

    let header_cb = ui.header.clone();
    let mute_cb = ui.mute.clone();
    // Cloned for the listener, which outlives this function.
    let app_for_events = handle.clone();
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
        note_mute(&app_for_events, payload.muted);
    });

    Ok(())
}

fn ui_mute(app: &AppHandle) -> Option<CheckMenuItem<tauri::Wry>> {
    app.try_state::<TrayUi>().map(|s| s.inner().mute.clone())
}

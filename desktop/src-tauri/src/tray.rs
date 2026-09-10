//! The system tray, GENERATED from `desktop/features.toml`.
//!
//! ## Why generated
//!
//! The registry has always called itself the source of truth — the honesty
//! registry the tray and Settings project from — and a Python test held it to
//! describing what the code really does. But the menu was written out by hand
//! here: eight items, against sixteen features the file marked available. So
//! clipboard copy, clipboard send, both captures and the whole listening
//! submenu were implemented, declared, and unreachable, because building a
//! row was a second place you had to remember to type.
//!
//! Now `features.rs` parses the file and this module walks it. What is left by
//! hand is the one part that genuinely is code — what an id DOES — and
//! `warn_about_drift` says so at startup if an available row has no arm.
//!
//! ## What the tray is still not allowed to do
//!
//! Approve anything. Three rows carry `never_one_click` in the registry
//! (`clipboard_send`, `capture_this_turn`, `capture_region`) and this module
//! honours it by opening the window instead: a click cannot tell you what is
//! about to be sent, and the clipboard can hold a password.

use serde::Deserialize;
use tauri::menu::{CheckMenuItem, MenuBuilder, MenuItem, PredefinedMenuItem,
                  SubmenuBuilder};
use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
use tauri::{AppHandle, Listener, Manager};

use crate::ShellState;
use std::sync::Mutex;

/// The few menu items the shell has to reach BACK into after building them.
///
/// All optional, because every row is now the registry's to include or leave
/// out (`desktop/features.toml`). A missing one means the file says not to
/// have it, which is a configuration, not a fault — so each user checks and
/// moves on rather than unwrapping.
#[derive(Clone)]
pub struct TrayUi {
    /// Which backend this chat is on. A label, not a picker.
    pub header: Option<MenuItem<tauri::Wry>>,
    pub mute: Option<CheckMenuItem<tauri::Wry>>,
    pub hands_free: Option<CheckMenuItem<tauri::Wry>>,
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

/// Persist the mute choice as the Assistant's `speak` setting.
///
/// On a worker thread: this is an HTTP round trip, and it is happening inside
/// a menu-event handler on the UI thread.
fn store_mute(app: &AppHandle, muted: bool) {
    let url = app
        .try_state::<Mutex<ShellState>>()
        .and_then(|s| s.inner().lock().ok().map(|g| g.console_url.clone()))
        .unwrap_or_default();
    if url.is_empty() {
        return;
    }
    let _ = std::thread::Builder::new()
        .name("mute-store".into())
        .spawn(move || crate::console_settings::set_bool(&url, "speak", !muted));
}

/// Say something to the Assistant from a menu click.
///
/// On a worker thread, because this is an HTTP round trip happening inside a
/// menu-event handler on the UI thread — the same reason `store_mute` above
/// spawns one. A tray that freezes for the length of a request is the exact
/// complaint T-015 exists to answer.
fn say_from_tray(app: &AppHandle, text: &'static str) {
    let url = console_url_of(app);
    if url.is_empty() {
        crate::tray_paint::said("the console is not running");
        return;
    }
    crate::console_api::say_detached(&url, text, "tray");
}

/// Where the console is, or "" when the shell has not recorded one yet.
fn console_url_of(app: &AppHandle) -> String {
    app.try_state::<Mutex<ShellState>>()
        .and_then(|s| s.inner().lock().ok().map(|g| g.console_url.clone()))
        .unwrap_or_default()
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
    // Close the overlay first. It is a second window, and that turned out to
    // matter: Tauri ends the process when the LAST window closes, so once the
    // HUD existed, closing `main` stopped the sidecar and left the shell
    // running with a dead console behind it — every feature broken, and no
    // way to quit. Reported as "Exit is not working", and it was.
    if let Some(hud) = app.get_webview_window(crate::hud::LABEL) {
        warn_on_err("request_quit hud close()", hud.close());
    }
    if let Some(w) = app.get_webview_window("main") {
        warn_on_err("request_quit close()", w.close());
    }
    // And say so outright rather than relying on window bookkeeping to imply
    // it. `exit` runs the exit hooks, so the sidecar still gets stopped.
    app.exit(0);
}

/// Ids this module knows how to carry out.
///
/// The menu's SHAPE comes from `desktop/features.toml`; what a row does is
/// code, and this is the list of it. Kept beside the dispatch it mirrors so
/// the two are read together, and checked against the registry at startup by
/// `warn_about_drift` — a row that is shown with no arm here is a menu item
/// that would silently do nothing, which is the failure the whole generated
/// menu exists to prevent.
const DISPATCHED: &[&str] = &[
    "show_window",
    "listen_off",
    "listen_short_take",
    "listen_hands_free",
    "new_chat",
    "interrupt",
    "clipboard_copy_last",
    "clipboard_send",
    "capture_this_turn",
    "capture_region",
    "mute_replies",
    "quit",
];

/// Say so when the registry and the code disagree.
///
/// Not an error: a shipped registry row whose work has not landed yet is a
/// normal state, and it is already rendered disabled with its reason. This
/// catches the other case — a row marked AVAILABLE with nothing behind it,
/// which would look like a working menu item and do nothing at all.
fn warn_about_drift() {
    for feature in crate::features::all() {
        if !feature.in_menu() || !feature.available {
            continue;
        }
        if matches!(
            feature.placement,
            crate::features::Placement::Header | crate::features::Placement::Submenu
        ) {
            continue; // a label and a container; neither is clicked
        }
        if !DISPATCHED.contains(&feature.id.as_str()) {
            log::warn!(
                "tray: features.toml offers {} as available, but nothing here \
                 carries it out — the row would do nothing",
                feature.id
            );
        }
    }
}

/// Build one row. `None` for a row the registry says to leave out entirely.
///
/// An unavailable row is rendered DISABLED and carries its reason in the
/// label, rather than being dropped: silence tells you nothing, while "Watch
/// — needs phase 6" tells you the feature is real and not ready. That is the
/// same honesty `voice.js` already applies to a missing capability, and it is
/// what `projection.unavailable = "disabled"` in the registry asks for.
fn build_row(
    app: &AppHandle,
    feature: &crate::features::Feature,
    hide_unavailable: bool,
    ticks: &mut Vec<(String, CheckMenuItem<tauri::Wry>)>,
) -> Option<MenuKind> {
    use crate::features::Placement;
    match feature.placement {
        Placement::Hide => None,
        Placement::Header => MenuItem::with_id(app, &feature.id, "—", false, None::<&str>)
            .ok()
            .map(MenuKind::Header),
        _ if !feature.available => {
            if hide_unavailable {
                return None;
            }
            let label = format!("{} — {}", feature.label, feature.reason_unavailable);
            MenuItem::with_id(app, &feature.id, label, false, None::<&str>)
                .ok()
                .map(MenuKind::Plain)
        }
        Placement::Submenu => {
            let mut builder = SubmenuBuilder::new(app, &feature.label);
            for child in crate::features::children_of(&feature.id) {
                match build_row(app, child, hide_unavailable, ticks) {
                    Some(MenuKind::Plain(item)) => builder = builder.item(&item),
                    Some(MenuKind::Check(item)) => builder = builder.item(&item),
                    _ => {}
                }
            }
            builder.build().ok().map(MenuKind::Sub)
        }
        Placement::Show if feature.check => {
            let item = CheckMenuItem::with_id(
                app,
                &feature.id,
                &feature.label,
                true,
                false,
                None::<&str>,
            )
            .ok()?;
            // Recorded on the way past, by id. A tick has to be CORRECTED
            // later — the initial mute state is read from the console, and a
            // hands-free session can end on its own when its time cap expires
            // — so the item that is actually in the menu must be reachable
            // afterwards. Rebuilding a second item with the same label would
            // give something whose `set_checked` moves nothing on screen,
            // which is worse than no tick at all.
            ticks.push((feature.id.clone(), item.clone()));
            Some(MenuKind::Check(item))
        }
        Placement::Show => {
            MenuItem::with_id(app, &feature.id, &feature.label, true, None::<&str>)
                .ok()
                .map(MenuKind::Plain)
        }
    }
}

/// The three shapes a built row can have, so `build_row` can return one thing.
enum MenuKind {
    Header(MenuItem<tauri::Wry>),
    Plain(MenuItem<tauri::Wry>),
    Check(CheckMenuItem<tauri::Wry>),
    Sub(tauri::menu::Submenu<tauri::Wry>),
}

pub fn attach(app: &tauri::App) -> Result<(), Box<dyn std::error::Error>> {
    let handle = app.handle();
    warn_about_drift();

    // Read once, before the menu is built, because it decides whether a row
    // exists at all rather than how it looks. Defaults to showing them: the
    // registry's own `projection.unavailable = "disabled"`.
    let hide_unavailable = false;

    // The menu is GENERATED from `desktop/features.toml`, in file order.
    //
    // It used to be eight items typed out by hand while the registry marked
    // sixteen features available — so clipboard copy, clipboard send, both
    // captures and the entire listening submenu were built, declared, and
    // unreachable. Two sources of truth drift; one cannot.
    //
    // File order is menu order: the registry is already grouped and reads top
    // to bottom the way a menu should, so a separate ordering field would be
    // one more thing to keep in step.
    let mut builder = MenuBuilder::new(handle);
    let mut header: Option<MenuItem<tauri::Wry>> = None;
    let mut ticks: Vec<(String, CheckMenuItem<tauri::Wry>)> = Vec::new();

    for feature in crate::features::roots() {
        let Some(built) = build_row(handle, feature, hide_unavailable, &mut ticks) else {
            continue;
        };
        match built {
            MenuKind::Header(item) => {
                builder = builder.item(&item).separator();
                header = Some(item);
            }
            MenuKind::Plain(item) => {
                // The one piece of furniture the registry does not describe:
                // quitting is not another action in the list.
                if feature.id == "quit" {
                    builder = builder.item(&PredefinedMenuItem::separator(handle)?);
                }
                builder = builder.item(&item);
            }
            MenuKind::Check(item) => builder = builder.item(&item),
            MenuKind::Sub(sub) => builder = builder.item(&sub),
        }
    }

    // Looked up by id from what was actually built — including the rows built
    // inside a submenu, which is where hands-free lives.
    let find = |id: &str| {
        ticks
            .iter()
            .find(|(known, _)| known == id)
            .map(|(_, item)| item.clone())
    };
    let mute = find("mute_replies");
    let hands_free_item = find("listen_hands_free");

    let menu = builder.build()?;

    // Every field is optional now, because every row is the registry's to
    // include or leave out. A tray with no header is a tray whose registry
    // says not to have one — not a bug to paper over with a placeholder.
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
                // Stop listening, whichever way it is listening. Two
                // mechanisms, one row: hands-free holds the microphone across
                // takes, a short take holds it for one. "Off" that only
                // handled one of them would leave the mic open half the time.
                "listen_off" => {
                    if crate::hands_free::running() {
                        crate::hands_free::stop("turned off from the tray");
                    }
                    if crate::listen::listening() {
                        crate::listen::release();
                    }
                }
                // A fast command the console already matches before any model
                // sees it, so the tray gets no privileged path of its own —
                // this row and typing "copy that" do the identical thing.
                "clipboard_copy_last" => say_from_tray(app, "copy that"),
                // `never_one_click` in the registry, all three of them, and
                // this is what that field means. A tray click cannot know
                // which window you meant, and it must never be the thing that
                // approves sending your screen or your clipboard anywhere —
                // the clipboard could hold a password and the screen could
                // hold anything. So the row takes you to where the decision
                // is made, with the destination and the gate visible.
                "clipboard_send" | "capture_this_turn" | "capture_region" => {
                    show_main(app);
                    eval_tray(app, id);
                }
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
                    // And the SERVER's, which is the switch that actually
                    // decides whether a reply is spoken aloud. Before this,
                    // the tray's checkbox only ever reached the webview's own
                    // `autoRead` preference — so the tray could read "muted"
                    // while `assistant_reply` happily spoke every reply
                    // through the bridge. One control, one meaning.
                    store_mute(app, muted);
                }
                "listen_hands_free" => {
                    // The tick follows the outcome, not the click: starting
                    // can fail, and a ticked box over a closed microphone is
                    // the one state this must never show.
                    let on = crate::toggle_hands_free(app);
                    if let Some(item) =
                        app.try_state::<TrayUi>().and_then(|s| s.inner().hands_free.clone())
                    {
                        warn_on_err("hands_free set_checked", item.set_checked(on));
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

    // The initial tick is READ, not assumed. It used to default to checked
    // because it mirrored the webview's `autoRead` (off by default), while
    // the setting that actually silences replies defaults to on — so the tray
    // opened life disagreeing with itself.
    {
        let app_for_mute = handle.clone();
        // Skipped rather than defaulted when the registry leaves the row out:
        // there is no tick to correct, and the console's own setting is still
        // what decides whether a reply is spoken.
        let item = ui.mute.clone();
        let _ = std::thread::Builder::new()
            .name("mute-initial".into())
            .spawn(move || {
                let url = app_for_mute
                    .try_state::<Mutex<ShellState>>()
                    .and_then(|s| s.inner().lock().ok().map(|g| g.console_url.clone()))
                    .unwrap_or_default();
                if url.is_empty() {
                    return;
                }
                let settings = crate::console_settings::all(&url);
                let speak = settings
                    .get("speak")
                    .and_then(|v| v.as_bool())
                    .unwrap_or(true);
                let muted = !speak;
                warn_on_err(
                    "initial mute sync",
                    app_for_mute.run_on_main_thread(move || {
                        if let Some(item) = item {
                            let _ = item.set_checked(muted);
                        }
                    }),
                );
                note_mute(&app_for_mute, muted);
            });
    }

    // Hands-free can end without anyone clicking the row — the session time
    // cap expires, or the microphone goes away. This keeps the tick honest in
    // those cases; without it the menu would claim an open microphone that had
    // already closed itself.
    //
    // Only started when the row exists. A polling thread whose only job is to
    // correct a tick that is not on screen is pure cost — and `if let` rather
    // than an early return, because everything below this still has to be set
    // up: a registry with no hands-free row must not also cost the tray its
    // backend header.
    if let Some(watched) = ui.hands_free.clone() {
        let app_for_sync = handle.clone();
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
        if let Some(header) = header_cb.as_ref() {
            warn_on_err("header set_text", header.set_text(label));
        }
        if let Some(mute) = mute_cb.as_ref() {
            warn_on_err("mute set_checked", mute.set_checked(payload.muted));
        }
        note_mute(&app_for_events, payload.muted);
    });

    Ok(())
}

fn ui_mute(app: &AppHandle) -> Option<CheckMenuItem<tauri::Wry>> {
    app.try_state::<TrayUi>().and_then(|s| s.inner().mute.clone())
}

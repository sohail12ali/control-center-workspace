#![windows_subsystem = "windows"]

mod audio;
mod bridge;
mod capture;
mod click;
mod clipboard;
mod console_settings;
mod hands_free;
mod icons;
mod listen;
mod logger;
mod ocr;
mod sidecar;
mod stt;
mod tray;
mod tray_link;
mod tray_paint;
mod tray_state;
mod tts;

#[cfg(windows)]
mod job;

use std::collections::HashMap;
use std::sync::{Arc, Mutex};

use sidecar::Handle;
use tauri::{Manager, WebviewUrl, WebviewWindowBuilder};

pub struct ShellState {
    owned: bool,
    pid: Option<u32>,
    repo_root: std::path::PathBuf,
    quitting: bool,
    /// Where the console is serving. The listen flow POSTs the transcript
    /// there, so it is kept here rather than re-derived.
    console_url: String,
}

/// Start one spoken command on a worker thread.
///
/// Every entry point — the hotkey, the tray, the bridge — comes through here,
/// so "already listening" and the tray transitions are decided in one place
/// rather than three.
pub fn begin_listening(app: &tauri::AppHandle) {
    let Some(state) = app.try_state::<Mutex<ShellState>>() else {
        return;
    };
    let (root, url) = match state.inner().lock() {
        Ok(s) => (s.repo_root.clone(), s.console_url.clone()),
        Err(_) => return,
    };
    let Some(assistant) = app.try_state::<Arc<Mutex<tray_state::Assistant>>>() else {
        return;
    };
    let assistant = assistant.inner().clone();
    if listen::listening() {
        // A second take would interleave two open microphones into one
        // unusable recording. Releasing the first is the useful reading of a
        // second press.
        log::info!("listen: already listening, treating this as a release");
        listen::release();
        return;
    }
    let _ = std::thread::Builder::new()
        .name("listen".into())
        .spawn(move || match listen::take(&root, &assistant, &url) {
            Ok(text) => log::info!("listen: sent {text:?}"),
            Err(e) => log::info!("listen: {e}"),
        });
}

/// Turn always-on listening on or off. Returns the state it left it in, so a
/// tray checkbox can show what actually happened rather than what was asked
/// for — starting can fail (no speech model), and a checkbox that ticks anyway
/// would be lying.
pub fn toggle_hands_free(app: &tauri::AppHandle) -> bool {
    if hands_free::running() {
        hands_free::stop("turned off from the tray");
        return false;
    }
    let Some(state) = app.try_state::<Mutex<ShellState>>() else {
        return false;
    };
    let (root, url) = match state.inner().lock() {
        Ok(s) => (s.repo_root.clone(), s.console_url.clone()),
        Err(_) => return false,
    };
    let Some(assistant) = app.try_state::<Arc<Mutex<tray_state::Assistant>>>() else {
        return false;
    };
    let assistant = assistant.inner().clone();
    let policy = hands_free::fetch_policy(&url);
    match hands_free::start(&root, assistant, url, policy) {
        Ok(()) => true,
        Err(e) => {
            log::warn!("hands-free: {e}");
            alert(&format!("Hands-free listening could not start.

{e}"));
            false
        }
    }
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

/// `--console` or `DESKTOP_CONSOLE=1` — the escape hatch back to a visible
/// console now that the host is an unconditional GUI subsystem.
fn console_requested() -> bool {
    std::env::args().any(|a| a == "--console")
        || std::env::var("DESKTOP_CONSOLE")
            .map(|v| v == "1")
            .unwrap_or(false)
}

#[cfg(windows)]
fn maybe_attach_console() {
    if !console_requested() {
        return;
    }
    use windows_sys::Win32::System::Console::{AllocConsole, AttachConsole, ATTACH_PARENT_PROCESS};
    unsafe {
        // Prefer the console of whoever launched us (so output lands in the
        // caller's terminal); fall back to a fresh one if there isn't one.
        if AttachConsole(ATTACH_PARENT_PROCESS) == 0 {
            AllocConsole();
        }
    }
}

#[cfg(not(windows))]
fn maybe_attach_console() {
    // No console concept to attach to outside Windows — `--console` is a
    // documented no-op there (see desktop/README.md).
}

/// The only trace of a crash left once stdout/stderr have no window to
/// appear in. `alert()` stays the user-visible fatal path, unchanged.
fn install_panic_hook() {
    std::panic::set_hook(Box::new(|info| {
        log::error!("panic: {info}");
        alert(&info.to_string());
    }));
}

/// Log then show the fatal alert, then end the process. Every hard startup
/// failure funnels through here — one place that decides what "fatal" means
/// and that a failure always exits non-zero, instead of near-identical
/// inline blocks at each call site risking drift (an earlier version of this
/// function let the `find_repo_root` failure return with exit code 0).
fn fatal(context: &str, msg: &str) -> ! {
    log::error!("{context}: {msg}");
    alert(msg);
    std::process::exit(1);
}

fn stop_owned(state: &ShellState) {
    // The speech engine holds a loaded model; leaving it resident after a
    // quit would be a 150 MB surprise in Task Manager.
    stt::shutdown();
    // Remove the pointer first. If the shell is going away, a console that
    // reads a live-looking pointer would hand a model a tool that then fails
    // mid-turn; better it reports "shell not running" from the next call on.
    bridge::clear_pointer(&state.repo_root);
    if state.owned {
        if let Some(pid) = state.pid {
            log::info!("quit: stopping owned sidecar pid={pid}");
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
    log::info!("window: main webview opened");
    Ok(())
}

/// Push-to-talk.
///
/// Registered from Rust, which is why no webview capability is widened for
/// it. A chord already owned by another application fails here, and that is
/// reported rather than silently doing nothing — a hotkey that does nothing
/// is indistinguishable from a broken microphone.
fn register_hotkey(app: &tauri::AppHandle) {
    use tauri_plugin_global_shortcut::{Code, Modifiers, Shortcut, ShortcutState};

    let chord = if cfg!(target_os = "macos") {
        Shortcut::new(Some(Modifiers::SUPER | Modifiers::ALT), Code::Space)
    } else {
        Shortcut::new(Some(Modifiers::CONTROL | Modifiers::ALT), Code::Space)
    };

    let handle = app.clone();
    match app.plugin(
        tauri_plugin_global_shortcut::Builder::new()
            .with_handler(move |_app, _shortcut, event| {
                // Fire on press only. Holding the chord and releasing it is
                // handled by the take's own end-pointing, so a press is
                // "start, or finish what is running".
                if event.state() == ShortcutState::Pressed {
                    begin_listening(&handle);
                }
            })
            .build(),
    ) {
        Ok(()) => {}
        Err(e) => {
            log::warn!("hotkey: plugin not registered ({e}); use the tray instead");
            return;
        }
    }

    use tauri_plugin_global_shortcut::GlobalShortcutExt;
    match app.global_shortcut().register(chord) {
        Ok(()) => log::info!("hotkey: push-to-talk registered"),
        Err(e) => log::warn!(
            "hotkey: could not register the chord ({e}); another app may own \
             it. The tray icon still starts a take"
        ),
    }
}

fn main() {
    install_panic_hook();
    maybe_attach_console();

    // Resolved before the builder starts so the logger — and everything
    // after it — has somewhere to write from the first line.
    let root = match sidecar::find_repo_root() {
        Ok(r) => r,
        Err(e) => fatal("startup", &e.0),
    };

    if let Err(e) = logger::FileLogger::init(root.join("console/.cache/desktop/host.log")) {
        // Non-fatal: a log file that cannot be opened must not stop the
        // shell from starting.
        eprintln!("logger init failed: {e}");
    }
    log::info!("startup: repo_root={}", root.display());

    tauri::Builder::default()
        // Registered first so a second launch is caught before anything
        // else runs: focus the existing window instead of a second instance
        // racing the first for the port and the tray icon.
        .plugin(tauri_plugin_single_instance::init(|app, _argv, _cwd| {
            log::info!("single-instance: second launch detected, focusing the existing window");
            tray::show_main(app);
        }))
        .setup(move |app| {
            // The tray's own view of what the assistant is doing. Shared with
            // the bridge so `GET /state` reports the same thing the icon shows
            // rather than a second, drifting copy.
            let assistant = Arc::new(Mutex::new(tray_state::Assistant::default()));
            // Managed as the Arc itself so the hotkey and the bridge can each
            // reach the same state without a second copy.
            app.manage(assistant.clone());

            let handle = match sidecar::ensure(&root, &HashMap::new()) {
                Ok(h) => h,
                Err(e) => fatal("ensure", &e.0),
            };
            log::info!(
                "ensure: sidecar owned={} pid={:?} url={}",
                handle.owned, handle.pid, handle.url
            );

            // Started after the sidecar because it needs the console's own
            // URL to hand a transcript to. There is no race in that
            // ordering: the console reads the pointer file per tool call, not
            // at startup, so it cannot look before this has written one.
            //
            // A bridge that fails to bind is not fatal — the console degrades
            // to "shell not running", which is a path it already handles
            // honestly.
            match bridge::start(&root, assistant.clone(), handle.url.clone()) {
                Ok(b) => log::info!(
                    "bridge: up at {}, pointer {}",
                    b.base_url,
                    b.pointer.display()
                ),
                Err(e) => log::warn!("bridge: not started ({e}) - desktop tools stay unavailable"),
            }

            #[cfg(windows)]
            if handle.owned {
                if let Some(pid) = handle.pid {
                    if let Some(j) = job::Job::new() {
                        let _ = j.add(pid);
                        std::mem::forget(j);
                        log::info!("job: pid={pid} added to job object");
                    }
                }
            }

            app.manage(Mutex::new(ShellState {
                owned: handle.owned,
                pid: handle.pid,
                repo_root: root.clone(),
                quitting: false,
                console_url: handle.url.clone(),
            }));

            if let Err(e) = open_window(app, &handle) {
                fatal("window", &e.to_string());
            }
            if let Err(e) = tray::attach(app) {
                fatal("tray", &e.to_string());
            }
            log::info!("tray: attached");

            // From here on, anything that changes the assistant's state can
            // repaint the icon — the microphone included, which before this
            // was the one thing that could not.
            tray_paint::attach(app.handle().clone());

            register_hotkey(app.handle());

            // Started after the tray exists, so the first repaint has
            // something to paint. It owns its own reconnects: the stream 404s
            // until an assistant chat exists, which is ordinary, not an error.
            tray_link::spawn(app.handle().clone(), assistant.clone(), handle.url.clone());

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
                    log::info!("close: window hidden, sidecar left running");
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

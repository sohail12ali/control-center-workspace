//! The voice overlay — the small panel that says what the assistant is doing.
//!
//! ## Why a window and not the tray
//!
//! The tray icon answers "is it listening" in a colour, five pixels wide, in
//! a corner you are not looking at. It cannot answer the questions that
//! actually come up while you are talking: is it hearing me *now*, and did it
//! get the words right. A level meter and a line of transcript answer both,
//! and they need somewhere to be drawn.
//!
//! ## Why the page is dumb
//!
//! `console/static/hud.html` has no API calls, no token and no polling. The
//! shell pushes state in with `eval`, exactly as it feeds the tray header.
//! An always-on-top panel with credentials in it would be a bad trade for a
//! level meter.
//!
//! ## Why it is created lazily and never destroyed
//!
//! Building a webview costs a beat; doing it on the first take and then
//! hiding it means every later take shows it instantly. Destroying and
//! rebuilding per take would put that cost back on every utterance.

use std::sync::atomic::{AtomicBool, Ordering};

use tauri::{AppHandle, Manager, WebviewUrl, WebviewWindowBuilder};

use crate::icons::State;

pub const LABEL: &str = "hud";

/// Panel size. Wide enough for a sentence of transcript at 12.5px, short
/// enough not to cover anything.
const WIDTH: f64 = 380.0;
const HEIGHT: f64 = 104.0;

/// Gap from the work-area corner, so the panel sits above the taskbar rather
/// than under it.
const MARGIN: f64 = 12.0;

/// Whether a take is currently feeding the meter.
static PUMPING: AtomicBool = AtomicBool::new(false);

/// Make sure the window exists. Returns false when it cannot be built, which
/// is not fatal: the tray still works and the voice loop does not care.
fn ensure(app: &AppHandle, console_url: &str) -> bool {
    if app.get_webview_window(LABEL).is_some() {
        return true;
    }
    let url = match format!("{}/hud.html", console_url.trim_end_matches('/')).parse() {
        Ok(u) => u,
        Err(e) => {
            log::warn!("hud: cannot build a url from {console_url}: {e}");
            return false;
        }
    };
    // Transparency is per-platform by necessity. Tauri gates it on macOS
    // behind `macos-private-api`, which is a private-API dependency and blocks
    // App Store distribution — a poor trade for rounded corners. So the window
    // is opaque there, and the page paints its own panel either way: on
    // Windows and Linux it floats with rounded corners, on macOS it is a
    // rectangle. Caught by CI, which builds all three.
    #[allow(unused_mut)]
    let mut built = WebviewWindowBuilder::new(app, LABEL, WebviewUrl::External(url))
        .title("Assistant")
        .inner_size(WIDTH, HEIGHT)
        .resizable(false)
        .decorations(false)
        .always_on_top(true)
        // Not a window you alt-tab to or find in the taskbar: it is a
        // read-out, and it must not take focus from what you are typing in.
        .skip_taskbar(true)
        .focused(false)
        .visible(false);
    #[cfg(not(target_os = "macos"))]
    {
        built = built.transparent(true);
    }
    let built = built.build();
    match built {
        Ok(window) => {
            place(&window);
            true
        }
        Err(e) => {
            log::warn!("hud: cannot create the overlay: {e}");
            false
        }
    }
}

/// Bottom-right of the work area on Windows and Linux, top-right on macOS —
/// each next to where that platform keeps its tray.
fn place(window: &tauri::WebviewWindow) {
    let Ok(Some(monitor)) = window.current_monitor() else {
        return;
    };
    let scale = monitor.scale_factor();
    let size = monitor.size().to_logical::<f64>(scale);
    let origin = monitor.position().to_logical::<f64>(scale);
    let x = origin.x + size.width - WIDTH - MARGIN;
    #[cfg(target_os = "macos")]
    let y = origin.y + MARGIN * 2.0;
    #[cfg(not(target_os = "macos"))]
    // 48px of taskbar plus the margin. `current_monitor` reports the full
    // screen rather than the work area, so this is the one number here that
    // is an estimate; being a little high is invisible, being low hides the
    // panel behind the taskbar.
    let y = origin.y + size.height - HEIGHT - MARGIN - 48.0;
    let _ = window.set_position(tauri::LogicalPosition::new(x, y));
}

fn push(app: &AppHandle, json: &str) {
    if let Some(window) = app.get_webview_window(LABEL) {
        let js = format!("try{{window.HUD&&window.HUD.set({json})}}catch(e){{}}");
        if let Err(e) = window.eval(&js) {
            log::debug!("hud: eval failed: {e}");
        }
    }
}

/// Show the panel with a state, and start the meter if we are listening.
pub fn show(app: &AppHandle, console_url: &str, state: State, hint: &str) {
    if !ensure(app, console_url) {
        return;
    }
    let Some(window) = app.get_webview_window(LABEL) else {
        return;
    };
    place(&window);
    let _ = window.show();
    // Re-asserted on every show: another window going full-screen can push a
    // topmost window behind it, and the panel is useless underneath.
    let _ = window.set_always_on_top(true);
    push(
        app,
        &format!(
            "{{\"state\":\"{}\",\"hint\":{}}}",
            state.as_str(),
            json_string(hint)
        ),
    );
    if matches!(state, State::Listening | State::Armed) {
        start_pump(app.clone());
    }
    arm_watchdog(app.clone());
}

/// Show the panel with a permission card up.
///
/// A state of its own, rather than one of `icons::State`. Those describe what
/// the ICON can say in five pixels, and "a human is being asked" is not one of
/// them — `ApprovalNeeded` folds into `Thinking` there, which is right for a
/// coloured dot in a corner and wrong for a panel that can carry two buttons.
/// The panel is allowed a bigger vocabulary because it has the room.
pub fn approval(app: &AppHandle, console_url: &str, tool: &str) {
    if !ensure(app, console_url) {
        return;
    }
    let Some(window) = app.get_webview_window(LABEL) else {
        return;
    };
    place(&window);
    let _ = window.show();
    let _ = window.set_always_on_top(true);
    PUMPING.store(false, Ordering::SeqCst);
    push(
        app,
        &format!(
            "{{\"state\":\"approval\",\"hint\":{},\"text\":{}}}",
            json_string("allow or deny"),
            json_string(&if tool.is_empty() {
                "waiting for you to allow or deny".to_string()
            } else {
                format!("{tool} wants to run")
            })
        ),
    );
    // A card that nobody answers is denied on the console's own timeout, so
    // the panel must not be the thing that outlives the question. Restarted
    // here because a card can arrive while an earlier watchdog is pending.
    arm_watchdog(app.clone());
}

/// What was heard, or what is being said back.
pub fn text(app: &AppHandle, line: &str) {
    push(app, &format!("{{\"text\":{}}}", json_string(line)));
}

pub fn state(app: &AppHandle, state: State) {
    push(app, &format!("{{\"state\":\"{}\"}}", state.as_str()));
    if !matches!(state, State::Listening | State::Armed) {
        PUMPING.store(false, Ordering::SeqCst);
    }
    // A state change is the definition of "something happened", so it retires
    // whichever watchdog was counting down and starts a fresh one.
    arm_watchdog(app.clone());
}

/// Hide the panel now, at the user's request.
///
/// The ✕ and Esc both land here. Deliberately unconditional and immediate: a
/// dismissal that waited for the state machine to agree would be the same bug
/// in a politer form, and the panel is a read-out — nothing is lost by
/// closing it, because everything it shows is also in the chat.
pub fn dismiss(app: &AppHandle) {
    PUMPING.store(false, Ordering::SeqCst);
    if let Some(window) = app.get_webview_window(LABEL) {
        if let Err(e) = window.hide() {
            log::warn!("hud: dismiss could not hide the panel: {e}");
        }
    }
}

/// Longest the panel may stay up with nothing new to say.
///
/// The backstop that turns every remaining stuck-state bug into a cosmetic
/// one. The panel used to hide only on three events, and one of them was
/// missing: an approval that resolved published nothing to hide it, and a
/// dropped event stream cleared a stale "Working" but never a stale card. So
/// an always-on-top window could sit over your work indefinitely, with no
/// close button, until the shell was killed.
///
/// Two minutes because it has to be longer than a slow turn — hiding the
/// panel while a model is still thinking would be worse than leaving it — and
/// far shorter than "forever".
const WATCHDOG: std::time::Duration = std::time::Duration::from_secs(120);

/// Bumped on every state change; the watchdog only fires if it is unchanged.
static GENERATION: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);

/// Hide the panel if nothing has changed by the time `WATCHDOG` elapses.
///
/// A generation counter rather than a timestamp, so "did anything happen"
/// needs no clock arithmetic and no lock: the thread reads the number it was
/// born with, and if it still matches, nothing has moved since.
fn arm_watchdog(app: AppHandle) {
    let mine = GENERATION.fetch_add(1, Ordering::SeqCst) + 1;
    let _ = std::thread::Builder::new()
        .name("hud-watchdog".into())
        .spawn(move || {
            std::thread::sleep(WATCHDOG);
            if GENERATION.load(Ordering::SeqCst) != mine {
                return; // something happened; a newer watchdog owns this
            }
            log::warn!(
                "hud: nothing changed for {}s — hiding the panel rather than \
                 leaving it over the screen",
                WATCHDOG.as_secs()
            );
            if let Some(window) = app.get_webview_window(LABEL) {
                let _ = window.hide();
            }
        });
}

/// Hide after `linger`, so a reply can be read before the panel goes.
pub fn hide_soon(app: &AppHandle, linger: std::time::Duration) {
    PUMPING.store(false, Ordering::SeqCst);
    let app = app.clone();
    let _ = std::thread::Builder::new()
        .name("hud-hide".into())
        .spawn(move || {
            std::thread::sleep(linger);
            // Another take may have started while we waited; hiding then
            // would blank the panel in the middle of being useful.
            if PUMPING.load(Ordering::SeqCst) {
                return;
            }
            if let Some(window) = app.get_webview_window(LABEL) {
                let _ = window.hide();
            }
        });
}

/// Feed the level meter while a take is open.
///
/// 15 Hz: fast enough to look like sound, slow enough to be nothing on a
/// CPU. Ends itself when the state leaves listening, so nothing has to
/// remember to stop it.
fn start_pump(app: AppHandle) {
    if PUMPING.swap(true, Ordering::SeqCst) {
        return; // already running
    }
    let _ = std::thread::Builder::new()
        .name("hud-level".into())
        .spawn(move || {
            while PUMPING.load(Ordering::SeqCst) {
                let level = crate::audio::level();
                push(&app, &format!("{{\"level\":{level:.3}}}"));
                std::thread::sleep(std::time::Duration::from_millis(66));
            }
            push(&app, "{\"level\":0}");
        });
}

/// Minimal JSON string escaping — the transcript is recogniser output, and a
/// stray quote in it must not break the push.
fn json_string(text: &str) -> String {
    let mut out = String::with_capacity(text.len() + 2);
    out.push('"');
    for c in text.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' | '\r' => out.push(' '),
            c if (c as u32) < 0x20 => out.push(' '),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

#[cfg(test)]
mod tests {
    use super::json_string;

    #[test]
    fn a_transcript_with_a_quote_in_it_is_escaped() {
        assert_eq!(json_string("say \"hi\""), "\"say \\\"hi\\\"\"");
        assert_eq!(json_string("a\\b"), "\"a\\\\b\"");
    }

    #[test]
    fn control_characters_become_spaces() {
        assert_eq!(json_string("one\ntwo"), "\"one two\"");
        assert_eq!(json_string("tab\there"), "\"tab here\"");
    }
}

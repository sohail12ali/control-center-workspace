//! The one place a state change becomes pixels.
//!
//! ## Why this module exists
//!
//! It exists because of a bug it makes impossible. `repaint` used to be
//! private to `tray_link`, reachable only from the console's event stream, so
//! everything the SHELL knows — the mic opening, a take being transcribed, an
//! utterance discarded — folded into the state machine and stopped there. The
//! icon then caught up whenever some unrelated console event happened to
//! trigger a repaint, which reads as a tray that lags or lies.
//!
//! So the painter is one module that every source of events calls, rather than
//! an `AppHandle` threaded through four of them.
//!
//! ## Why a global handle rather than a parameter
//!
//! `listen` and `hands_free` run on their own threads, started before and
//! outliving any particular window, and neither has any other reason to know
//! about Tauri. Passing an `AppHandle` down to them would put a UI type in the
//! signature of "record some audio". The handle is set once at setup and is
//! read-only afterwards, which is what `OnceLock` is for.
//!
//! Before it is set — in unit tests, and during startup before the tray
//! exists — painting is a no-op rather than a panic. A state machine that
//! cannot be exercised without a desktop session would be much harder to test
//! than one that simply has nothing to paint on.

use std::sync::{Arc, Mutex, OnceLock};

use tauri::image::Image;
use tauri::AppHandle;

use crate::icons::State;
use crate::tray_state::{Assistant, Event};

/// Tray icon id, as built in `tray.rs`.
const TRAY_ID: &str = "main";

static HANDLE: OnceLock<AppHandle> = OnceLock::new();
static CONSOLE_URL: OnceLock<String> = OnceLock::new();

/// Called once from setup, after the tray icon exists.
///
/// The console url comes along because the overlay is a page served by the
/// console. Kept here rather than in `hud` so there is one place that knows
/// how to reach the UI at all.
pub fn attach(app: AppHandle, console_url: String) {
    if HANDLE.set(app).is_err() {
        log::warn!("tray-paint: already attached; ignoring the second handle");
    }
    let _ = CONSOLE_URL.set(console_url);
}

/// What was just heard, or just said — shown in the overlay.
pub fn said(line: &str) {
    if let Some(app) = HANDLE.get() {
        crate::hud::text(app, line);
    }
}

/// Fold an event in and repaint if the visual changed.
///
/// `apply` already answers "did this change anything the user can see", so the
/// caller never diffs anything and an event that changes nothing costs one
/// lock and no icon work.
pub fn note(assistant: &Arc<Mutex<Assistant>>, event: Event) {
    let before = assistant.lock().map(|a| a.shown()).unwrap_or(State::Idle);
    let changed = match assistant.lock() {
        Ok(mut a) => a.apply(event.clone()),
        Err(e) => {
            log::warn!("tray-paint: state lock poisoned: {e}");
            return;
        }
    };
    if changed {
        repaint(assistant);
    }
    // The overlay and the cues follow the SAME event, deliberately. Three
    // surfaces deciding for themselves what state the assistant is in is
    // three chances to disagree, and the tray showing idle over an open
    // microphone (T-009) is what that looks like.
    if HANDLE.get().is_none() {
        // No app: nothing to show a panel on and nothing to play a tone
        // through. Returning here also keeps unit tests from writing the
        // cue module's global mute flag, which is shared state they have no
        // business touching.
        return;
    }
    let after = assistant.lock().map(|a| a.shown()).unwrap_or(State::Idle);
    let muted = assistant.lock().map(|a| a.muted()).unwrap_or(false);
    crate::cue::set_muted(muted);
    announce(&event, before, after);
}

/// Move the overlay and play a cue for what just happened.
fn announce(event: &Event, before: State, after: State) {
    let Some(app) = HANDLE.get() else {
        return;
    };
    let url = CONSOLE_URL.get().cloned().unwrap_or_default();
    match event {
        Event::ListenStart => {
            // The cue goes with the mic actually being open, which is why
            // this is on the event rather than on the click: there is most of
            // a second between them, and a beep that came first would invite
            // you to talk into a microphone that is not on yet.
            crate::cue::play(crate::cue::Cue::Open);
            // The hint says what you can DO, not what is happening — the
            // label beside the dot already says that, and a panel that says
            // "Listening / listening" is using its second line on nothing.
            crate::hud::show(app, &url, after, "click the tray to send");
            crate::hud::text(app, "");
        }
        Event::Armed(true) => crate::hud::show(app, &url, after, "say the wake word"),
        Event::Armed(false) => crate::hud::hide_soon(app, LINGER),
        Event::Transcribing | Event::TurnStart => {
            crate::hud::show(app, &url, after, "");
        }
        Event::SpeakStart => crate::hud::state(app, after),
        Event::Cancel => {
            if before == State::Listening {
                crate::cue::play(crate::cue::Cue::Dropped);
                crate::hud::text(app, "nothing heard");
            }
            crate::hud::state(app, after);
            crate::hud::hide_soon(app, LINGER);
        }
        Event::TurnEnd | Event::SpeakStop => {
            crate::hud::state(app, after);
            if after == State::Idle {
                crate::hud::hide_soon(app, LINGER);
            }
        }
        Event::ApprovalNeeded => {
            crate::hud::show(app, &url, after, "open the window");
            crate::hud::text(app, "waiting for you to allow or deny");
        }
        Event::ApprovalResolved | Event::Mute(_) => {}
    }
}

/// How long the overlay stays after there is nothing left to report — long
/// enough to read the last line, short enough not to be furniture.
const LINGER: std::time::Duration = std::time::Duration::from_secs(4);

/// Push the current state onto the actual tray icon.
pub fn repaint(assistant: &Arc<Mutex<Assistant>>) {
    let Some(app) = HANDLE.get() else {
        return; // no tray yet, or a test
    };
    let (state, bytes, tooltip) = match assistant.lock() {
        Ok(a) => (a.shown(), a.icon(), a.tooltip()),
        Err(_) => return,
    };
    // Logged because a painted icon is otherwise invisible to everything
    // except a human looking at the tray — including to a test.
    log::info!("tray: painted {}", state.as_str());
    let step = std::time::Instant::now();
    let Some(tray) = app.tray_by_id(TRAY_ID) else {
        return;
    };
    let by_id_ms = step.elapsed().as_millis();
    let step = std::time::Instant::now();
    match Image::from_bytes(bytes) {
        Ok(image) => {
            let decoded_ms = step.elapsed().as_millis();
            let step = std::time::Instant::now();
            if let Err(e) = tray.set_icon(Some(image)) {
                log::warn!("tray-paint: set_icon failed: {e}");
            }
            log::debug!(
                "tray-paint: by_id {by_id_ms}ms, decode {decoded_ms}ms, set_icon {}ms",
                step.elapsed().as_millis()
            );
            #[cfg(target_os = "macos")]
            if let Err(e) = tray.set_icon_as_template(true) {
                log::warn!("tray-paint: set_icon_as_template failed: {e}");
            }
        }
        Err(e) => log::warn!("tray-paint: icon bytes rejected: {e}"),
    }
    let step = std::time::Instant::now();
    if let Err(e) = tray.set_tooltip(Some(&tooltip)) {
        log::warn!("tray-paint: set_tooltip failed: {e}");
    }
    log::debug!("tray-paint: set_tooltip {}ms", step.elapsed().as_millis());
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn noting_an_event_without_a_tray_still_moves_the_state() {
        // The property that keeps the state machine testable: no desktop
        // session, no handle, no panic — and the state still advances.
        let a = Arc::new(Mutex::new(Assistant::default()));
        note(&a, Event::ListenStart);
        assert_eq!(a.lock().unwrap().state(), State::Listening);
        repaint(&a);
    }

    #[test]
    fn a_poisoned_lock_is_survivable() {
        let a = Arc::new(Mutex::new(Assistant::default()));
        let poisoned = Arc::clone(&a);
        let _ = std::thread::spawn(move || {
            let _guard = poisoned.lock().unwrap();
            panic!("poison it");
        })
        .join();
        // A tray that cannot read its own state must degrade, not take the
        // shell down with it.
        note(&a, Event::ListenStart);
    }
}

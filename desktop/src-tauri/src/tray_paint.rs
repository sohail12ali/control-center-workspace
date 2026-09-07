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

use crate::tray_state::{Assistant, Event};

/// Tray icon id, as built in `tray.rs`.
const TRAY_ID: &str = "main";

static HANDLE: OnceLock<AppHandle> = OnceLock::new();

/// Called once from setup, after the tray icon exists.
pub fn attach(app: AppHandle) {
    if HANDLE.set(app).is_err() {
        log::warn!("tray-paint: already attached; ignoring the second handle");
    }
}

/// Fold an event in and repaint if the visual changed.
///
/// `apply` already answers "did this change anything the user can see", so the
/// caller never diffs anything and an event that changes nothing costs one
/// lock and no icon work.
pub fn note(assistant: &Arc<Mutex<Assistant>>, event: Event) {
    let changed = match assistant.lock() {
        Ok(mut a) => a.apply(event),
        Err(e) => {
            log::warn!("tray-paint: state lock poisoned: {e}");
            return;
        }
    };
    if changed {
        repaint(assistant);
    }
}

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
    let Some(tray) = app.tray_by_id(TRAY_ID) else {
        return;
    };
    match Image::from_bytes(bytes) {
        Ok(image) => {
            if let Err(e) = tray.set_icon(Some(image)) {
                log::warn!("tray-paint: set_icon failed: {e}");
            }
            #[cfg(target_os = "macos")]
            if let Err(e) = tray.set_icon_as_template(true) {
                log::warn!("tray-paint: set_icon_as_template failed: {e}");
            }
        }
        Err(e) => log::warn!("tray-paint: icon bytes rejected: {e}"),
    }
    if let Err(e) = tray.set_tooltip(Some(&tooltip)) {
        log::warn!("tray-paint: set_tooltip failed: {e}");
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::icons::State;

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

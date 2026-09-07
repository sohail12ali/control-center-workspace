//! What one left-click on the tray icon means.
//!
//! Split into a pure function and a doer, because the interesting half is the
//! decision and the decision is a table. `act` is four lines of dispatch to
//! entry points that already exist; `action` is the part with opinions in it,
//! and it can be tested without a tray, a microphone or a desktop session.
//!
//! ## Why the click is state-aware
//!
//! The icon is the nearest thing this app has to a microphone button, and it
//! already shows what the assistant is doing. Making the click mean "the
//! obvious thing to do about what you are looking at" keeps one gesture
//! honest across every state: talk when nothing is happening, send when you
//! are mid-take, shut it up when it is talking. The tooltip has promised
//! "click to stop" while speaking since T-006 — this is the code that finally
//! makes that true.
//!
//! ## Why it is configurable
//!
//! A tray click opens the app in most software, and someone who expects that
//! is not wrong. `tray_click_action` in the Assistant's settings switches this
//! to plain "show the window", or to arming hands-free.

use tauri::Manager;

use crate::icons::State;

/// The whole vocabulary of a click. Named after the user's intent, not the
/// function that carries it out, so the table below reads as a decision.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Action {
    /// Open the mic for one take.
    Talk,
    /// End the take in progress and send it now, rather than waiting for the
    /// silence detector — which on a noisy microphone can mean waiting for
    /// the whole cap.
    SendNow,
    /// Stop a reply being read aloud.
    StopSpeaking,
    ShowWindow,
    ToggleHandsFree,
}

/// Decide what a click does.
///
/// `needs_approval` outranks everything, in every mode: a permission card is
/// a question addressed to a human, and no amount of talking at the tray
/// answers it. Sending a take into a chat that is blocked on a card would put
/// words behind a modal nobody has read yet.
pub fn action(state: State, needs_approval: bool, setting: &str) -> Action {
    if needs_approval {
        return Action::ShowWindow;
    }
    match setting {
        "show" => Action::ShowWindow,
        // Barge-in survives every mode: if it is talking, the first thing a
        // click should be able to do is stop it.
        "hands_free" if state == State::Speaking => Action::StopSpeaking,
        "hands_free" => Action::ToggleHandsFree,
        // "listen", and anything unrecognised — the cautious reading of a bad
        // setting is the documented default, not nothing at all.
        _ => match state {
            State::Listening => Action::SendNow,
            State::Speaking => Action::StopSpeaking,
            // A turn is running and there is nothing useful to say to it;
            // showing the window is where the interrupt button lives.
            State::Thinking => Action::ShowWindow,
            // Idle, Muted, Armed. Armed included on purpose: hands-free is
            // waiting for a wake word, and a click is how you skip saying it.
            _ => Action::Talk,
        },
    }
}

/// Carry out a click. Every branch is an entry point that already existed.
pub fn act(app: &tauri::AppHandle) {
    let (state, needs_approval) = match app
        .try_state::<std::sync::Arc<std::sync::Mutex<crate::tray_state::Assistant>>>()
    {
        Some(s) => match s.inner().lock() {
            Ok(a) => (a.state(), a.needs_approval()),
            Err(_) => (State::Idle, false),
        },
        None => (State::Idle, false),
    };
    let setting = setting_for(app);
    let action = action(state, needs_approval, &setting);
    log::info!("tray: click in {} -> {action:?}", state.as_str());
    match action {
        Action::Talk => crate::begin_listening(app),
        Action::SendNow => {
            crate::listen::release();
        }
        Action::StopSpeaking => {
            crate::tts::stop();
        }
        Action::ShowWindow => crate::tray::show_main(app),
        Action::ToggleHandsFree => {
            crate::toggle_hands_free(app);
        }
    }
}

/// The configured meaning of a click, asked fresh each time.
///
/// Fresh rather than cached: settings are changed on the Settings tab in the
/// same app, and a cached value would mean the change did not take effect
/// until a restart, which nothing in the UI would tell you. The read is one
/// loopback request.
fn setting_for(app: &tauri::AppHandle) -> String {
    let url = app
        .try_state::<std::sync::Mutex<crate::ShellState>>()
        .and_then(|s| s.inner().lock().ok().map(|g| g.console_url.clone()))
        .unwrap_or_default();
    if url.is_empty() {
        return "listen".into();
    }
    crate::console_settings::string_or(&url, "tray_click_action", "listen")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_default_click_does_the_obvious_thing_for_each_state() {
        for (state, want) in [
            (State::Idle, Action::Talk),
            (State::Muted, Action::Talk),
            (State::Armed, Action::Talk),
            (State::Listening, Action::SendNow),
            (State::Speaking, Action::StopSpeaking),
            (State::Thinking, Action::ShowWindow),
        ] {
            assert_eq!(action(state, false, "listen"), want, "{:?}", state);
        }
    }

    #[test]
    fn a_permission_card_wins_over_every_state_and_every_setting() {
        // Words said at a tray cannot answer a question on screen.
        for setting in ["listen", "show", "hands_free"] {
            for state in [State::Idle, State::Listening, State::Speaking, State::Armed] {
                assert_eq!(action(state, true, setting), Action::ShowWindow,
                           "{setting} / {state:?}");
            }
        }
    }

    #[test]
    fn show_mode_always_opens_the_window() {
        for state in [State::Idle, State::Listening, State::Speaking, State::Thinking] {
            assert_eq!(action(state, false, "show"), Action::ShowWindow);
        }
    }

    #[test]
    fn hands_free_mode_arms_but_still_lets_you_shut_it_up() {
        assert_eq!(action(State::Idle, false, "hands_free"), Action::ToggleHandsFree);
        assert_eq!(action(State::Armed, false, "hands_free"), Action::ToggleHandsFree);
        assert_eq!(action(State::Speaking, false, "hands_free"), Action::StopSpeaking);
    }

    #[test]
    fn an_unrecognised_setting_falls_back_to_the_default_behaviour() {
        // A typo that reached the shell must not leave the icon inert.
        assert_eq!(action(State::Idle, false, "nonsense"), Action::Talk);
        assert_eq!(action(State::Listening, false, ""), Action::SendNow);
    }
}

//! Always-on listening.
//!
//! Push-to-talk asks you to say when you are talking to the assistant.
//! Hands-free removes that, and in doing so raises three problems that
//! push-to-talk simply does not have. Each one is answered here rather than
//! left to the user to discover.
//!
//! ## 1. Everything in the room would go to a model
//!
//! It does not. Audio is transcribed **on this machine**, and the transcript
//! is discarded unless it is addressed to the assistant by name. Leaving the
//! microphone on therefore means the room is heard locally and forgotten —
//! not sent anywhere. Only an addressed utterance becomes a turn.
//!
//! That can be switched off, for headphones-on, nobody-else-in-the-room use,
//! and it is off-by-default precisely because the alternative is a surprise.
//!
//! ## 2. The assistant would hear itself
//!
//! Through speakers, a spoken reply is picked up by the microphone,
//! transcribed, and answered — the assistant talking to itself in a loop. So
//! listening pauses while a reply is being read aloud. On headphones there is
//! no echo, and a setting keeps the microphone open, which is what makes
//! barge-in work by voice instead of by hotkey.
//!
//! ## 3. It would run forever
//!
//! A microphone left on by accident stops on its own after a configured
//! number of minutes, and says why.
//!
//! Everything else — how a take ends, transcription, dispatch — is the same
//! machinery push-to-talk uses. This module is a loop and three policies, not
//! a second voice pipeline.

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use crate::tray_state::{Assistant, Event};
use crate::{listen, tray_paint, tts};

/// Whether the loop should keep going. Also what `stop()` clears.
static RUNNING: AtomicBool = AtomicBool::new(false);

/// Why the loop last stopped, for the tray and `/listen/state`.
static LAST_STOP: Mutex<String> = Mutex::new(String::new());

/// How long to wait before looking again while paused (speaking, or a
/// permission card is open). Short enough to feel responsive, long enough not
/// to spin.
const PAUSE_POLL: Duration = Duration::from_millis(200);

/// Settings the loop needs, fetched from the console so `assistant.toml`
/// stays the single source of truth rather than being parsed twice.
#[derive(Clone, Debug)]
pub struct Policy {
    pub require_wake: bool,
    pub wake_word: String,
    pub listen_while_speaking: bool,
    pub max_minutes: u64,
}

impl Default for Policy {
    fn default() -> Self {
        // Matches `assistant_config.DEFAULTS`. Used only when the console
        // cannot be asked, and deliberately the cautious set.
        Self {
            require_wake: true,
            wake_word: "console".into(),
            listen_while_speaking: false,
            max_minutes: 30,
        }
    }
}

pub fn running() -> bool {
    RUNNING.load(Ordering::SeqCst)
}

pub fn last_stop_reason() -> String {
    LAST_STOP.lock().unwrap_or_else(|e| e.into_inner()).clone()
}

fn set_stop_reason(why: &str) {
    *LAST_STOP.lock().unwrap_or_else(|e| e.into_inner()) = why.to_string();
}

/// Ask the loop to finish. The take in flight is released, not abandoned.
pub fn stop(why: &str) {
    if RUNNING.swap(false, Ordering::SeqCst) {
        set_stop_reason(why);
        listen::release();
        log::info!("hands-free: stopping ({why})");
    }
}

/// Tell the tray the microphone is open, or no longer is.
///
/// The bool is `require_wake`, because that is the difference the icon is
/// reporting: a gated mic (armed) or one where everything said is sent
/// (listening).
fn show_armed(assistant: &Arc<Mutex<Assistant>>, on: bool, require_wake: bool) {
    tray_paint::note(assistant, Event::Armed(on && require_wake));
}

/// Is `transcript` addressed to the assistant?
///
/// Deliberately forgiving about what surrounds the wake word — a recogniser
/// adds punctuation and capitalisation of its own — and deliberately strict
/// about where it appears. Requiring it at the START is what makes the rule
/// predictable: "ask the console about X" addresses the assistant, while "the
/// console is slow today" does not, and a rule matching anywhere in the
/// sentence could not tell those apart.
pub fn is_addressed(transcript: &str, wake_word: &str) -> bool {
    let wake = wake_word.trim().to_lowercase();
    if wake.is_empty() {
        return true;
    }
    let text = transcript.trim().to_lowercase();
    // Strip leading filler a recogniser reliably produces before a name.
    let text = text
        .trim_start_matches(|c: char| !c.is_alphanumeric())
        .to_string();
    for prefix in ["hey ", "ok ", "okay ", "hi ", "yo "] {
        if let Some(rest) = text.strip_prefix(prefix) {
            return starts_with_word(rest, &wake);
        }
    }
    starts_with_word(&text, &wake)
}

/// `text` begins with `wake` as a whole word, not as a prefix of a longer one
/// — so "console" matches "console, what's open" but not "consolidate".
fn starts_with_word(text: &str, wake: &str) -> bool {
    match text.strip_prefix(wake) {
        None => false,
        Some("") => true,
        Some(rest) => !rest.chars().next().map(char::is_alphanumeric).unwrap_or(false),
    }
}


/// Ask the console for the current hands-free policy.
///
/// Fetched rather than parsed from `assistant.toml` directly: the console
/// already merges committed defaults with this machine's overrides, and a
/// second TOML reader here would be a second answer to the same question.
/// Falls back to the cautious defaults when the console cannot be reached,
/// which is the right way to be wrong about an always-on microphone.
pub fn fetch_policy(console_url: &str) -> Policy {
    match crate::console_settings::fetch(console_url) {
        Ok(v) => {
            let get_bool = |k: &str, d: bool| v.get(k).and_then(|x| x.as_bool()).unwrap_or(d);
            let d = Policy::default();
            Policy {
                require_wake: get_bool("hands_free_require_wake", d.require_wake),
                wake_word: v
                    .get("hands_free_wake_word")
                    .and_then(|x| x.as_str())
                    .filter(|s| s.trim().len() >= 2)
                    .unwrap_or(&d.wake_word)
                    .to_string(),
                listen_while_speaking: get_bool(
                    "hands_free_listen_while_speaking", d.listen_while_speaking),
                max_minutes: v
                    .get("hands_free_max_minutes")
                    .and_then(|x| x.as_u64())
                    .filter(|m| *m >= 1)
                    .unwrap_or(d.max_minutes),
            }
        }
        Err(e) => {
            log::warn!("hands-free: could not read settings ({e}); using cautious defaults");
            Policy::default()
        }
    }
}

/// Start the loop. Returns an error the caller can show if it cannot run.
pub fn start(
    repo_root: &std::path::Path,
    assistant: Arc<Mutex<Assistant>>,
    console_url: String,
    policy: Policy,
) -> Result<(), String> {
    if !listen::available(repo_root) {
        return Err(listen::hint(repo_root));
    }
    if RUNNING.swap(true, Ordering::SeqCst) {
        return Err("hands-free is already on".into());
    }
    set_stop_reason("");

    // Summarised before the policy moves into the thread.
    let summary = policy_summary(&policy);
    show_armed(&assistant, true, policy.require_wake);
    let root = repo_root.to_path_buf();
    std::thread::Builder::new()
        .name("hands-free".into())
        .spawn(move || run(root, assistant, console_url, policy))
        .map_err(|e| {
            RUNNING.store(false, Ordering::SeqCst);
            format!("cannot start hands-free: {e}")
        })?;
    log::info!("hands-free: on (wake word required: {summary})");
    Ok(())
}

fn policy_summary(policy: &Policy) -> String {
    if policy.require_wake {
        format!("yes, {:?}", policy.wake_word)
    } else {
        "no - every utterance is sent".into()
    }
}

fn run(
    repo_root: std::path::PathBuf,
    assistant: Arc<Mutex<Assistant>>,
    console_url: String,
    policy: Policy,
) {
    let started = Instant::now();
    let cap = Duration::from_secs(policy.max_minutes.max(1) * 60);

    while RUNNING.load(Ordering::SeqCst) {
        if started.elapsed() >= cap {
            stop("reached the time limit");
            break;
        }

        let speaking = !tts::finished();
        let awaiting_approval = assistant
            .lock()
            .map(|a| a.needs_approval())
            .unwrap_or(false);
        if should_pause(&policy, speaking, awaiting_approval) {
            std::thread::sleep(PAUSE_POLL);
            continue;
        }

        let policy_for_gate = policy.clone();
        match listen::take_gated(&repo_root, &assistant, &console_url, move |text| {
            should_send(text, &policy_for_gate)
        }) {
            Ok(sent) => log::info!("hands-free: sent {sent:?}"),
            Err(reason) => {
                // "nothing heard" is the normal outcome of a quiet room and
                // must not be logged as a problem or slow the loop down.
                if reason != "nothing heard"
                    && reason != "already listening"
                    && reason != "not addressed"
                {
                    log::info!("hands-free: {reason}");
                }
                if reason.contains("microphone") || reason.contains("engine") {
                    // A broken microphone would otherwise spin this loop.
                    stop(&reason);
                    break;
                }
            }
        }
    }

    RUNNING.store(false, Ordering::SeqCst);
    show_armed(&assistant, false, policy.require_wake);
    log::info!("hands-free: off ({})", last_stop_reason());
}

/// Should the loop hold the microphone shut for a moment?
///
/// Two reasons, and they are different reasons. Speaking is about echo: on
/// speakers the assistant hears its own reply and answers it, which is why
/// `listen_while_speaking` exists and why it is off by default. An open
/// approval card is about consent: someone reading "allow this?" out loud, or
/// talking it over with a colleague, must not have that recorded and sent as
/// their next instruction — so that pause is not configurable.
pub fn should_pause(policy: &Policy, speaking: bool, awaiting_approval: bool) -> bool {
    if awaiting_approval {
        return true;
    }
    speaking && !policy.listen_while_speaking
}

/// The wake-word gate, applied to a transcript before anything is sent.
///
/// Separate from the loop so `listen` can call it on the take it just made,
/// and so it can be tested without a microphone.
pub fn should_send(transcript: &str, policy: &Policy) -> bool {
    !policy.require_wake || is_addressed(transcript, &policy.wake_word)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn an_addressed_utterance_is_recognised() {
        for said in [
            "console what's open",
            "Console, what's open?",
            "hey console take a screenshot",
            "OK console, status ticket two",
            "  console  status  ",
        ] {
            assert!(is_addressed(said, "console"), "{said:?}");
        }
    }

    #[test]
    fn ordinary_conversation_is_not_addressed() {
        // This is the property that makes an always-on microphone tolerable:
        // the room is heard locally and forgotten.
        for said in [
            "the console is slow today",
            "I was talking to Sam about the console",
            "shall we get lunch",
            "consolidate the tickets",   // not a prefix match
            "",
        ] {
            assert!(!is_addressed(said, "console"), "{said:?}");
        }
    }

    #[test]
    fn the_wake_word_must_be_a_whole_word() {
        assert!(!is_addressed("consoles are great", "console"));
        assert!(is_addressed("console: status", "console"));
    }

    #[test]
    fn a_configured_wake_word_is_honoured() {
        assert!(is_addressed("jarvis what's open", "jarvis"));
        assert!(!is_addressed("console what's open", "jarvis"));
    }

    #[test]
    fn an_empty_wake_word_addresses_everything() {
        // Belt and braces: the console refuses to store one this short, but
        // if it ever arrived, failing open on the GATE would be wrong — so
        // this is the documented behaviour rather than an accident.
        assert!(is_addressed("anything at all", ""));
    }

    #[test]
    fn requiring_a_wake_word_is_what_decides_sending() {
        let strict = Policy::default();
        assert!(!strict.wake_word.is_empty());
        assert!(should_send("console status", &strict));
        assert!(!should_send("shall we get lunch", &strict));

        let open = Policy { require_wake: false, ..Policy::default() };
        assert!(should_send("shall we get lunch", &open));
    }

    #[test]
    fn the_cautious_defaults_are_the_defaults() {
        // If these drift, an always-on microphone starts behaving in a way
        // nobody chose.
        let p = Policy::default();
        assert!(p.require_wake, "unaddressed speech must not be sent by default");
        assert!(!p.listen_while_speaking, "the assistant must not hear itself");
        assert!(p.max_minutes >= 1, "it must stop on its own");
    }

    #[test]
    fn real_whisper_transcripts_are_gated_correctly() {
        // Not hand-written strings: these are exactly what whisper.cpp
        // (ggml-base.en) produced from spoken audio on 2026-09-07 — leading
        // spaces, capitalisation and punctuation included. A recogniser's
        // output is not the words you meant to type, and the gate has to hold
        // against the former.
        for said in ["  Console, what is open?", "  Hey console, take a screenshot"] {
            assert!(is_addressed(said, "console"), "{said:?}");
        }
        for said in ["  The console is slow today.", "  Shall we get lunch after this?"] {
            assert!(!is_addressed(said, "console"), "{said:?}");
        }
    }

    #[test]
    fn the_loop_pauses_while_a_reply_is_being_spoken() {
        let d = Policy::default();
        assert!(should_pause(&d, true, false), "it would answer its own voice");
        assert!(!should_pause(&d, false, false));

        // Headphones: no echo, so the microphone stays open and barge-in
        // works by voice.
        let phones = Policy { listen_while_speaking: true, ..Policy::default() };
        assert!(!should_pause(&phones, true, false));
    }

    #[test]
    fn an_open_approval_card_pauses_even_on_headphones() {
        // Not an echo question. Someone reading an approval out loud, or
        // talking it over, must not have that become their next instruction.
        let phones = Policy { listen_while_speaking: true, ..Policy::default() };
        assert!(should_pause(&phones, false, true));
        assert!(should_pause(&Policy::default(), false, true));
    }

    #[test]
    fn stopping_when_not_running_is_harmless() {
        stop("test");
        assert!(!running());
    }
}

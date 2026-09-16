//! One spoken command, start to finish.
//!
//! Record until the speaker stops, transcribe it, and hand the text to the
//! console's assistant — the same endpoint a typed message goes to, which is
//! the whole reason T-004 built that endpoint before any microphone existed.
//! Nothing here knows what a command means; that is the console's dispatch
//! table, and duplicating any of it would be a second place for it to differ.
//!
//! ## Why the tray state is set here and not inferred
//!
//! The console can tell the tray about a turn, but only the shell knows the
//! mic is open or that audio is being transcribed. Those two states are set
//! from this module, and the rest come off the console's stream in
//! `tray_link`. Between them the icon reflects the whole cycle.
//!
//! ## One take at a time
//!
//! A second listen while one is running is refused rather than queued: two
//! open microphones would interleave into one unusable recording, and the
//! honest answer to "you are already listening" is to say so.

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};

use crate::tray_state::{Assistant, Event};
use crate::console_settings;
use crate::console_api;
use crate::{audio, stt, tts};

/// Guards against two takes at once. An `AtomicBool` rather than the state
/// machine's own flag, because this must be correct even if a repaint is
/// mid-flight.
static LISTENING: AtomicBool = AtomicBool::new(false);

/// Set when a take should stop early — push-to-talk released, or cancelled.
static STOP: Mutex<bool> = Mutex::new(false);

pub type ListenResult<T> = Result<T, String>;

pub fn listening() -> bool {
    LISTENING.load(Ordering::SeqCst)
}

/// Ask the take in flight to finish now. Harmless when nothing is listening.
pub fn release() {
    *STOP.lock().unwrap_or_else(|e| e.into_inner()) = true;
}

/// Is speech usable at all right now? Drives `caps.stt` and the tray's
/// listening rows, so it must answer for this machine rather than for the
/// feature in principle.
pub fn available(repo_root: &std::path::Path) -> bool {
    audio::available() && stt::available(repo_root)
}

pub fn hint(repo_root: &std::path::Path) -> String {
    if !audio::available() {
        return "no microphone: nothing is set as the default input device".into();
    }
    stt::hint(repo_root)
}

/// Record, transcribe, and send. Blocking — the caller gives it a thread.
///
/// Returns the transcript so a caller (or a test) can see what was heard,
/// even though the console has already been given it.
pub fn take(
    repo_root: &std::path::Path,
    assistant: &Arc<Mutex<Assistant>>,
    console_url: &str,
) -> ListenResult<String> {
    // Push-to-talk: you already said this was for the assistant by pressing
    // the key, so there is nothing further to decide.
    take_gated(repo_root, assistant, console_url, |_| true)
}

/// A take whose transcript must pass `gate` before it is sent anywhere.
///
/// The gate is a closure rather than a policy type so this module does not
/// depend on `hands_free`, which depends on it. It exists for always-on
/// listening, where the transcript has to be checked for whether it was
/// addressed to the assistant at all — and where failing that check must mean
/// the words never leave this machine.
pub fn take_gated<F>(
    repo_root: &std::path::Path,
    assistant: &Arc<Mutex<Assistant>>,
    console_url: &str,
    gate: F,
) -> ListenResult<String>
where
    F: Fn(&str) -> bool,
{
    // No cached microphone: a push-to-talk take opens one and closes it, so
    // the OS indicator is lit exactly while it is recording.
    take_gated_on(&mut None, repo_root, assistant, console_url, gate)
}

/// A gated take that may REUSE an already-open microphone.
///
/// For hands-free, where the mic is openly on for the whole session: closing
/// and reopening it between takes buys no privacy — it just makes the
/// assistant deaf for the second it takes to reopen, which is exactly where
/// the next wake word lands. `cpal::Stream` is not `Send`, so the cache
/// belongs to the caller's thread, which is where the loop lives anyway.
pub fn take_gated_on<F>(
    mic: &mut Option<audio::Mic>,
    repo_root: &std::path::Path,
    assistant: &Arc<Mutex<Assistant>>,
    console_url: &str,
    gate: F,
) -> ListenResult<String>
where
    F: Fn(&str) -> bool,
{
    if LISTENING.swap(true, Ordering::SeqCst) {
        return Err("already listening".into());
    }
    // Whatever happens below, the flag and the tray must come back.
    let outcome = take_inner(mic, repo_root, assistant, console_url, &gate, None);
    LISTENING.store(false, Ordering::SeqCst);
    if outcome.is_err() {
        note(assistant, Event::Cancel);
    }
    outcome
}

/// A take that begins in the PAST, because the wake word has already fired.
///
/// By the time a spotter recognises a phrase, the phrase has been said — so a
/// take that starts "now" starts after the interesting part. `from` is a
/// cursor into the microphone's ring, taken a second before the firing, and
/// the audio it names is still there.
///
/// There is no gate: the wake word WAS the gate, and it ran on the audio
/// rather than on a transcript, so nothing here has to decide again.
pub fn take_after_wake(
    mic: &mut Option<audio::Mic>,
    from: u64,
    repo_root: &std::path::Path,
    assistant: &Arc<Mutex<Assistant>>,
    console_url: &str,
) -> ListenResult<String> {
    if LISTENING.swap(true, Ordering::SeqCst) {
        return Err("already listening".into());
    }
    let outcome = take_inner(
        mic, repo_root, assistant, console_url, &|_: &str| true, Some(from));
    LISTENING.store(false, Ordering::SeqCst);
    if outcome.is_err() {
        note(assistant, Event::Cancel);
    }
    outcome
}

/// The two limits a take runs under, from the console's merged settings.
///
/// `patient` is the hands-free shape: a longer first pause, because somebody
/// who has just said a wake word and stopped is thinking rather than finished.
/// Push-to-talk passes false — there, a short take is a short command.
pub fn limits_from(settings: &serde_json::Value, patient: bool) -> audio::Limits {
    let trailing = std::time::Duration::from_millis(console_settings::u64_at(
        settings, "listen_silence_ms",
        audio::DEFAULT_TRAILING_SILENCE.as_millis() as u64,
    ));
    audio::Limits {
        max_take: std::time::Duration::from_secs(console_settings::u64_at(
            settings, "listen_max_seconds", audio::DEFAULT_MAX_TAKE.as_secs(),
        )),
        trailing_silence: trailing,
        first_pause: if patient {
            std::time::Duration::from_millis(console_settings::u64_at(
                settings, "listen_first_pause_ms",
                audio::DEFAULT_FIRST_PAUSE.as_millis() as u64,
            ))
        } else {
            trailing
        },
    }
}

fn take_inner<F>(
    mic: &mut Option<audio::Mic>,
    repo_root: &std::path::Path,
    assistant: &Arc<Mutex<Assistant>>,
    console_url: &str,
    gate: &F,
    from: Option<u64>,
) -> ListenResult<String>
where
    F: Fn(&str) -> bool,
{
    // Timed end to end. A voice loop is judged on how long it makes you wait,
    // and "it feels slow" is not something anyone can fix — so every take says
    // where its seconds went.
    let began = std::time::Instant::now();
    if !audio::available() {
        return Err(hint(repo_root));
    }
    if !stt::available(repo_root) {
        return Err(stt::hint(repo_root));
    }
    let checked_ms = began.elapsed().as_millis();

    // A reply being read aloud would otherwise be recorded back into the
    // microphone. Stopping it IS barge-in: talking over the assistant
    // interrupts it, which is what a person expects.
    let step = std::time::Instant::now();
    if tts::stop() {
        note(assistant, Event::SpeakStop);
    }
    log::debug!("listen: step tts_stop {}ms", step.elapsed().as_millis());

    *STOP.lock().unwrap_or_else(|e| e.into_inner()) = false;
    let stop = Arc::new(Mutex::new(false));
    let stop_watch = stop.clone();
    // Bridge the module-level flag into the recorder's own, so `release()`
    // from an HTTP request or a hotkey reaches a take already in progress.
    let watcher = std::thread::Builder::new()
        .name("listen-stop".into())
        .spawn(move || loop {
            if *STOP.lock().unwrap_or_else(|e| e.into_inner()) {
                *stop_watch.lock().unwrap_or_else(|e| e.into_inner()) = true;
                return;
            }
            if !LISTENING.load(Ordering::SeqCst) {
                return;
            }
            std::thread::sleep(std::time::Duration::from_millis(50));
        })
        .ok();

    // Both limits, and the model, come from the console's merged settings —
    // one reader for the whole shell. Asked for once per take rather than
    // cached, so changing them on the Settings tab takes effect on the next
    // thing you say instead of the next time you launch.
    log::debug!("listen: step watcher {}ms", step.elapsed().as_millis());
    let step = std::time::Instant::now();
    let settings = console_settings::all(console_url);
    log::debug!("listen: step settings {}ms", step.elapsed().as_millis());
    let limits = limits_from(&settings, from.is_some());
    stt::prefer_model(&console_settings::str_at(&settings, "stt_model", "base.en"));
    // Tell the decoder what it is about to hear. Ticket ids and the wake word
    // are exactly the words a general model has no reason to expect, and
    // exactly the ones a spoken command turns on.
    stt::prefer_prompt(&stt::prompt_for(
        &console_settings::str_at(&settings, "hands_free_wake_word", ""),
        &console_settings::str_at(&settings, "ticket_prefix", "T-"),
    ));

    let step = std::time::Instant::now();
    note(assistant, Event::ListenStart);
    log::debug!("listen: step paint_listening {}ms", step.elapsed().as_millis());
    let opening = std::time::Instant::now();
    if mic.is_none() {
        *mic = Some(audio::Mic::open()?);
    }
    let open = mic.as_mut().expect("just opened");
    let recorded = match from {
        // Pre-roll: the wake word was said before it was recognised.
        Some(cursor) => open.record_from(cursor, stop, limits),
        None => open.take(stop, limits),
    };
    if recorded.is_err() {
        // A microphone that failed mid-take may have been unplugged. Drop it
        // so the next take opens a fresh one rather than retrying a handle to
        // a device that is gone.
        *mic = None;
    }
    let recorded_ms = opening.elapsed().as_millis();
    // The watcher exits on its own once LISTENING clears or STOP is seen; it
    // is joined so a take never leaves a thread behind.
    LISTENING.store(false, Ordering::SeqCst);
    if let Some(w) = watcher {
        let _ = w.join();
    }
    LISTENING.store(true, Ordering::SeqCst);

    let take = recorded?;
    log::debug!("listen: step after_record {}ms", opening.elapsed().as_millis().saturating_sub(recorded_ms));
    if take.ending == audio::Ending::NothingHeard {
        note(assistant, Event::Cancel);
        return Err("nothing heard".into());
    }
    log::info!(
        "listen: {:.1}s of audio, ended by {:?}",
        take.seconds(),
        take.ending
    );

    let step = std::time::Instant::now();
    note(assistant, Event::Transcribing);
    log::debug!("listen: step paint_thinking {}ms", step.elapsed().as_millis());
    let step = std::time::Instant::now();
    let wav = take.wav();
    log::debug!("listen: step wav {}ms", step.elapsed().as_millis());
    let transcribing = std::time::Instant::now();
    let text = stt::transcribe(repo_root, &wav)?;
    let stt_ms = transcribing.elapsed().as_millis();
    let text = text.trim().to_string();
    if text.is_empty() {
        note(assistant, Event::Cancel);
        return Err("the speech engine returned nothing".into());
    }
    // The gate runs HERE: after local transcription, before anything is sent.
    // That ordering is the whole privacy argument for always-on listening —
    // unaddressed speech is heard, transcribed on this machine, and dropped,
    // rather than travelling anywhere to be judged.
    if !gate(&text) {
        // Say that something was heard and dropped — but never WHAT. The
        // transcript of unaddressed speech does not leave this machine, and a
        // log file on it is still leaving the moment it is written.
        //
        // Silence here is what made hands-free look broken: it heard, it
        // discarded, and nothing anywhere said so, which is identical to a
        // dead microphone from the outside.
        log::info!("listen: heard {} words, not addressed - discarded",
                   text.split_whitespace().count());
        crate::tray_paint::said("heard you - say the wake word first");
        note(assistant, Event::Cancel);
        return Err("not addressed".into());
    }
    log::info!("listen: heard {text:?}");
    // Shown before it is sent, so the first thing you see is what it thought
    // you said — the answer to "did it get that right" arrives before the
    // answer to the question itself.
    crate::tray_paint::said(&text);

    // Handing it to the console is what makes a spoken command and a typed
    // one the same thing.
    let sending = std::time::Instant::now();
    console_api::say(console_url, &text, "voice")?;
    crate::cue::play(crate::cue::Cue::Sent);
    // One line, whole take, in the order the user experiences it. `checks` is
    // the part before the microphone is even asked to open — the part nobody
    // suspects until it is printed.
    log::info!(
        "listen: took {}ms (checks {}ms, record {}ms for {:.1}s of audio,          stt {}ms, post {}ms)",
        began.elapsed().as_millis(),
        checked_ms,
        recorded_ms,
        take.seconds(),
        stt_ms,
        sending.elapsed().as_millis()
    );
    Ok(text)
}

/// Tell the tray what just happened.
///
/// Through `tray_paint` rather than straight into the state machine: this used
/// to apply the event and stop, so the mic could open with the icon still
/// showing idle until something else repainted it.
fn note(assistant: &Arc<Mutex<Assistant>>, event: Event) {
    crate::tray_paint::note(assistant, event);
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_hint_explains_whichever_half_is_missing() {
        let empty = std::env::temp_dir().join("t006-nothing-here");
        let h = hint(&empty);
        assert!(!h.is_empty());
        assert!(h.contains("microphone") || h.contains("get-whisper"), "{h}");
    }

    #[test]
    fn release_is_safe_when_nothing_is_listening() {
        release();
        assert!(!listening());
    }
}

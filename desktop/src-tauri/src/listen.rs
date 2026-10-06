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
use crate::{audio, devices, stt, tts};

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

/// Test hook: makes `take_in_progress` say yes without a real take, which
/// would need a microphone. Separate from `LISTENING` so a test using it cannot
/// make `listening()` lie to the others running beside it.
#[cfg(test)]
static FORCE_BUSY: AtomicBool = AtomicBool::new(false);

#[cfg(test)]
pub fn force_busy(busy: bool) {
    FORCE_BUSY.store(busy, Ordering::SeqCst);
}

/// Is a take in flight? What the mic test refuses on.
pub fn take_in_progress() -> bool {
    #[cfg(test)]
    if FORCE_BUSY.load(Ordering::SeqCst) {
        return true;
    }
    listening()
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

/// The settings that decide what the shell hears and says, besides the take
/// limits: the speech model and the prompt it is given, the voice and its
/// speed, and the two audio devices.
///
/// Read in one place (`extract_voice_settings`) and put to work in one place
/// (`apply_voice_settings`), so a take and the settings refresh cannot disagree
/// about what a key means (T-031 D-7).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct VoiceSettings {
    pub model: String,
    pub prompt: String,
    pub voice: String,
    pub rate_percent: u64,
    pub input_device: String,
    pub output_device: String,
}

/// Read the voice settings out of the console's merged settings. Pure.
///
/// A key that is missing or blank takes its default, which for the devices and
/// the voice is "automatic". Values are trimmed.
pub fn extract_voice_settings(settings: &serde_json::Value) -> VoiceSettings {
    VoiceSettings {
        model: console_settings::str_at(settings, "stt_model", "base.en"),
        prompt: stt::prompt_for(
            &console_settings::str_at(settings, "hands_free_wake_word", ""),
            &console_settings::str_at(settings, "ticket_prefix", "T-"),
        ),
        voice: console_settings::str_at(settings, "speak_voice", ""),
        rate_percent: console_settings::u64_at(settings, "speak_rate_percent", 100),
        input_device: console_settings::str_at(settings, "input_device", ""),
        output_device: console_settings::str_at(settings, "output_device", ""),
    }
}

/// What a re-apply actually changed. Only a real change costs anything: a new
/// engine for the model or prompt, a reopened microphone for the input device.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct Applied {
    pub model_changed: bool,
    pub prompt_changed: bool,
    pub input_changed: bool,
    pub output_changed: bool,
    /// Either device name changed.
    pub device_changed: bool,
}

impl Applied {
    /// Is the speech engine now running something other than what is wanted?
    pub fn engine_changed(&self) -> bool {
        self.model_changed || self.prompt_changed
    }
}

/// Where the preferences land. The shell's are process-wide (`Shell`); a test
/// hands in its own, so tests running in parallel cannot disturb each other or
/// the real engine. Each setter returns whether the value changed.
pub trait Preferences {
    fn model(&self, name: &str) -> bool;
    fn prompt(&self, text: &str) -> bool;
    fn voice(&self, repo_root: &std::path::Path, voice: &str, rate_percent: u64);
    fn input(&self, name: &str) -> bool;
    fn output(&self, name: &str) -> bool;
}

/// The shell's own preferences: the engine's, the synthesiser's and the
/// devices'.
struct Shell;

impl Preferences for Shell {
    fn model(&self, name: &str) -> bool {
        let changed = stt::preferred_model() != name;
        stt::prefer_model(name);
        changed
    }
    fn prompt(&self, text: &str) -> bool {
        let changed = stt::prompt() != text;
        stt::prefer_prompt(text);
        changed
    }
    fn voice(&self, repo_root: &std::path::Path, voice: &str, rate_percent: u64) {
        tts::choose(voice);
        tts::configure(repo_root, voice, rate_percent as f32 / 100.0);
    }
    fn input(&self, name: &str) -> bool {
        devices::PREFS.set_input(name)
    }
    fn output(&self, name: &str) -> bool {
        devices::PREFS.set_output(name)
    }
}

/// Put `settings` into `prefs` and say what changed.
pub fn apply_voice_settings_on(
    prefs: &dyn Preferences,
    repo_root: &std::path::Path,
    settings: &VoiceSettings,
) -> Applied {
    let input_changed = prefs.input(&settings.input_device);
    let output_changed = prefs.output(&settings.output_device);
    prefs.voice(repo_root, &settings.voice, settings.rate_percent);
    Applied {
        model_changed: prefs.model(&settings.model),
        prompt_changed: prefs.prompt(&settings.prompt),
        input_changed,
        output_changed,
        device_changed: input_changed || output_changed,
    }
}

/// Apply the voice settings to the shell.
pub fn apply_voice_settings(repo_root: &std::path::Path, settings: &VoiceSettings) -> Applied {
    apply_voice_settings_on(&Shell, repo_root, settings)
}

/// Read and apply the console's merged settings.
///
/// `None` when `settings` is not an object, which is what `console_settings`
/// returns when the console cannot be reached. An outage must apply NOTHING:
/// reading it as "every key at its default" would reset the user's model and
/// devices, and swap the engine and reopen the microphone, because a request
/// timed out.
pub fn apply_settings(repo_root: &std::path::Path, settings: &serde_json::Value) -> Option<Applied> {
    if !settings.is_object() {
        return None;
    }
    Some(apply_voice_settings(repo_root, &extract_voice_settings(settings)))
}

/// Two quick pokes apply in the order they came, not whichever finishes last.
static REFRESH: Mutex<()> = Mutex::new(());

/// The settings poke's work: forget the cached settings, read them again, apply
/// them, and start the new model in the background when that changed. Blocking
/// (the console may stall for seconds), so the bridge gives it a thread and
/// answers the poke first (T-031 D-15).
pub fn refresh_settings(repo_root: &std::path::Path, console_url: &str) -> Option<Applied> {
    let _in_order = REFRESH.lock().unwrap_or_else(|e| e.into_inner());
    console_settings::forget();
    let settings = console_settings::all(console_url);
    let Some(applied) = apply_settings(repo_root, &settings) else {
        log::info!("settings: the console did not answer the refresh; nothing was applied");
        return None;
    };
    if applied != Applied::default() {
        log::info!("settings: refreshed, {applied:?}");
    }
    if applied.engine_changed() {
        // Usually done before the next take, instead of that take paying for it.
        stt::prewarm(repo_root);
    }
    Some(applied)
}

/// What to do about the microphone before a take.
#[derive(Debug, PartialEq, Eq, Clone, Copy)]
pub enum Reopen {
    /// An open microphone still matches the input setting.
    Keep,
    /// There is none: open one.
    Open,
    /// The input setting changed since it was opened: close it, open another.
    Replace,
}

/// The decision, and the pre-roll cursor the take may still use.
#[derive(Debug, PartialEq, Eq, Clone, Copy)]
pub struct ReopenPlan {
    pub action: Reopen,
    pub from: Option<u64>,
}

/// Decide whether a cached microphone can serve the next take. Pure.
///
/// A pre-roll cursor is a position in ONE microphone's ring. A new microphone
/// has a ring of its own, so a cursor from the one it replaced points at audio
/// that was never recorded (or past the end of it): the take starts now
/// instead, and the old audio is gone with the old device.
pub fn reopen_decision(has_mic: bool, stale: bool, from: Option<u64>) -> ReopenPlan {
    match (has_mic, stale) {
        (true, false) => ReopenPlan { action: Reopen::Keep, from },
        (true, true) => ReopenPlan { action: Reopen::Replace, from: None },
        (false, _) => ReopenPlan { action: Reopen::Open, from: None },
    }
}

/// What a take says when the Settings microphone test holds the device.
/// Matched by `hands_free::stops_loop`, which must NOT treat it as a broken mic.
pub const MIC_TEST_BUSY: &str = "a microphone test is running; try again in a moment";

/// Why a take may not open a microphone now, or `None`. A cached microphone
/// that stays in use opens nothing, so there is nothing to refuse. Pure.
pub fn take_refusal(mic_test_running: bool, will_open: bool) -> Option<&'static str> {
    (mic_test_running && will_open).then_some(MIC_TEST_BUSY)
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
    // The Settings microphone test has the device for two seconds: a second
    // open beside it is refused (before any side effect) rather than raced.
    let will_open = mic.as_ref().map(|m| m.needs_reopen()).unwrap_or(true);
    if let Some(why) = take_refusal(crate::voice_test::running(&crate::voice_test::shell_state()), will_open) {
        return Err(why.into());
    }
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
    // The model, the decoder prompt (ticket ids and the wake word are exactly
    // the words a general model has no reason to expect, and the ones a spoken
    // command turns on), the voice and the devices: one applier, shared with
    // the settings refresh. `transcribe` starts any swap the change implies.
    apply_settings(repo_root, &settings);

    let step = std::time::Instant::now();
    note(assistant, Event::ListenStart);
    log::debug!("listen: step paint_listening {}ms", step.elapsed().as_millis());
    let opening = std::time::Instant::now();
    // A cached microphone (hands-free keeps one for the whole session) is
    // still recording from the device it opened on. If the input setting has
    // moved since, it is replaced here rather than used one more time.
    let plan = reopen_decision(
        mic.is_some(),
        mic.as_ref().map(|m| m.needs_reopen()).unwrap_or(false),
        from,
    );
    if plan.action != Reopen::Keep {
        if plan.action == Reopen::Replace {
            log::info!("listen: the input device changed; reopening the microphone");
        }
        // Dropped first: the old stream has to let go of its device before a
        // new one opens, and a failed open must not leave the old one behind.
        *mic = None;
        *mic = Some(audio::Mic::open()?);
    }
    let from = plan.from;
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
        // Either half may be what is missing. The speech half names where to
        // fix it, which differs per OS: Windows has a script that installs the
        // engine; the other systems have none and point at Settings.
        let stt_half = if cfg!(windows) { "get-whisper" } else { "Settings" };
        assert!(h.contains("microphone") || h.contains(stt_half), "{h}");
    }

    #[test]
    fn release_is_safe_when_nothing_is_listening() {
        release();
        assert!(!listening());
    }

    // -- reopening on a device change (T-031 AC-56) -------------------------

    #[test]
    fn with_no_microphone_one_is_opened_and_a_stale_cursor_is_not_trusted() {
        assert_eq!(
            reopen_decision(false, false, None),
            ReopenPlan { action: Reopen::Open, from: None }
        );
        // A cursor with nothing to point into belongs to some earlier mic.
        assert_eq!(reopen_decision(false, false, Some(48_000)).from, None);
    }

    #[test]
    fn an_unchanged_setting_keeps_the_microphone_and_its_preroll() {
        assert_eq!(
            reopen_decision(true, false, Some(48_000)),
            ReopenPlan { action: Reopen::Keep, from: Some(48_000) }
        );
        assert_eq!(reopen_decision(true, false, None).from, None);
    }

    #[test]
    fn a_changed_setting_replaces_the_microphone_and_drops_the_preroll() {
        // The cursor was taken on the OLD microphone's ring; the take starts
        // now on the new one.
        assert_eq!(
            reopen_decision(true, true, Some(48_000)),
            ReopenPlan { action: Reopen::Replace, from: None }
        );
        assert_eq!(reopen_decision(true, true, None).action, Reopen::Replace);
    }

    #[test]
    fn re_applying_an_identical_preference_reopens_nothing() {
        // The settings poke re-applies every preference on every write. Only a
        // real change may cost a reopen, or each unrelated settings edit would
        // make hands-free deaf for a second.
        let prefs = crate::devices::Prefs::new();
        prefs.set_input("Headset");
        let opened_under = prefs.input_generation();

        prefs.set_input("Headset");
        prefs.set_input("  Headset ");
        let stale = crate::devices::needs_reopen(opened_under, prefs.input_generation());
        assert_eq!(reopen_decision(true, stale, Some(1)).action, Reopen::Keep);

        prefs.set_input("Array Mic");
        let stale = crate::devices::needs_reopen(opened_under, prefs.input_generation());
        assert_eq!(reopen_decision(true, stale, Some(1)).action, Reopen::Replace);
    }

    #[test]
    fn the_take_path_and_the_armed_loop_both_ask_the_microphone_whether_to_reopen() {
        // Production code only: the test module also spells the method, so it
        // is cut off before looking.
        for (name, source) in [
            ("listen.rs", include_str!("listen.rs")),
            ("hands_free.rs", include_str!("hands_free.rs")),
        ] {
            let production = source.split("mod tests {").next().unwrap();
            assert!(production.contains(".needs_reopen()"), "{name} never checks needs_reopen");
        }
    }

    // -- the voice settings, read once and applied once (T-031 AC-42) ------

    use serde_json::json;

    #[test]
    fn missing_keys_take_the_defaults() {
        for settings in [serde_json::Value::Null, json!({}), json!({"stt_model": "   "})] {
            let v = extract_voice_settings(&settings);
            assert_eq!(v.model, "base.en");
            assert_eq!(v.voice, "");
            assert_eq!(v.rate_percent, 100);
            assert_eq!(v.input_device, "");
            assert_eq!(v.output_device, "");
        }
    }

    #[test]
    fn values_are_trimmed_and_read_from_their_keys() {
        let v = extract_voice_settings(&json!({
            "stt_model": "  small.en ",
            "speak_voice": " en_US-amy-medium ",
            "speak_rate_percent": 140,
            "input_device": "  USB Headset Mic  ",
            "output_device": "\tSpeakers (Realtek) ",
        }));
        assert_eq!(v.model, "small.en");
        assert_eq!(v.voice, "en_US-amy-medium");
        assert_eq!(v.rate_percent, 140);
        assert_eq!(v.input_device, "USB Headset Mic");
        assert_eq!(v.output_device, "Speakers (Realtek)");
    }

    #[test]
    fn the_wake_word_and_the_ticket_prefix_feed_the_prompt() {
        let v = extract_voice_settings(&json!({
            "hands_free_wake_word": " Computer ",
            "ticket_prefix": "CC-",
        }));
        assert_eq!(v.prompt, stt::prompt_for("Computer", "CC-"));
        assert!(v.prompt.contains("Computer, what is open?"), "{}", v.prompt);
        assert!(v.prompt.contains("CC-002"), "{}", v.prompt);
        // Neither set: the ticket prefix defaults, the wake word is simply absent.
        let plain = extract_voice_settings(&json!({}));
        assert_eq!(plain.prompt, stt::prompt_for("", "T-"));
    }

    /// Preferences of a test's own, so nothing here touches the process-wide
    /// ones the real engine and the other tests read.
    struct Fake {
        devices: devices::Prefs,
        model: Mutex<String>,
        prompt: Mutex<String>,
        voice: Mutex<(String, u64)>,
    }

    impl Fake {
        fn new() -> Self {
            Fake {
                devices: devices::Prefs::new(),
                model: Mutex::new(String::new()),
                prompt: Mutex::new(String::new()),
                voice: Mutex::new((String::new(), 0)),
            }
        }
    }

    fn set_if_new(slot: &Mutex<String>, value: &str) -> bool {
        let mut slot = slot.lock().unwrap();
        let changed = *slot != value;
        *slot = value.to_string();
        changed
    }

    impl Preferences for Fake {
        fn model(&self, name: &str) -> bool { set_if_new(&self.model, name) }
        fn prompt(&self, text: &str) -> bool { set_if_new(&self.prompt, text) }
        fn voice(&self, _root: &std::path::Path, voice: &str, rate_percent: u64) {
            *self.voice.lock().unwrap() = (voice.to_string(), rate_percent);
        }
        fn input(&self, name: &str) -> bool { self.devices.set_input(name) }
        fn output(&self, name: &str) -> bool { self.devices.set_output(name) }
    }

    fn settings_with(input: &str, output: &str, model: &str) -> VoiceSettings {
        extract_voice_settings(&json!({
            "input_device": input, "output_device": output, "stt_model": model,
        }))
    }

    #[test]
    fn a_device_change_is_reported_once_and_bumps_the_generation_once() {
        let fake = Fake::new();
        let root = std::path::Path::new(".");
        let first = apply_voice_settings_on(&fake, root, &settings_with("", "", "base.en"));
        assert!(!first.device_changed, "nothing was configured and nothing is now");
        assert_eq!(fake.devices.input_generation(), 0);

        let moved = apply_voice_settings_on(&fake, root, &settings_with("Headset Mic", "", "base.en"));
        assert!(moved.device_changed && moved.input_changed && !moved.output_changed);
        assert_eq!(fake.devices.input_generation(), 1, "one change, one bump");
        assert_eq!(fake.devices.output_generation(), 0);

        // The poke re-applies every key on every write. An identical device must
        // not count as a change, or each unrelated edit would reopen the mic.
        for _ in 0..3 {
            let same = apply_voice_settings_on(&fake, root, &settings_with("Headset Mic", "", "base.en"));
            assert!(!same.device_changed, "{same:?}");
        }
        assert_eq!(fake.devices.input_generation(), 1);

        let out = apply_voice_settings_on(&fake, root, &settings_with("Headset Mic", "Speakers", "base.en"));
        assert!(out.device_changed && out.output_changed && !out.input_changed);
        assert_eq!(fake.devices.output_generation(), 1);
        assert_eq!(fake.devices.input_generation(), 1, "the input did not move");
    }

    #[test]
    fn only_a_model_or_prompt_change_asks_for_a_new_engine() {
        let fake = Fake::new();
        let root = std::path::Path::new(".");
        apply_voice_settings_on(&fake, root, &settings_with("", "", "base.en"));

        let devices_only = apply_voice_settings_on(&fake, root, &settings_with("Mic", "", "base.en"));
        assert!(!devices_only.engine_changed(), "a device is not the engine's business");

        let model = apply_voice_settings_on(&fake, root, &settings_with("Mic", "", "tiny.en"));
        assert!(model.model_changed && !model.prompt_changed && model.engine_changed());

        let mut with_prompt = settings_with("Mic", "", "tiny.en");
        with_prompt.prompt.push_str(" Extra.");
        let prompt = apply_voice_settings_on(&fake, root, &with_prompt);
        assert!(prompt.prompt_changed && !prompt.model_changed && prompt.engine_changed());

        let nothing = apply_voice_settings_on(&fake, root, &with_prompt);
        assert_eq!(nothing, Applied::default());
    }

    #[test]
    fn the_voice_and_speed_are_handed_to_the_synthesiser() {
        let fake = Fake::new();
        let v = extract_voice_settings(&json!({"speak_voice": "en_US-ryan-medium", "speak_rate_percent": 80}));
        apply_voice_settings_on(&fake, std::path::Path::new("."), &v);
        assert_eq!(*fake.voice.lock().unwrap(), ("en_US-ryan-medium".to_string(), 80));
    }

    #[test]
    fn settings_that_are_not_an_object_apply_nothing() {
        // `console_settings::all` answers Null when the console is down. That
        // must not look like "everything is at its default".
        let before = (stt::preferred_model(), stt::prompt(), devices::PREFS.input_generation());
        for down in [serde_json::Value::Null, json!("oops"), json!([1, 2]), json!(7)] {
            assert_eq!(apply_settings(std::path::Path::new("."), &down), None, "{down}");
        }
        assert_eq!(
            before,
            (stt::preferred_model(), stt::prompt(), devices::PREFS.input_generation()),
            "nothing global moved"
        );
    }

    #[test]
    fn a_refresh_against_an_unreachable_console_applies_nothing() {
        // Port 1 is closed on loopback: the fetch fails at once, as it does
        // when the console is not running.
        let before = (stt::preferred_model(), stt::prompt(), devices::PREFS.input_generation());
        assert_eq!(refresh_settings(std::path::Path::new("."), "http://127.0.0.1:1"), None);
        assert_eq!(
            before,
            (stt::preferred_model(), stt::prompt(), devices::PREFS.input_generation())
        );
    }

    #[test]
    fn a_take_applies_through_the_same_pair_as_the_refresh() {
        // One applier (D-7): `take_inner` must not grow a private copy of the
        // reads that `extract_voice_settings` owns.
        let production = include_str!("listen.rs").split("mod tests {").next().unwrap();
        let take = production.split("fn take_inner").nth(1).expect("take_inner exists");
        let take = take.split("\nfn note(").next().unwrap();
        assert!(take.contains("apply_settings("), "take_inner no longer applies the settings");
        for private_read in ["prefer_model(", "prefer_prompt(", "\"stt_model\"", "\"speak_voice\""] {
            assert!(!take.contains(private_read), "take_inner reads {private_read} itself");
        }
    }

    // -- a take does not open a second microphone beside the test (T-031 FIX-1)

    #[test]
    fn a_take_that_would_open_a_microphone_is_refused_while_the_test_runs() {
        let why = take_refusal(true, true).expect("refused");
        assert_eq!(why, MIC_TEST_BUSY);
        assert!(why.contains("microphone test is running"), "{why}");
        assert!(why.contains("try again"), "{why}");
        assert_eq!(take_refusal(false, true), None);
        assert_eq!(take_refusal(false, false), None);
        // A microphone that is already open is not opened again: nothing to refuse.
        assert_eq!(take_refusal(true, false), None);
    }

    #[test]
    fn take_inner_asks_before_it_opens_a_microphone() {
        let production = include_str!("listen.rs").split("mod tests {").next().unwrap();
        let take = production.split("fn take_inner").nth(1).expect("take_inner exists");
        let ask = take.find("take_refusal(").expect("take_inner consults the mic test");
        let open = take.find("audio::Mic::open()").expect("take_inner opens a mic");
        assert!(ask < open, "the check must come before the open");
    }
}

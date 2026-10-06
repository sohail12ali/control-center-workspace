//! The Settings "Test microphone" and "Test speaker" buttons.
//!
//! ## What the microphone test is, and is not
//!
//! It opens a FRESH `Mic` on the input device the shell would use, listens for
//! two seconds, and reports the loudest sample it saw. That is all it keeps:
//! each chunk is reduced to a peak and dropped, nothing is written to disk and
//! nothing is sent anywhere (T-031 D-11, BR-15). It runs on its own thread
//! because the bridge handles one request at a time.
//!
//! What a script can show is that the device opened and the peak lies in 0..1.
//! That the bar follows a real voice is something only a person can check.

use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use cpal::traits::DeviceTrait;
use serde_json::{json, Value};

/// How long the microphone is listened to.
pub const MIC_TEST: Duration = Duration::from_secs(2);

/// The loudest sample as a fraction of full scale, 0..1. `i16::MIN` is 1.0.
pub fn peak_of(samples: &[i16]) -> f32 {
    let loudest = samples.iter().map(|s| (*s as i32).abs()).max().unwrap_or(0);
    (loudest as f32 / 32768.0).clamp(0.0, 1.0)
}

/// Why a mic test may not start now, or `None` when it may.
pub fn refuse_reason(listening: bool, hands_free: bool, already_running: bool) -> Option<&'static str> {
    if listening {
        Some("a take is in progress: the microphone is in use")
    } else if hands_free {
        Some("hands-free is listening: turn it off to test the microphone")
    } else if already_running {
        Some("a microphone test is already running")
    } else {
        None
    }
}

/// Where the test's samples come from. The shell's is an open `Mic`; a test
/// hands in a fake, so nothing here needs hardware.
pub trait Source {
    fn device(&self) -> String;
    /// Whatever arrived since the last call.
    fn read(&mut self) -> Vec<i16>;
}

struct MicSource {
    mic: crate::audio::Mic,
    cursor: u64,
}

impl Source for MicSource {
    fn device(&self) -> String {
        self.mic.device_name().to_string()
    }
    fn read(&mut self) -> Vec<i16> {
        let (next, samples) = self.mic.since(self.cursor);
        self.cursor = next;
        samples
    }
}

/// Clears `running` however the test thread ends, a panic included. Without
/// it a panic would leave `running` true and refuse every later test.
struct RunGuard(Shared);

impl Drop for RunGuard {
    fn drop(&mut self) {
        let mut s = self.0.lock().unwrap_or_else(|e| e.into_inner());
        if s.running && std::thread::panicking() && s.error.is_empty() {
            s.error = "the microphone test stopped unexpectedly".into();
        }
        s.running = false;
    }
}

#[derive(Default)]
pub struct State {
    running: bool,
    peak: f32,
    device: String,
    error: String,
}

pub type Shared = Arc<Mutex<State>>;

static STATE: Mutex<Option<Shared>> = Mutex::new(None);

/// The shell's one mic-test state.
pub fn shell_state() -> Shared {
    STATE.lock().unwrap_or_else(|e| e.into_inner()).get_or_insert_with(Shared::default).clone()
}

/// `{running, peak, device}` and `error` only when a start failed.
pub fn state_json(state: &Shared) -> Value {
    let s = state.lock().unwrap_or_else(|e| e.into_inner());
    let mut v = json!({"running": s.running, "peak": s.peak, "device": s.device});
    if !s.error.is_empty() {
        v["error"] = json!(s.error);
    }
    v
}

pub fn running(state: &Shared) -> bool {
    state.lock().unwrap_or_else(|e| e.into_inner()).running
}

/// Wait until no test is running, polling every `poll`, for at most `bound`.
/// True when idle. The other half of the guard: a test refuses to start while
/// a take is listening, and whatever wants to open the microphone waits (or
/// refuses) while a test holds it. Pure over `running`, so it needs no device.
pub fn wait_idle_with(mut running: impl FnMut() -> bool, bound: Duration, poll: Duration) -> bool {
    let end = Instant::now() + bound;
    while running() {
        if Instant::now() >= end {
            return false;
        }
        std::thread::sleep(poll);
    }
    true
}

/// `wait_idle_with` on the shell's own mic test.
pub fn wait_idle(bound: Duration) -> bool {
    let state = shell_state();
    wait_idle_with(|| running(&state), bound, Duration::from_millis(50))
}

/// Start the test and return AT ONCE. The thread opens the source, reads it for
/// `duration`, publishes the running peak through `state` and `on_level`, then
/// drops the source (which releases the device).
pub fn start_mic_test_with<F, L>(
    state: &Shared,
    open: F,
    duration: Duration,
    on_level: L,
) -> Result<(), String>
where
    F: FnOnce() -> Result<Box<dyn Source>, String> + Send + 'static,
    L: Fn(f32) + Send + 'static,
{
    {
        let mut s = state.lock().unwrap_or_else(|e| e.into_inner());
        if let Some(why) = refuse_reason(false, false, s.running) {
            return Err(why.into());
        }
        *s = State { running: true, ..State::default() };
    }
    let shared = state.clone();
    let spawned = std::thread::Builder::new().name("mic-test".into()).spawn(move || {
        let _release = RunGuard(shared.clone());
        match open() {
            Err(e) => {
                let mut s = shared.lock().unwrap_or_else(|e| e.into_inner());
                s.running = false;
                s.error = e;
            }
            Ok(mut source) => {
                shared.lock().unwrap_or_else(|e| e.into_inner()).device = source.device();
                let began = Instant::now();
                while began.elapsed() < duration {
                    let level = peak_of(&source.read());
                    on_level(level);
                    let mut s = shared.lock().unwrap_or_else(|e| e.into_inner());
                    s.peak = s.peak.max(level);
                    drop(s);
                    std::thread::sleep(Duration::from_millis(20));
                }
                on_level(0.0);
                drop(source);
                shared.lock().unwrap_or_else(|e| e.into_inner()).running = false;
            }
        }
    });
    if let Err(e) = spawned {
        let mut s = state.lock().unwrap_or_else(|e| e.into_inner());
        s.running = false;
        s.error = format!("cannot start the test: {e}");
        return Err(s.error.clone());
    }
    Ok(())
}

/// The two-note test tone at `rate` Hz: about 250 ms a note, 3 ms edge fades,
/// peak 0.22 (never above 0.25: a test must not be a shock).
pub fn tone_samples(rate: f32) -> Vec<f32> {
    crate::cue::render(&[(660.0, 250), (880.0, 250)], rate)
}

/// Test the speaker. The output is resolved HERE, synchronously, so a missing
/// or unresolved device is an error the caller can show at once; only the
/// playing is on a thread. The reply-mute switch is deliberately not consulted:
/// someone who muted replies and presses "Test speaker" wants to hear it.
///
/// Returns the device's name.
pub fn speaker_test_with<D: Send + 'static>(
    resolve: impl FnOnce() -> Result<(D, String), String>,
    play: impl FnOnce(D) + Send + 'static,
) -> Result<String, String> {
    let (device, name) = resolve().map_err(|e| {
        if e.contains("output") { e } else { format!("output device: {e}") }
    })?;
    std::thread::Builder::new()
        .name("speaker-test".into())
        .spawn(move || play(device))
        .map_err(|e| format!("cannot start the output test: {e}"))?;
    Ok(name)
}

/// The shell's speaker test, on the resolved output device.
pub fn start_speaker_test() -> Result<String, String> {
    speaker_test_with(
        || {
            let chosen = crate::devices::resolve_output()?;
            let config = chosen.device.default_output_config().map_err(|e| format!("output device: {e}"))?;
            if config.sample_format() != cpal::SampleFormat::F32 {
                return Err(format!("output device is {:?}, not f32", config.sample_format()));
            }
            Ok(((chosen.device, config), chosen.name))
        },
        |(device, config)| {
            let samples = tone_samples(config.sample_rate().0 as f32);
            if let Err(e) = crate::cue::play_buffer(&device, config, samples) {
                log::warn!("speaker test: {e}");
            }
        },
    )
}

/// The shell's mic test: a fresh `Mic` on the resolved input, 2 s, level bar on.
pub fn start_mic_test() -> Result<(), String> {
    start_mic_test_with(
        &shell_state(),
        || {
            let mic = crate::audio::Mic::open()?;
            let cursor = mic.cursor();
            Ok(Box::new(MicSource { mic, cursor }) as Box<dyn Source>)
        },
        MIC_TEST,
        crate::audio::set_level,
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicU32, Ordering};

    #[test]
    fn the_tone_is_audible_gentle_soft_edged_and_the_right_length() {
        for rate in [44_100.0f32, 48_000.0, 96_000.0] {
            let t = tone_samples(rate);
            let peak = t.iter().fold(0.0f32, |m, s| m.max(s.abs()));
            assert!(t.iter().all(|s| s.is_finite()), "{rate}");
            assert!(peak > 0.1 && peak <= 0.25, "{rate}: peak {peak}");
            assert!(t[0].abs() < 0.001, "{rate}: starts at {}", t[0]);
            assert!(t[t.len() - 1].abs() < 0.01, "{rate}: ends at {}", t[t.len() - 1]);
            let ms = t.len() as f32 / rate * 1000.0;
            assert!((400.0..=800.0).contains(&ms), "{rate}: {ms} ms");
        }
    }

    #[test]
    fn the_tone_is_two_notes_the_second_higher() {
        let t = tone_samples(48_000.0);
        let (a, b) = t.split_at(t.len() / 2);
        let crossings = |s: &[f32]| s.windows(2).filter(|w| w[0] < 0.0 && w[1] >= 0.0).count();
        assert!(crossings(b) > crossings(a), "{} vs {}", crossings(a), crossings(b));
    }

    #[test]
    fn an_unresolved_output_fails_at_once_naming_the_cause_and_plays_nothing() {
        let played = Arc::new(AtomicU32::new(0));
        let seen = played.clone();
        let r = speaker_test_with::<()>(
            || Err("no output device: nothing is set as the default output device".into()),
            move |_| { seen.fetch_add(1, Ordering::SeqCst); },
        );
        assert!(r.unwrap_err().contains("output"));
        // A cause that does not say "output" is still labelled.
        let r = speaker_test_with::<()>(|| Err("denied".into()), |_| {});
        assert_eq!(r.unwrap_err(), "output device: denied");
        std::thread::sleep(Duration::from_millis(50));
        assert_eq!(played.load(Ordering::SeqCst), 0);
    }

    #[test]
    fn the_speaker_test_plays_even_when_replies_are_muted() {
        crate::cue::set_muted(true);
        let (tx, rx) = std::sync::mpsc::channel();
        let name = speaker_test_with(|| Ok((7u8, "Fake Speakers".to_string())), move |d| tx.send(d).unwrap());
        crate::cue::set_muted(false);
        assert_eq!(name.unwrap(), "Fake Speakers");
        assert_eq!(rx.recv_timeout(Duration::from_secs(2)).unwrap(), 7, "the player was not called");
    }

    #[test]
    fn the_speaker_test_returns_while_the_player_is_still_playing() {
        let began = Instant::now();
        let r = speaker_test_with(|| Ok(((), "S".to_string())), |_| std::thread::sleep(Duration::from_millis(300)));
        assert!(r.is_ok());
        assert!(began.elapsed() < Duration::from_millis(100), "{:?}", began.elapsed());
    }

    #[test]
    fn peak_of_covers_the_whole_range() {
        assert_eq!(peak_of(&[]), 0.0);
        assert_eq!(peak_of(&[0, 0, 0]), 0.0);
        assert!(peak_of(&[i16::MAX]) > 0.9999 && peak_of(&[i16::MAX]) <= 1.0);
        assert_eq!(peak_of(&[i16::MIN]), 1.0);
        let tone: Vec<i16> = (0..480)
            .map(|i| ((i as f32 / 480.0 * std::f32::consts::TAU * 4.0).sin() * 16384.0) as i16)
            .collect();
        assert!((peak_of(&tone) - 0.5).abs() < 0.001, "{}", peak_of(&tone));
        for k in (-32768i32..=32767).step_by(257) {
            let p = peak_of(&[k as i16]);
            assert!((0.0..=1.0).contains(&p), "{k} -> {p}");
        }
    }

    #[test]
    fn the_guard_refuses_a_busy_microphone() {
        assert!(refuse_reason(true, false, false).unwrap().contains("take"));
        assert!(refuse_reason(false, true, false).unwrap().contains("hands-free"));
        assert!(refuse_reason(false, false, true).unwrap().contains("already"));
        assert_eq!(refuse_reason(false, false, false), None);
    }

    /// Emits a ramp, then silence.
    struct Ramp(bool);
    impl Source for Ramp {
        fn device(&self) -> String { "Fake Mic".into() }
        fn read(&mut self) -> Vec<i16> {
            if self.0 { return vec![0; 16]; }
            self.0 = true;
            (0..=100).map(|i| (i * 200) as i16).collect()
        }
    }

    fn wait_done(state: &Shared) {
        wait_done_within(state, 5);
    }

    fn wait_done_within(state: &Shared, secs: u64) {
        let end = Instant::now() + Duration::from_secs(secs);
        while running(state) && Instant::now() < end {
            std::thread::sleep(Duration::from_millis(5));
        }
        assert!(!running(state), "the test thread did not finish");
    }

    #[test]
    fn the_reported_peak_is_the_sources_peak_and_it_stops_running() {
        let state = Shared::default();
        let last = Arc::new(AtomicU32::new(999));
        let seen = last.clone();
        start_mic_test_with(&state, || Ok(Box::new(Ramp(false))), Duration::from_millis(120),
            move |l| seen.store((l * 1000.0) as u32, Ordering::SeqCst)).unwrap();
        wait_done(&state);
        let v = state_json(&state);
        let want = peak_of(&[(100 * 200) as i16]);
        assert!((v["peak"].as_f64().unwrap() as f32 - want).abs() < 1e-6, "{v}");
        assert_eq!(v["running"], false);
        assert_eq!(v["device"], "Fake Mic");
        assert_eq!(last.load(Ordering::SeqCst), 0, "the bar is released at the end");
    }

    #[test]
    fn starting_returns_at_once_while_the_source_blocks() {
        struct Slow;
        impl Source for Slow {
            fn device(&self) -> String { "Slow".into() }
            fn read(&mut self) -> Vec<i16> { std::thread::sleep(Duration::from_millis(300)); vec![] }
        }
        let state = Shared::default();
        let began = Instant::now();
        start_mic_test_with(&state, || Ok(Box::new(Slow)), Duration::from_millis(50), |_| {}).unwrap();
        assert!(began.elapsed() < Duration::from_millis(50), "{:?}", began.elapsed());
        assert!(running(&state));
        // A second start while one runs is refused.
        let again = start_mic_test_with(&state, || Ok(Box::new(Slow)), Duration::from_millis(50), |_| {});
        assert!(again.unwrap_err().contains("already"));
        wait_done(&state);
    }

    #[test]
    fn the_state_has_exactly_three_keys_and_error_only_on_failure() {
        let state = Shared::default();
        let v = state_json(&state);
        let mut keys: Vec<_> = v.as_object().unwrap().keys().cloned().collect();
        keys.sort();
        assert_eq!(keys, ["device", "peak", "running"]);
    }

    #[test]
    fn a_source_that_will_not_open_reports_the_error_without_panicking() {
        let state = Shared::default();
        start_mic_test_with(&state, || Err("cannot open the microphone (denied)".into()),
            Duration::from_millis(50), |_| {}).unwrap();
        wait_done(&state);
        let v = state_json(&state);
        assert!(v["error"].as_str().unwrap().contains("microphone"), "{v}");
        assert_eq!(v["running"], false);
    }

    #[test]
    fn nothing_here_writes_a_file_or_sends_anything() {
        let production = include_str!("voice_test.rs").split("mod tests {").next().unwrap();
        for needle in ["std::fs", "File::", "TcpStream", "console_api", "wav("] {
            assert!(!production.contains(needle), "voice_test.rs uses {needle}");
        }
    }

    /// Hardware-gated: a real two-second test on this machine's microphone.
    #[test]
    fn a_real_microphone_test_reports_a_peak_in_range() {
        if !crate::audio::available() {
            eprintln!("skipped: no input device on this machine");
            return;
        }
        let state = Shared::default();
        let began = Instant::now();
        let started = start_mic_test_with(&state, || {
            let mic = crate::audio::Mic::open()?;
            let cursor = mic.cursor();
            Ok(Box::new(MicSource { mic, cursor }) as Box<dyn Source>)
        }, MIC_TEST, |_| {});
        assert!(started.is_ok());
        // A Bluetooth input can take 2-4 s just to open, on top of the 2 s test.
        wait_done_within(&state, 15);
        let v = state_json(&state);
        if v.get("error").is_some() {
            eprintln!("skipped: the microphone would not open ({})", v["error"]);
            return;
        }
        let p = v["peak"].as_f64().unwrap();
        assert!((0.0..=1.0).contains(&p));
        eprintln!("voice_test: real mic {:?} peak {p:.4} in {:?}", v["device"], began.elapsed());
    }

    // -- a panic must not wedge the test (T-031 FIX-2) ----------------------

    #[test]
    fn a_panicking_source_does_not_leave_the_test_running_forever() {
        struct Boom;
        impl Source for Boom {
            fn device(&self) -> String { "Boom".into() }
            fn read(&mut self) -> Vec<i16> { panic!("the driver blew up") }
        }
        let state = Shared::default();
        start_mic_test_with(&state, || Ok(Box::new(Boom)), Duration::from_millis(50), |_| {}).unwrap();
        wait_done(&state);
        let v = state_json(&state);
        assert_eq!(v["running"], false, "{v}");
        assert!(v["error"].as_str().unwrap_or("").contains("stopped"), "a panic is reported: {v}");
        // Not refused as "already running" afterwards.
        start_mic_test_with(&state, || Ok(Box::new(Ramp(false))), Duration::from_millis(30), |_| {})
            .expect("a later test starts");
        wait_done(&state);
    }

    #[test]
    fn a_panic_while_opening_is_released_too() {
        let state = Shared::default();
        start_mic_test_with(&state, || -> Result<Box<dyn Source>, String> { panic!("open blew up") },
            Duration::from_millis(50), |_| {}).unwrap();
        wait_done(&state);
        assert_eq!(state_json(&state)["running"], false);
    }

    // -- the guard is symmetric (T-031 FIX-1) -------------------------------

    #[test]
    fn waiting_for_an_idle_test_returns_at_once_when_none_runs() {
        let began = Instant::now();
        assert!(wait_idle_with(|| false, Duration::from_secs(3), Duration::from_millis(10)));
        assert!(began.elapsed() < Duration::from_millis(100), "{:?}", began.elapsed());
    }

    #[test]
    fn waiting_for_an_idle_test_sees_it_finish() {
        let polls = std::cell::Cell::new(0);
        let idle = wait_idle_with(
            || { polls.set(polls.get() + 1); polls.get() < 4 },
            Duration::from_secs(3),
            Duration::from_millis(5),
        );
        assert!(idle);
        assert_eq!(polls.get(), 4);
    }

    #[test]
    fn waiting_for_a_test_that_never_ends_gives_up_at_the_bound() {
        let began = Instant::now();
        assert!(!wait_idle_with(|| true, Duration::from_millis(120), Duration::from_millis(10)));
        let took = began.elapsed();
        assert!(took >= Duration::from_millis(120) && took < Duration::from_millis(600), "{took:?}");
    }

    #[test]
    fn the_shell_wait_follows_the_shell_state() {
        // Nothing in the unit tests starts the SHELL's test, so it is idle.
        assert!(!running(&shell_state()));
        assert!(wait_idle(Duration::from_millis(50)));
    }
}

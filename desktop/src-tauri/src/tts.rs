//! Speaking a reply out loud.
//!
//! ## Why a process, not a library
//!
//! Every one of these three platforms ships a speech synthesiser that is
//! already installed, already has voices, and already knows how to reach the
//! audio device: `System.Speech` on Windows, `say` on macOS, `spd-say` or
//! `espeak-ng` on Linux. This module spawns one of those and lets the OS do
//! the work.
//!
//! ## And why there is now a second backend
//!
//! Because the voices did justify it. `System.Speech` reaches only the old
//! "Desktop" voices — Microsoft David and Zira on a typical Windows install —
//! and "it talks like a robot" turned out to be a fair description rather than
//! a figure of speech. So `piper` is preferred when it is installed: a local
//! neural voice, fetched deliberately by `desktop/get-piper.ps1`, with the OS
//! synthesiser as the fallback that always works. This module is the choice
//! between them; `piper.rs` owns the harder half.
//!
//! ## Why the text is passed by stdin on Windows
//!
//! The reply is model output. Interpolating it into a PowerShell command line
//! would make a quote or a `$(...)` in a reply into a code-injection bug, and
//! the reply is the one string in this system most influenced by whatever is
//! on the user's screen. Stdin has no such problem.
//!
//! ## Barge-in
//!
//! `stop()` kills whatever is speaking. That is what makes "interrupt" work
//! while the assistant is mid-sentence, and it is why the child is tracked in
//! a mutex rather than fired and forgotten.

use std::io::Write;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;

pub type TtsResult<T> = Result<T, String>;

/// The utterance in flight, so a later `stop()` can end it.
static SPEAKING: Mutex<Option<Child>> = Mutex::new(None);

fn guard() -> std::sync::MutexGuard<'static, Option<Child>> {
    SPEAKING.lock().unwrap_or_else(|e| e.into_inner())
}

/// Is a synthesiser available on this machine?
pub fn available() -> bool {
    backend().is_some()
}

/// Where the neural voice would be, if it is installed. Set once at startup
/// so `speak()` keeps a signature the bridge can call without carrying a path
/// through every layer that does not care.
static ROOT: Mutex<Option<std::path::PathBuf>> = Mutex::new(None);

/// Voice and speed, read from the console's settings by the caller.
static VOICE: Mutex<String> = Mutex::new(String::new());
static RATE: Mutex<f32> = Mutex::new(1.0);

pub fn configure(repo_root: &std::path::Path, voice: &str, rate: f32) {
    *ROOT.lock().unwrap_or_else(|e| e.into_inner()) = Some(repo_root.to_path_buf());
    *VOICE.lock().unwrap_or_else(|e| e.into_inner()) = voice.to_string();
    *RATE.lock().unwrap_or_else(|e| e.into_inner()) = rate;
}

/// The voice the SETTINGS name, as last applied. Separate from `VOICE`, which a
/// Preview overrides for one utterance: `/health` reports this one.
static CHOSEN: Mutex<String> = Mutex::new(String::new());

pub fn choose(voice: &str) {
    *CHOSEN.lock().unwrap_or_else(|e| e.into_inner()) = voice.to_string();
}

pub fn chosen_voice() -> String {
    CHOSEN.lock().unwrap_or_else(|e| e.into_inner()).clone()
}

/// What `configure` last stored: voice name and speed factor. For tests of the
/// route that calls it.
#[cfg(test)]
pub fn configured() -> (String, f32) {
    (
        VOICE.lock().unwrap_or_else(|e| e.into_inner()).clone(),
        *RATE.lock().unwrap_or_else(|e| e.into_inner()),
    )
}

/// The voice and speed for one `/speak`: what the request names, else what the
/// settings say.
///
/// A non-blank `voice` and a numeric `rate_percent` in the body win, which is
/// how Preview lets you hear a choice before saving it; anything absent comes
/// from `speak_voice` / `speak_rate_percent` (100 when unset). The speed is
/// clamped to 50-200 per cent and returned as the factor `configure` takes.
///
/// Pure, and it stores nothing (BR-13): a preview is not a setting. A voice that
/// is not installed is passed through untouched; falling back to one that is
/// belongs to `piper::voice`, so there is one rule for it.
pub fn speak_params(settings: &serde_json::Value, body: &serde_json::Value) -> (String, f32) {
    let voice = body
        .get("voice")
        .and_then(serde_json::Value::as_str)
        .map(str::trim)
        .filter(|v| !v.is_empty())
        .map(str::to_string)
        .unwrap_or_else(|| crate::console_settings::str_at(settings, "speak_voice", ""));
    let percent = body
        .get("rate_percent")
        .and_then(serde_json::Value::as_f64)
        .unwrap_or_else(|| {
            crate::console_settings::u64_at(settings, "speak_rate_percent", 100) as f64
        });
    (voice, (percent.clamp(50.0, 200.0) / 100.0) as f32)
}

fn root() -> Option<std::path::PathBuf> {
    ROOT.lock().unwrap_or_else(|e| e.into_inner()).clone()
}

/// The name of the backend that would be used, for `/health` and for saying
/// why speech is unavailable.
pub fn backend_name() -> String {
    match backend() {
        Some(Backend::Piper) => "piper".into(),
        Some(Backend::Windows) => "system.speech".into(),
        Some(Backend::Say) => "say".into(),
        Some(Backend::SpdSay) => "spd-say".into(),
        Some(Backend::Espeak) => "espeak-ng".into(),
        None => String::new(),
    }
}

enum Backend {
    /// A local neural voice. Preferred when installed — it is the reason this
    /// module has a choice to make at all.
    Piper,
    /// PowerShell + `System.Speech`. Present on every Windows install.
    Windows,
    /// macOS `say`.
    Say,
    /// Linux speech-dispatcher.
    SpdSay,
    /// Linux fallback.
    Espeak,
}

fn on_path(exe: &str) -> bool {
    std::env::var_os("PATH")
        .map(|paths| {
            std::env::split_paths(&paths).any(|dir| {
                dir.join(exe).is_file()
                    || (cfg!(windows) && dir.join(format!("{exe}.exe")).is_file())
            })
        })
        .unwrap_or(false)
}

fn backend() -> Option<Backend> {
    if let Some(root) = root() {
        if crate::piper::available(&root) {
            return Some(Backend::Piper);
        }
    }
    if cfg!(windows) {
        // Preferred over any of the below on Windows: it needs no install and
        // uses the voice the user already hears from the OS.
        if on_path("powershell") {
            return Some(Backend::Windows);
        }
    }
    if cfg!(target_os = "macos") && on_path("say") {
        return Some(Backend::Say);
    }
    if on_path("spd-say") {
        return Some(Backend::SpdSay);
    }
    if on_path("espeak-ng") {
        return Some(Backend::Espeak);
    }
    None
}

fn hint() -> String {
    if cfg!(windows) {
        "no speech synthesiser: powershell is not on PATH".into()
    } else if cfg!(target_os = "macos") {
        "no speech synthesiser: `say` is not on PATH".into()
    } else {
        "no speech synthesiser: install speech-dispatcher (spd-say) or espeak-ng".into()
    }
}

/// Trim to something worth hearing. Public so the same rule can be tested
/// without a sound card.
pub fn spoken_form(text: &str) -> String {
    crate::speech_text::spoken_form(text)
}

/// Speak `text`, interrupting anything already speaking.
///
/// Returns as soon as the utterance has STARTED, not when it finishes: the
/// caller is a bridge request thread, and holding an HTTP response open for
/// the length of a spoken paragraph would tie the console to the speed of
/// speech.
pub fn speak(text: &str) -> TtsResult<usize> {
    let body = spoken_form(text);
    if body.is_empty() {
        return Ok(0);
    }
    let backend = backend().ok_or_else(hint)?;
    stop();

    if matches!(backend, Backend::Piper) {
        let root = root().ok_or("piper has no repo root")?;
        let voice = VOICE.lock().unwrap_or_else(|e| e.into_inner()).clone();
        let rate = *RATE.lock().unwrap_or_else(|e| e.into_inner());
        crate::piper::speak_voice(&root, &voice, &body, rate)?;
        return Ok(body.chars().count());
    }

    let mut command = match backend {
        // Handled above, before any process is built.
        Backend::Piper => unreachable!("piper speaks through its own path"),
        Backend::Windows => {
            let mut c = Command::new("powershell");
            // The text arrives on stdin, never on the command line - see the
            // module docstring. `-` reads all of stdin before speaking.
            c.args([
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "Add-Type -AssemblyName System.Speech; \
                 $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; \
                 $s.Speak([Console]::In.ReadToEnd())",
            ]);
            c
        }
        Backend::Say => Command::new("say"),
        Backend::SpdSay => {
            let mut c = Command::new("spd-say");
            // Wait so the process lives as long as the speech, which is what
            // makes `stop()` able to cut it off.
            c.arg("--wait");
            c
        }
        Backend::Espeak => Command::new("espeak-ng"),
    };

    command.stdin(Stdio::piped()).stdout(Stdio::null()).stderr(Stdio::null());
    #[cfg(windows)]
    cmd_no_window(&mut command);

    let mut child = command
        .spawn()
        .map_err(|e| format!("cannot start the speech synthesiser: {e}"))?;

    // `say`, `spd-say` and `espeak-ng` all read stdin when given no text
    // argument, so one path feeds them all.
    if let Some(mut stdin) = child.stdin.take() {
        let _ = stdin.write_all(body.as_bytes());
        // Dropping stdin closes it, which is what tells the child to begin.
    }

    let spoken = body.chars().count();
    *guard() = Some(child);
    Ok(spoken)
}

#[cfg(windows)]
fn cmd_no_window(command: &mut Command) {
    use std::os::windows::process::CommandExt;
    command.creation_flags(0x0800_0000); // CREATE_NO_WINDOW
}

/// Stop whatever is speaking. Safe to call when nothing is.
pub fn stop() -> bool {
    // Both, unconditionally: which backend spoke last is not worth tracking
    // when stopping the one that is silent costs nothing.
    let piper_stopped = crate::piper::stop();
    let mut slot = guard();
    if piper_stopped && slot.is_none() {
        return true;
    }
    match slot.take() {
        Some(mut child) => {
            let _ = child.kill();
            let _ = child.wait();
            true
        }
        None => false,
    }
}

/// Has the current utterance finished? Used to drive the tray back out of the
/// speaking state without the caller having to poll a process handle.
pub fn finished() -> bool {
    if !crate::piper::finished() {
        return false;
    }
    let mut slot = guard();
    match slot.as_mut() {
        Some(child) => match child.try_wait() {
            Ok(Some(_)) => {
                *slot = None;
                true
            }
            Ok(None) => false,
            // A handle we cannot query is one we should stop waiting on.
            Err(_) => {
                *slot = None;
                true
            }
        },
        None => true,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_hint_names_something_installable() {
        let h = hint();
        assert!(h.contains("no speech synthesiser"));
        assert!(h.contains("powershell") || h.contains("say") || h.contains("espeak"));
    }

    #[test]
    fn empty_text_speaks_nothing_rather_than_erroring() {
        // A turn that produced no text should not look like a broken
        // synthesiser.
        assert_eq!(speak("   ").unwrap(), 0);
    }

    #[test]
    fn what_gets_spoken_is_shaped_for_speech() {
        // The rules (and their tests) live in `speech_text`; this asserts the
        // wiring, so a future `speak()` that stopped calling it is caught.
        assert_eq!(spoken_form("**Two** tickets, see T-002"),
                   "Two tickets, see T 2.");
    }

    #[test]
    fn stop_is_safe_when_nothing_is_speaking() {
        stop();
        assert!(!stop(), "the second stop has nothing to kill");
        assert!(finished(), "nothing speaking counts as finished");
    }

    /// Real speech, skipped loudly where there is no synthesiser. Kept short
    /// and stopped immediately so a test run does not talk at length.
    #[test]
    fn speaks_and_can_be_interrupted() {
        if !available() {
            eprintln!("skipped: {}", hint());
            return;
        }
        let n = speak("testing one two three four five").expect("a backend is available");
        assert!(n > 0);
        // Barge-in: this is the mechanism that lets "stop" cut off a reply
        // that is being read aloud.
        assert!(stop(), "an utterance in flight should be killable");
        assert!(finished());
        eprintln!("tts: backend={} spoke {} chars then stopped", backend_name(), n);
    }

    // -- per-request voice and speed (T-031 FR-15, AC-47) ------------------

    use serde_json::json;

    fn close(a: f32, b: f32) -> bool {
        (a - b).abs() < 1e-6
    }

    #[test]
    fn a_voice_and_speed_in_the_request_win_over_the_settings() {
        let settings = json!({"speak_voice": "from-settings", "speak_rate_percent": 90});
        let (voice, rate) = speak_params(&settings, &json!({"voice": " en_US-ryan-medium ", "rate_percent": 140}));
        assert_eq!(voice, "en_US-ryan-medium");
        assert!(close(rate, 1.4), "{rate}");
        // Each wins on its own.
        let (voice, rate) = speak_params(&settings, &json!({"voice": "only-voice"}));
        assert_eq!((voice.as_str(), close(rate, 0.9)), ("only-voice", true));
        let (voice, rate) = speak_params(&settings, &json!({"rate_percent": 160}));
        assert_eq!((voice.as_str(), close(rate, 1.6)), ("from-settings", true));
    }

    #[test]
    fn what_the_request_leaves_out_comes_from_the_settings() {
        let settings = json!({"speak_voice": " from-settings ", "speak_rate_percent": 75});
        for body in [json!({}), json!({"text": "hi"}), json!({"voice": "   "}), json!({"rate_percent": "fast"})] {
            let (voice, rate) = speak_params(&settings, &body);
            assert_eq!(voice, "from-settings", "{body}");
            assert!(close(rate, 0.75), "{body} -> {rate}");
        }
    }

    #[test]
    fn with_neither_it_is_automatic_at_normal_speed() {
        for settings in [serde_json::Value::Null, json!({})] {
            let (voice, rate) = speak_params(&settings, &json!({}));
            assert_eq!(voice, "");
            assert!(close(rate, 1.0), "{rate}");
        }
    }

    #[test]
    fn the_speed_is_kept_between_half_and_double() {
        for (asked, want) in [(10.0, 0.5), (50.0, 0.5), (100.0, 1.0), (200.0, 2.0), (500.0, 2.0), (-30.0, 0.5)] {
            let (_, rate) = speak_params(&json!({}), &json!({"rate_percent": asked}));
            assert!(close(rate, want), "{asked} -> {rate}");
        }
        // A setting outside the range is held to it too.
        let (_, rate) = speak_params(&json!({"speak_rate_percent": 900}), &json!({}));
        assert!(close(rate, 2.0), "{rate}");
    }

    #[test]
    fn an_unknown_voice_falls_back_exactly_as_the_piper_lookup_does() {
        // Two fake voices on disk: asking for one that is not there is passed
        // through untouched and lands on the first sorted installed voice.
        let root = std::env::temp_dir().join(format!("t031-tts-fallback-{}", std::process::id()));
        let dir = root.join("desktop/tts");
        let _ = std::fs::remove_dir_all(&root);
        std::fs::create_dir_all(&dir).unwrap();
        for name in ["z-last.onnx", "a-first.onnx"] {
            std::fs::write(dir.join(name), b"x").unwrap();
        }

        let (voice, _) = speak_params(&json!({}), &json!({"voice": "not-installed"}));
        assert_eq!(voice, "not-installed", "the lookup, not the resolver, owns the fallback");
        let spoken = crate::piper::voice(&root, &voice).expect("a voice is installed");
        assert_eq!(spoken.file_name().unwrap(), "a-first.onnx");
        assert_eq!(crate::piper::voice_in_use(&root, &voice).as_deref(), Some("a-first"));
        // An installed one is used as named.
        let (voice, _) = speak_params(&json!({}), &json!({"voice": "z-last"}));
        assert_eq!(crate::piper::voice(&root, &voice).unwrap().file_name().unwrap(), "z-last.onnx");
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn resolving_the_parameters_saves_nothing() {
        // BR-13: a preview is not a setting. `speak_params` has no way to
        // store anything; this pins it against `configure` creeping in.
        let production = include_str!("tts.rs").split("mod tests {").next().unwrap();
        let body = production
            .split("pub fn speak_params")
            .nth(1)
            .and_then(|rest| rest.split("\nfn root()").next())
            .expect("speak_params is in the file");
        for storing in ["configure(", "VOICE", "RATE", ".lock()"] {
            assert!(!body.contains(storing), "speak_params touches {storing}");
        }
    }
}

//! Speaking a reply out loud.
//!
//! ## Why a process, not a library
//!
//! Every one of these three platforms ships a speech synthesiser that is
//! already installed, already has voices, and already knows how to reach the
//! audio device: `System.Speech` on Windows, `say` on macOS, `spd-say` or
//! `espeak-ng` on Linux. Going through WinRT's `SpeechSynthesis` instead would
//! mean owning WAV decoding and an output stream to gain better voices — and
//! after T-005, adding more WinRT to this binary is a cost worth avoiding
//! unless something demands it.
//!
//! So this module spawns a process and lets the OS do the work. The whole
//! backend is swappable behind `speak()` if the voices ever justify it.
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

/// Cap on what will be spoken in one go. A model can produce pages; reading
/// pages aloud is not a feature, it is a hostage situation. The console
/// already trims to its own `reply_chars`, and this is the backstop.
const MAX_CHARS: usize = 2000;

fn guard() -> std::sync::MutexGuard<'static, Option<Child>> {
    SPEAKING.lock().unwrap_or_else(|e| e.into_inner())
}

/// Is a synthesiser available on this machine?
pub fn available() -> bool {
    backend().is_some()
}

/// The name of the backend that would be used, for `/health` and for saying
/// why speech is unavailable.
pub fn backend_name() -> String {
    match backend() {
        Some(Backend::Windows) => "system.speech".into(),
        Some(Backend::Say) => "say".into(),
        Some(Backend::SpdSay) => "spd-say".into(),
        Some(Backend::Espeak) => "espeak-ng".into(),
        None => String::new(),
    }
}

enum Backend {
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
    let trimmed = text.trim();
    if trimmed.chars().count() <= MAX_CHARS {
        return trimmed.to_string();
    }
    let cut: String = trimmed.chars().take(MAX_CHARS).collect();
    // Break at a sentence end if there is one nearby, so it does not stop
    // mid-word.
    match cut.rfind(['.', '!', '?']) {
        Some(idx) if idx > MAX_CHARS / 2 => cut[..=idx].to_string(),
        _ => cut,
    }
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

    let mut command = match backend {
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
    let mut slot = guard();
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
    fn a_long_reply_is_trimmed_at_a_sentence_end() {
        let long = format!("{}. and then more text that runs past the cap", "x".repeat(1990));
        let out = spoken_form(&long);
        assert!(out.chars().count() <= MAX_CHARS);
        assert!(out.ends_with('.'), "trimmed mid-word: {:?}", &out[out.len().saturating_sub(30)..]);
    }

    #[test]
    fn a_long_reply_with_no_sentence_end_is_still_capped() {
        let out = spoken_form(&"y".repeat(5000));
        assert_eq!(out.chars().count(), MAX_CHARS);
    }

    #[test]
    fn short_text_is_passed_through_trimmed() {
        assert_eq!(spoken_form("  pong  "), "pong");
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
}

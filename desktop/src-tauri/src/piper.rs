//! A neural voice, running on this machine.
//!
//! ## Why not the OS synthesiser
//!
//! Because of what it actually sounds like. Windows' `System.Speech` reaches
//! only the old "Desktop" voices — on the machine this was written on, that is
//! Microsoft David and Zira, and "it talks like a robot" is a fair description
//! of both. Piper is a small neural synthesiser: ~60 MB per voice, real-time
//! on a CPU, offline, and close enough to a person that you stop noticing.
//!
//! Same bargain as whisper.cpp for listening, and the same rules: fetched
//! deliberately by `desktop/get-piper.ps1`, never downloaded behind your back,
//! and absent means the OS voice still works rather than speech breaking.
//!
//! ## Why the audio is played here rather than by a player
//!
//! `piper --output_raw` writes headerless 16-bit mono PCM to stdout as it
//! synthesises. Writing that to a temp file and handing it to a player would
//! add a round trip to disk, a spawn, and a wait — for a two-second reply,
//! most of the latency. Feeding it to the output device as it arrives means
//! the voice starts while the rest is still being generated, and `stop()`
//! kills it mid-word, which is what makes barge-in feel immediate.
//!
//! ## Why the resampler is six lines
//!
//! A voice model runs at its own rate (22.05 kHz for the medium voices) and
//! the output device runs at whatever it runs at, usually 48 kHz. Linear
//! interpolation between two samples is inaudible on speech and is the whole
//! of the mismatch; a resampling crate would be a dependency to carry for a
//! problem this size. The same argument, and the same six lines, as the
//! capture side in `audio.rs`.

use std::collections::VecDeque;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};

use cpal::traits::{DeviceTrait, StreamTrait};

/// Where `get-piper.ps1` puts the binary and its voices.
const TTS_DIR: &str = "desktop/tts";

/// Fallback if a voice ships without a readable config. Every `medium` voice
/// is 22.05 kHz, so being wrong here is a wrong-pitch bug, not a silent one.
const DEFAULT_HZ: u32 = 22_050;

/// True while a Piper utterance is being played.
static PLAYING: AtomicBool = AtomicBool::new(false);

/// Asks the playback thread to stop. Separate from killing the child: the
/// child can be gone while a second of audio is still queued.
static CANCEL: AtomicBool = AtomicBool::new(false);

/// The synthesiser process, so `stop()` can end it mid-sentence.
static CHILD: Mutex<Option<Child>> = Mutex::new(None);

pub fn exe(repo_root: &Path) -> Option<PathBuf> {
    let name = if cfg!(windows) { "piper.exe" } else { "piper" };
    let path = repo_root.join(TTS_DIR).join(name);
    path.is_file().then_some(path)
}

/// The voice to use: the named one if it is here, else any installed voice.
///
/// Falling back rather than failing, because a name that does not match what
/// was downloaded is a settings typo, and losing the good voice over a typo is
/// a worse outcome than using the one that is actually present.
pub fn voice(repo_root: &Path, wanted: &str) -> Option<PathBuf> {
    let (path, fell_back) = resolve_voice(repo_root, wanted)?;
    if fell_back {
        log::warn!(
            "piper: voice {:?} is not in {TTS_DIR}; using {}",
            wanted.trim(),
            path.file_name().unwrap_or_default().to_string_lossy()
        );
    }
    Some(path)
}

/// A voice NAME: letters, digits, `.`, `_`, `-` and nothing else (the rule
/// `console/server/voice_assets.py` applies, `^[A-Za-z0-9._-]+$`). No
/// separator, drive colon, space or NUL, so a name can never be a path.
fn is_safe_voice_name(name: &str) -> bool {
    !name.is_empty()
        && name.chars().all(|c| c.is_ascii_alphanumeric() || matches!(c, '.' | '_' | '-'))
}

/// The voice `wanted` resolves to, and whether that was a fallback. No side
/// effects: `voice` is the one that speaks up about a fallback, and the caps
/// ask this on every poll.
fn resolve_voice(repo_root: &Path, wanted: &str) -> Option<(PathBuf, bool)> {
    let dir = repo_root.join(TTS_DIR);
    let wanted = wanted.trim();
    // Only a safe NAME is looked up. Anything else (a path, a drive, a space)
    // is treated as a voice that is not installed: it falls back like a typo.
    if is_safe_voice_name(wanted) {
        let named = dir.join(format!("{wanted}.onnx"));
        if named.is_file() {
            return Some((named, false));
        }
    }
    let mut found: Vec<PathBuf> = std::fs::read_dir(&dir)
        .ok()?
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| p.extension().map(|x| x == "onnx").unwrap_or(false))
        .collect();
    found.sort();
    // Blank is "automatic", not a typo: only a NAME that is missing is a fallback.
    found.into_iter().next().map(|first| (first, !wanted.is_empty()))
}

/// The name of the voice that would speak for `wanted` (`en_US-amy-medium`), or
/// `None` when no voice is installed. Never logs, so `/health` can ask it on
/// every poll without repeating the fallback warning.
pub fn voice_in_use(repo_root: &Path, wanted: &str) -> Option<String> {
    let (path, _) = resolve_voice(repo_root, wanted)?;
    path.file_stem().and_then(|s| s.to_str()).map(str::to_string)
}

/// Every voice installed, for the Settings picker.
pub fn voices(repo_root: &Path) -> Vec<String> {
    let dir = repo_root.join(TTS_DIR);
    let mut out: Vec<String> = std::fs::read_dir(&dir)
        .into_iter()
        .flatten()
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| p.extension().map(|x| x == "onnx").unwrap_or(false))
        .filter_map(|p| {
            p.file_stem()
                .and_then(|s| s.to_str())
                .map(|s| s.to_string())
        })
        .collect();
    out.sort();
    out
}

/// Is a neural voice available at all?
pub fn available(repo_root: &Path) -> bool {
    exe(repo_root).is_some() && voice(repo_root, "").is_some()
}

/// The sample rate this voice was trained at, from its config.
fn sample_rate(model: &Path) -> u32 {
    let config = model.with_extension("onnx.json");
    let Ok(text) = std::fs::read_to_string(&config) else {
        return DEFAULT_HZ;
    };
    serde_json::from_str::<serde_json::Value>(&text)
        .ok()
        .and_then(|v| v.get("audio")?.get("sample_rate")?.as_u64())
        .map(|hz| hz as u32)
        .unwrap_or(DEFAULT_HZ)
}

/// Speak `text` with the named voice, returning once the audio has STARTED.
///
/// The caller is a bridge request thread; holding an HTTP response open for
/// the length of a spoken paragraph would tie the console to the speed of
/// speech.
pub fn speak_voice(
    repo_root: &Path,
    voice_name: &str,
    text: &str,
    rate: f32,
) -> Result<(), String> {
    let exe = exe(repo_root).ok_or("piper is not installed")?;
    let model = voice(repo_root, voice_name).ok_or("no piper voice is installed")?;
    speak_with(&exe, &model, text, rate)
}

fn speak_with(exe: &Path, model: &Path, text: &str, rate: f32) -> Result<(), String> {
    stop();
    CANCEL.store(false, Ordering::SeqCst);

    let hz = sample_rate(model);
    // Piper's `length_scale` is duration, so it runs the other way from a
    // speed: 0.5 is twice as long, not twice as fast. Inverting here keeps the
    // setting the thing a person means by "rate".
    let length_scale = 1.0 / rate.clamp(0.5, 2.0);

    let mut command = Command::new(exe);
    command
        .arg("--model")
        .arg(model)
        .arg("--length_scale")
        .arg(format!("{length_scale:.3}"))
        .arg("--output_raw")
        .current_dir(exe.parent().unwrap_or(Path::new(".")))
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x0800_0000); // CREATE_NO_WINDOW
    }

    let mut child = command
        .spawn()
        .map_err(|e| format!("cannot start piper: {e}"))?;

    // The text goes in on stdin, never on the command line: a reply is model
    // output, and it is the string in this system most influenced by whatever
    // is on screen. Same reasoning as the OS backend's.
    if let Some(mut stdin) = child.stdin.take() {
        let line = text.replace(['\r', '\n'], " ");
        let _ = stdin.write_all(line.as_bytes());
        let _ = stdin.write_all(b"\n");
        // Dropping it closes the pipe, which is what tells piper to begin.
    }

    let stdout = child.stdout.take().ok_or("piper gave no output stream")?;
    *CHILD.lock().unwrap_or_else(|e| e.into_inner()) = Some(child);

    let samples: Arc<Mutex<VecDeque<i16>>> = Arc::new(Mutex::new(VecDeque::new()));
    let done = Arc::new(AtomicBool::new(false));

    // Reader: raw PCM off the pipe and into the queue.
    {
        let samples = samples.clone();
        let done = done.clone();
        let _ = std::thread::Builder::new()
            .name("piper-read".into())
            .spawn(move || {
                let mut stdout = stdout;
                let mut buf = [0u8; 4096];
                loop {
                    match stdout.read(&mut buf) {
                        Ok(0) | Err(_) => break,
                        Ok(n) => {
                            let mut queue = samples.lock().unwrap_or_else(|e| e.into_inner());
                            for pair in buf[..n].chunks_exact(2) {
                                queue.push_back(i16::from_le_bytes([pair[0], pair[1]]));
                            }
                        }
                    }
                    if CANCEL.load(Ordering::SeqCst) {
                        break;
                    }
                }
                done.store(true, Ordering::SeqCst);
            });
    }

    // Playback: owns the stream, because a cpal stream is not `Send`.
    PLAYING.store(true, Ordering::SeqCst);
    let started = std::thread::Builder::new()
        .name("piper-play".into())
        .spawn(move || {
            if let Err(e) = play(samples, done, hz) {
                log::warn!("piper: {e}");
            }
            PLAYING.store(false, Ordering::SeqCst);
        });
    if started.is_err() {
        PLAYING.store(false, Ordering::SeqCst);
        stop();
        return Err("cannot start playback".into());
    }
    Ok(())
}

fn play(
    samples: Arc<Mutex<VecDeque<i16>>>,
    done: Arc<AtomicBool>,
    source_hz: u32,
) -> Result<(), String> {
    // The device the output setting names, else the system default.
    let chosen = crate::devices::resolve_output()?;
    log::debug!("piper: playing on {:?}", chosen.name);
    let device = chosen.device;
    let config = device.default_output_config().map_err(|e| e.to_string())?;
    if config.sample_format() != cpal::SampleFormat::F32 {
        return Err(format!("output is {:?}, not f32", config.sample_format()));
    }
    let device_hz = config.sample_rate().0 as f64;
    let channels = config.channels() as usize;
    let step = source_hz as f64 / device_hz;

    let feed = samples.clone();
    // Fractional read position, kept across callbacks — this IS the resampler.
    let mut position = 0.0f64;
    let mut last = 0.0f32;

    let stream = device
        .build_output_stream(
            &config.into(),
            move |out: &mut [f32], _: &cpal::OutputCallbackInfo| {
                let mut queue = feed.lock().unwrap_or_else(|e| e.into_inner());
                for frame in out.chunks_mut(channels) {
                    while position >= 1.0 {
                        if let Some(sample) = queue.pop_front() {
                            last = sample as f32 / i16::MAX as f32;
                        }
                        position -= 1.0;
                    }
                    let next = queue
                        .front()
                        .map(|s| *s as f32 / i16::MAX as f32)
                        .unwrap_or(last);
                    // Between the two samples we are sitting between.
                    let value = last + (next - last) * position as f32;
                    for slot in frame.iter_mut() {
                        *slot = value;
                    }
                    position += step;
                }
            },
            |e| log::debug!("piper: output error: {e}"),
            None,
        )
        .map_err(|e| e.to_string())?;
    stream.play().map_err(|e| e.to_string())?;

    // Hold the stream until the synthesiser has finished AND the queue has
    // drained. Polling rather than a condvar: this thread has nothing else to
    // do, and a 30ms tick costs nothing next to speech.
    loop {
        if CANCEL.load(Ordering::SeqCst) {
            break;
        }
        let empty = samples
            .lock()
            .map(|q| q.is_empty())
            .unwrap_or(true);
        if done.load(Ordering::SeqCst) && empty {
            // A last tick so the tail of the buffer actually reaches the
            // speaker before the stream is dropped.
            std::thread::sleep(std::time::Duration::from_millis(120));
            break;
        }
        std::thread::sleep(std::time::Duration::from_millis(30));
    }
    Ok(())
}

/// Stop mid-word. Safe to call when nothing is speaking.
pub fn stop() -> bool {
    CANCEL.store(true, Ordering::SeqCst);
    let was = PLAYING.swap(false, Ordering::SeqCst);
    let mut slot = CHILD.lock().unwrap_or_else(|e| e.into_inner());
    if let Some(mut child) = slot.take() {
        let _ = child.kill();
        let _ = child.wait();
        return true;
    }
    was
}

/// Has the utterance finished?
pub fn finished() -> bool {
    !PLAYING.load(Ordering::SeqCst)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_missing_install_is_absent_not_an_error() {
        let root = std::path::Path::new("Z:/definitely/not/here");
        assert!(!available(root));
        assert!(exe(root).is_none());
        assert!(voices(root).is_empty());
    }

    #[test]
    fn stopping_when_nothing_speaks_is_harmless() {
        stop();
        assert!(finished());
    }

    #[test]
    fn a_voice_config_gives_its_sample_rate() {
        let dir = std::env::temp_dir().join("piper-rate-test");
        let _ = std::fs::create_dir_all(&dir);
        let model = dir.join("v.onnx");
        std::fs::write(&model, b"not a real model").unwrap();
        std::fs::write(model.with_extension("onnx.json"),
                       br#"{"audio": {"sample_rate": 16000}}"#).unwrap();
        assert_eq!(sample_rate(&model), 16_000);
    }

    #[test]
    fn a_voice_with_no_config_falls_back_rather_than_failing() {
        // Wrong here is a wrong-PITCH bug, which is audible; silent failure
        // would not be.
        let dir = std::env::temp_dir().join("piper-rate-missing");
        let _ = std::fs::create_dir_all(&dir);
        let model = dir.join("v.onnx");
        std::fs::write(&model, b"x").unwrap();
        let _ = std::fs::remove_file(model.with_extension("onnx.json"));
        assert_eq!(sample_rate(&model), DEFAULT_HZ);
    }

    // -- which voice speaks (T-031 FR-15, AC-2, AC-47) ---------------------

    /// A repo-shaped temp root whose `desktop/tts` holds these fake voices.
    fn root_with(tag: &str, voices: &[&str]) -> PathBuf {
        let root = std::env::temp_dir().join(format!("t031-piper-{tag}-{}", std::process::id()));
        let dir = root.join(TTS_DIR);
        let _ = std::fs::remove_dir_all(&root);
        std::fs::create_dir_all(&dir).unwrap();
        for v in voices {
            std::fs::write(dir.join(format!("{v}.onnx")), b"x").unwrap();
        }
        root
    }

    #[test]
    fn a_named_voice_is_used_and_anything_else_is_the_first_sorted() {
        let root = root_with("pick", &["b-voice", "a-voice", "c-voice"]);
        assert_eq!(voice_in_use(&root, "b-voice").as_deref(), Some("b-voice"));
        assert_eq!(voice_in_use(&root, "  c-voice ").as_deref(), Some("c-voice"));
        // Absent, blank and whitespace all fall to the first sorted voice.
        for wanted in ["nope", "", "   "] {
            assert_eq!(voice_in_use(&root, wanted).as_deref(), Some("a-voice"), "{wanted:?}");
        }
        // And `voice` (what actually speaks) agrees with it every time.
        for wanted in ["b-voice", "nope", "", "c-voice"] {
            let spoken = voice(&root, wanted).expect("a voice is installed");
            let stem = spoken.file_stem().unwrap().to_string_lossy().into_owned();
            assert_eq!(Some(stem), voice_in_use(&root, wanted), "{wanted:?}");
        }
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn no_voice_installed_is_none_for_both() {
        let root = root_with("none", &[]);
        assert_eq!(voice_in_use(&root, "anything"), None);
        assert!(voice(&root, "anything").is_none());
        // No directory at all is the same answer.
        let absent = std::env::temp_dir().join("t031-piper-no-such-root");
        assert_eq!(voice_in_use(&absent, ""), None);
        let _ = std::fs::remove_dir_all(&root);
    }

    /// Every warning-level record, in memory. The test binary has no logger of
    /// its own (the shell installs one in `main`), so this installs one.
    struct Capture;
    static LOGGED: Mutex<Vec<String>> = Mutex::new(Vec::new());

    impl log::Log for Capture {
        fn enabled(&self, _: &log::Metadata) -> bool {
            true
        }
        fn log(&self, record: &log::Record) {
            LOGGED.lock().unwrap_or_else(|e| e.into_inner()).push(record.args().to_string());
        }
        fn flush(&self) {}
    }

    fn mentions(marker: &str) -> usize {
        LOGGED.lock().unwrap_or_else(|e| e.into_inner()).iter().filter(|l| l.contains(marker)).count()
    }

    #[test]
    fn asking_which_voice_is_in_use_never_logs_the_fallback() {
        static ONCE: std::sync::Once = std::sync::Once::new();
        ONCE.call_once(|| {
            let _ = log::set_logger(&Capture);
            log::set_max_level(log::LevelFilter::Warn);
        });
        let root = root_with("log", &["a-voice"]);
        // A name nothing else uses, so the parallel tests' own lines cannot be
        // mistaken for ours.
        let missing = format!("t031-missing-voice-{}", std::process::id());

        for _ in 0..5 {
            assert_eq!(voice_in_use(&root, &missing).as_deref(), Some("a-voice"));
        }
        assert_eq!(mentions(&missing), 0, "a poll must not repeat the warning");

        // The control: the speaking path does warn, so the zero above means
        // something (the capture works and the fallback is a warning).
        assert!(voice(&root, &missing).is_some());
        assert_eq!(mentions(&missing), 1, "voice() warns once per fallback");
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn a_voice_is_two_files_named_after_it() {
        // The console's downloader writes `{voice}.onnx` and `{voice}.onnx.json`
        // (`console/server/voice_assets.py`); this side reads exactly those.
        let root = root_with("contract", &["en_US-test-medium"]);
        let config = root.join(TTS_DIR).join("en_US-test-medium.onnx.json");
        std::fs::write(&config, br#"{"audio": {"sample_rate": 16000}}"#).unwrap();

        let model = voice(&root, "en_US-test-medium").expect("found by its name");
        assert_eq!(model.file_name().unwrap(), "en_US-test-medium.onnx");
        assert_eq!(sample_rate(&model), 16_000, "the config is {{voice}}.onnx.json");
        // The config is not a voice of its own.
        assert_eq!(voices(&root), vec!["en_US-test-medium".to_string()]);
        let _ = std::fs::remove_dir_all(&root);
    }

    // -- a voice name is a name, never a path (T-031 FIX-3) -----------------

    #[test]
    fn a_voice_name_that_is_a_path_is_an_unknown_voice_and_never_leaves_the_directory() {
        let root = root_with("traverse", &["a-voice", "b-voice"]);
        let dir = root.join(TTS_DIR);
        // Reachable by `..\evil` / `../evil` from desktop/tts, and by its absolute path.
        std::fs::write(root.join("desktop").join("evil.onnx"), b"x").unwrap();
        let outside = std::env::temp_dir().join(format!("t031-piper-outside-{}", std::process::id()));
        std::fs::create_dir_all(&outside).unwrap();
        std::fs::write(outside.join("evil2.onnx"), b"x").unwrap();
        let absolute = outside.join("evil2").to_string_lossy().into_owned();

        let hostile = [
            "..\\evil".to_string(),
            "../evil".to_string(),
            "..\\..\\evil".to_string(),
            "C:\\x\\y".to_string(),
            "/abs/x".to_string(),
            absolute.clone(),
            absolute.replace('\\', "/"),
            "sub/dir".to_string(),
            "with space".to_string(),
            "nul\0byte".to_string(),
            "a-voice\0".to_string(),
            "C:evil".to_string(),
        ];
        for wanted in &hostile {
            assert_eq!(voice_in_use(&root, wanted).as_deref(), Some("a-voice"), "{wanted:?}");
            let spoken = voice(&root, wanted).expect("a voice is installed");
            assert_eq!(spoken.parent().unwrap(), dir, "{wanted:?} escaped to {spoken:?}");
        }
        let _ = std::fs::remove_dir_all(&root);
        let _ = std::fs::remove_dir_all(&outside);
    }

    #[test]
    fn an_empty_name_is_automatic_and_a_dotted_hyphenated_name_still_resolves() {
        let long = "en_GB-northern_english_male-medium";
        let root = root_with("names", &["a-voice", long, "v1.2_x-y"]);
        assert_eq!(voice_in_use(&root, "").as_deref(), Some("a-voice"));
        assert_eq!(voice_in_use(&root, long).as_deref(), Some(long));
        assert_eq!(voice_in_use(&root, " v1.2_x-y ").as_deref(), Some("v1.2_x-y"));
        let spoken = voice(&root, long).unwrap();
        assert_eq!(spoken, root.join(TTS_DIR).join(format!("{long}.onnx")));
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn the_safe_name_rule_is_the_pythons() {
        for ok in ["a", "en_US-amy-medium", "v1.2_x-y", "A9"] {
            assert!(is_safe_voice_name(ok), "{ok:?}");
        }
        for bad in ["", "a b", "a/b", "a\\b", "C:x", "a\0", "é", "a\n"] {
            assert!(!is_safe_voice_name(bad), "{bad:?}");
        }
    }
}

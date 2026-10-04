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

use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};

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
    let dir = repo_root.join(TTS_DIR);
    let wanted = wanted.trim();
    if !wanted.is_empty() {
        let named = dir.join(format!("{wanted}.onnx"));
        if named.is_file() {
            return Some(named);
        }
    }
    let mut found: Vec<PathBuf> = std::fs::read_dir(&dir)
        .ok()?
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| p.extension().map(|x| x == "onnx").unwrap_or(false))
        .collect();
    found.sort();
    let first = found.into_iter().next();
    if let (false, Some(path)) = (wanted.is_empty(), first.as_ref()) {
        log::warn!(
            "piper: voice {wanted:?} is not in {TTS_DIR}; using {}",
            path.file_name().unwrap_or_default().to_string_lossy()
        );
    }
    first
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
    let host = cpal::default_host();
    let device = host.default_output_device().ok_or("no output device")?;
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
}

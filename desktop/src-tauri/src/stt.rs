//! Turning a take of audio into text.
//!
//! ## Why a local server process
//!
//! `whisper.cpp` ships a prebuilt `whisper-server` that speaks HTTP. Using it
//! means no C toolchain in this build (binding the library needs CMake and
//! LLVM, neither of which is installed here), no model loading code of our
//! own, and — the part that matters in use — the model stays loaded between
//! takes. Loading a 150 MB model per utterance would add seconds to every
//! command.
//!
//! So: spawn it once on first listen, keep it warm, kill it when the shell
//! exits or after a long idle.
//!
//! ## Why nothing is downloaded from here
//!
//! The engine and model are fetched by `desktop/get-whisper.ps1`, which a
//! person runs deliberately. If they are absent, this reports that with the
//! command to fix it, and the tray shows listening as unavailable. A feature
//! that silently pulls 150 MB the first time you click a tray icon is not a
//! feature.
//!
//! ## Why the HTTP is hand-written
//!
//! One multipart POST to `127.0.0.1`. The same reasoning as `tray_link`: an
//! HTTP client crate would bring a TLS stack and an async runtime to a binary
//! that needs neither, and multipart is a boundary string and two headers.

use std::io::{BufRead, BufReader, Read, Write};
use std::net::TcpStream;
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::{Duration, Instant};

pub type SttResult<T> = Result<T, String>;

/// Where `get-whisper.ps1` puts things, relative to the repo root.
const STT_DIR: &str = "desktop/stt";

/// How long to wait for the server to come up. Loading a base model takes
/// well under this; a cap stops a broken binary hanging the first listen.
const START_TIMEOUT: Duration = Duration::from_secs(30);

/// Transcription of a short take is fast, but a cap keeps a wedged engine
/// from holding a listen open forever.
const INFER_TIMEOUT: Duration = Duration::from_secs(60);

struct Engine {
    child: Child,
    port: u16,
    model: String,
    started: Instant,
}

static ENGINE: Mutex<Option<Engine>> = Mutex::new(None);

fn guard() -> std::sync::MutexGuard<'static, Option<Engine>> {
    ENGINE.lock().unwrap_or_else(|e| e.into_inner())
}

fn exe_name(stem: &str) -> String {
    if cfg!(windows) {
        format!("{stem}.exe")
    } else {
        stem.to_string()
    }
}

/// The server binary: bundled first, then PATH.
fn server_binary(repo_root: &std::path::Path) -> Option<PathBuf> {
    let bundled = repo_root.join(STT_DIR).join(exe_name("whisper-server"));
    if bundled.is_file() {
        return Some(bundled);
    }
    std::env::var_os("PATH").and_then(|paths| {
        std::env::split_paths(&paths)
            .map(|dir| dir.join(exe_name("whisper-server")))
            .find(|p| p.is_file())
    })
}

/// Which model to load, by name (`base.en`, `tiny.en`, ...).
///
/// Set from the settings, because "smallest first" alone made the choice
/// implicit and reversible by a download: dropping `tiny.en` beside
/// `base.en` silently switched every future transcript to the faster, less
/// accurate model. A named preference makes the trade a decision.
static PREFERRED: Mutex<String> = Mutex::new(String::new());

pub fn prefer_model(name: &str) {
    let mut slot = PREFERRED.lock().unwrap_or_else(|e| e.into_inner());
    if *slot != name {
        *slot = name.to_string();
    }
}

/// The named model if it is installed; otherwise any ggml in the directory,
/// smallest first, so a machine with only one still works and a machine
/// missing the named one says which it fell back to.
fn model_file(repo_root: &std::path::Path) -> Option<PathBuf> {
    let wanted = PREFERRED.lock().unwrap_or_else(|e| e.into_inner()).clone();
    let wanted = wanted.trim().to_string();
    if !wanted.is_empty() {
        let named = repo_root.join(STT_DIR).join(format!("ggml-{wanted}.bin"));
        if named.is_file() {
            return Some(named);
        }
    }
    let fallback = smallest_model(repo_root);
    if !wanted.is_empty() {
        if let Some(path) = fallback.as_ref() {
            log::warn!(
                "stt: ggml-{wanted}.bin is not in {STT_DIR}; using {} instead",
                path.file_name().unwrap_or_default().to_string_lossy()
            );
        }
    }
    fallback
}

fn smallest_model(repo_root: &std::path::Path) -> Option<PathBuf> {
    let dir = repo_root.join(STT_DIR);
    let mut found: Vec<(u64, PathBuf)> = std::fs::read_dir(&dir)
        .ok()?
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| {
            p.extension().map(|x| x == "bin").unwrap_or(false)
                && p.file_name()
                    .and_then(|n| n.to_str())
                    .map(|n| n.starts_with("ggml-"))
                    .unwrap_or(false)
        })
        .filter_map(|p| std::fs::metadata(&p).ok().map(|m| (m.len(), p)))
        .collect();
    found.sort_by_key(|(len, _)| *len);
    found.into_iter().next().map(|(_, p)| p)
}

/// How many threads to give the decoder: every core, not whisper's default
/// four. Nothing else is running while a take is transcribed, and the user is
/// waiting for it.
fn threads() -> usize {
    std::thread::available_parallelism().map(|n| n.get()).unwrap_or(4)
}

/// Can speech be transcribed on this machine right now?
pub fn available(repo_root: &std::path::Path) -> bool {
    server_binary(repo_root).is_some() && model_file(repo_root).is_some()
}

/// What to tell someone when it is not available. Names the fix, because
/// "unavailable" on its own is not actionable.
pub fn hint(repo_root: &std::path::Path) -> String {
    let has_server = server_binary(repo_root).is_some();
    let has_model = model_file(repo_root).is_some();
    let fetch = if cfg!(windows) {
        "powershell -File desktop/get-whisper.ps1"
    } else {
        "sh desktop/get-whisper.sh"
    };
    match (has_server, has_model) {
        (false, false) => format!("no speech engine or model in {STT_DIR}. Run: {fetch}"),
        (false, true) => format!("the model is there but whisper-server is not. Run: {fetch}"),
        (true, false) => format!("whisper-server is there but no ggml-*.bin model. Run: {fetch}"),
        (true, true) => String::new(),
    }
}

/// The model in use, for `/health` and the Settings display.
pub fn model_name(repo_root: &std::path::Path) -> String {
    model_file(repo_root)
        .and_then(|p| p.file_name().map(|n| n.to_string_lossy().to_string()))
        .unwrap_or_default()
}

/// Ask the OS for a port nobody is using, then let go of it.
///
/// There is a race here in principle — something could take the port between
/// the bind and the server's own bind. On loopback, in the fraction of a
/// millisecond between the two, it has not happened; and the alternative
/// (parsing the port out of the server's log output) couples us to its
/// logging format.
fn free_port() -> SttResult<u16> {
    let listener = std::net::TcpListener::bind("127.0.0.1:0")
        .map_err(|e| format!("cannot find a free port: {e}"))?;
    listener
        .local_addr()
        .map(|a| a.port())
        .map_err(|e| format!("cannot read the port: {e}"))
}

fn responding(port: u16) -> bool {
    TcpStream::connect_timeout(
        &format!("127.0.0.1:{port}").parse().expect("a literal address parses"),
        Duration::from_millis(250),
    )
    .is_ok()
}

/// Start the engine if it is not already up. Returns its port.
fn ensure(repo_root: &std::path::Path) -> SttResult<u16> {
    let mut slot = guard();

    // Already running and still answering?
    if let Some(engine) = slot.as_mut() {
        match engine.child.try_wait() {
            Ok(None) if responding(engine.port) => return Ok(engine.port),
            _ => {
                // Died, or stopped answering. Clear it and start again rather
                // than reporting a failure the user cannot act on.
                let _ = engine.child.kill();
                let _ = engine.child.wait();
                *slot = None;
            }
        }
    }

    let binary = server_binary(repo_root).ok_or_else(|| hint(repo_root))?;
    let model = model_file(repo_root).ok_or_else(|| hint(repo_root))?;
    let port = free_port()?;

    let mut command = Command::new(&binary);
    command
        .arg("-m")
        .arg(&model)
        .arg("--host")
        .arg("127.0.0.1")
        .arg("--port")
        .arg(port.to_string())
        // English only, and no timestamps in the output: this transcribes
        // short commands, not subtitles.
        .arg("-l")
        .arg("en")
        .arg("-nt")
        // Speed, measured rather than assumed: on a fixed WAV these took a
        // 2854ms transcription to 2209ms with a byte-identical transcript.
        // Every one of them trades something this workload does not want:
        //   -t      all the cores, not the default four
        //   -bo 1   one candidate; `best-of 2` decodes twice to pick a
        //           winner, which is for prose, not "open T-002"
        //   -nf     no temperature fallback re-runs on a low-confidence
        //           segment — a command is better re-said than re-decoded
        //   -mc 0   carry no text context between segments. Also stops the
        //           doubled-phrase hallucination seen in T-008's live run
        //   -sns    suppress non-speech tokens, so room noise does not
        //           become "(clears throat)" in the transcript
        .arg("-t")
        .arg(threads().to_string())
        .arg("-bo")
        .arg("1")
        .arg("-nf")
        .arg("-mc")
        .arg("0")
        .arg("-sns")
        // The DLLs sit beside the binary.
        .current_dir(binary.parent().unwrap_or(repo_root))
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x0800_0000); // CREATE_NO_WINDOW
    }

    let child = command
        .spawn()
        .map_err(|e| format!("cannot start {}: {e}", binary.display()))?;

    let waited = Instant::now();
    while waited.elapsed() < START_TIMEOUT {
        if responding(port) {
            log::info!(
                "stt: engine up on {port} with {}",
                model.file_name().unwrap_or_default().to_string_lossy()
            );
            *slot = Some(Engine {
                child,
                port,
                model: model.file_name().unwrap_or_default().to_string_lossy().to_string(),
                started: Instant::now(),
            });
            return Ok(port);
        }
        std::thread::sleep(Duration::from_millis(100));
    }

    let mut child = child;
    let _ = child.kill();
    let _ = child.wait();
    Err(format!(
        "the speech engine did not start within {}s",
        START_TIMEOUT.as_secs()
    ))
}

/// Stop the engine. Called when the shell quits so a 150 MB model is not left
/// resident.
pub fn shutdown() {
    let mut slot = guard();
    if let Some(engine) = slot.take() {
        let mut child = engine.child;
        let _ = child.kill();
        let _ = child.wait();
        log::info!("stt: engine stopped after {:?}", engine.started.elapsed());
    }
}

pub fn running() -> bool {
    let mut slot = guard();
    match slot.as_mut() {
        Some(engine) => matches!(engine.child.try_wait(), Ok(None)),
        None => false,
    }
}

pub fn loaded_model() -> String {
    guard().as_ref().map(|e| e.model.clone()).unwrap_or_default()
}

/// Transcribe a WAV. Blocking; the caller is already on a worker thread.
pub fn transcribe(repo_root: &std::path::Path, wav: &[u8]) -> SttResult<String> {
    // `ensure` may have to START the engine and wait for a 150 MB model to
    // load; inference is a different cost with a different fix, so they are
    // timed apart rather than reported as one number.
    let step = Instant::now();
    let port = ensure(repo_root)?;
    let ensured_ms = step.elapsed().as_millis();
    let inferring = Instant::now();
    let body = multipart(wav);
    let mut stream = TcpStream::connect(("127.0.0.1", port))
        .map_err(|e| format!("cannot reach the speech engine: {e}"))?;
    stream
        .set_read_timeout(Some(INFER_TIMEOUT))
        .map_err(|e| e.to_string())?;

    let head = format!(
        "POST /inference HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n\
         Content-Type: multipart/form-data; boundary={BOUNDARY}\r\n\
         Content-Length: {}\r\nConnection: close\r\n\r\n",
        body.len()
    );
    stream
        .write_all(head.as_bytes())
        .and_then(|()| stream.write_all(&body))
        .map_err(|e| format!("cannot send the audio: {e}"))?;

    let mut reader = BufReader::new(stream);
    let mut status = String::new();
    reader
        .read_line(&mut status)
        .map_err(|e| format!("no answer from the speech engine: {e}"))?;
    if !status.contains(" 200") {
        return Err(format!("the speech engine said {}", status.trim()));
    }
    // Skip headers.
    loop {
        let mut line = String::new();
        reader.read_line(&mut line).map_err(|e| e.to_string())?;
        if line == "\r\n" || line == "\n" || line.is_empty() {
            break;
        }
    }
    let mut payload = String::new();
    reader
        .read_to_string(&mut payload)
        .map_err(|e| format!("cannot read the transcript: {e}"))?;

    log::info!(
        "stt: engine ready in {ensured_ms}ms, inference {}ms",
        inferring.elapsed().as_millis()
    );
    Ok(extract_text(&payload))
}

const BOUNDARY: &str = "----consoleT006boundary";

fn multipart(wav: &[u8]) -> Vec<u8> {
    let mut body = Vec::with_capacity(wav.len() + 512);
    let part = |headers: &str, data: &[u8], out: &mut Vec<u8>| {
        out.extend_from_slice(format!("--{BOUNDARY}\r\n{headers}\r\n\r\n").as_bytes());
        out.extend_from_slice(data);
        out.extend_from_slice(b"\r\n");
    };
    part(
        "Content-Disposition: form-data; name=\"file\"; filename=\"take.wav\"\r\n\
         Content-Type: audio/wav",
        wav,
        &mut body,
    );
    part(
        "Content-Disposition: form-data; name=\"response_format\"",
        b"json",
        &mut body,
    );
    body.extend_from_slice(format!("--{BOUNDARY}--\r\n").as_bytes());
    body
}

/// Pull the transcript out of the engine's answer.
///
/// Tolerant on purpose: `whisper-server` returns `{"text": "..."}` for
/// `response_format=json`, but has returned plain text in other versions, and
/// a transcript is worth having even if the wrapper changed shape.
pub fn extract_text(payload: &str) -> String {
    let body = payload.trim();
    if let Some(start) = body.find("\"text\"") {
        let rest = &body[start + 6..];
        if let Some(open) = rest.find('"') {
            let after = &rest[open + 1..];
            let mut out = String::new();
            let mut chars = after.chars();
            while let Some(c) = chars.next() {
                match c {
                    '\\' => match chars.next() {
                        Some('n') => out.push('\n'),
                        Some('t') => out.push('\t'),
                        Some('"') => out.push('"'),
                        Some('\\') => out.push('\\'),
                        Some(other) => out.push(other),
                        None => break,
                    },
                    '"' => break,
                    other => out.push(other),
                }
            }
            return out.trim().to_string();
        }
    }
    // Not JSON at all: take it as the transcript, minus any chunked-encoding
    // length lines the engine's framing may have left behind.
    body.lines()
        .filter(|l| !l.trim().is_empty() && u64::from_str_radix(l.trim(), 16).is_err())
        .collect::<Vec<_>>()
        .join(" ")
        .trim()
        .to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn repo() -> PathBuf {
        crate::sidecar::find_repo_root().expect("tests run inside the checkout")
    }

    #[test]
    fn the_hint_names_the_command_that_fixes_it() {
        // "Unavailable" alone is not actionable; the message has to say what
        // to run.
        let empty = std::env::temp_dir().join("t006-no-stt-here");
        let h = hint(&empty);
        assert!(h.contains("get-whisper"), "{h}");
    }

    #[test]
    fn availability_and_hint_agree() {
        let root = repo();
        if available(&root) {
            assert_eq!(hint(&root), "", "available means no hint to give");
            assert!(model_name(&root).starts_with("ggml-"), "{}", model_name(&root));
        } else {
            assert!(!hint(&root).is_empty(), "unavailable must explain itself");
        }
    }

    #[test]
    fn a_free_port_is_actually_free() {
        let port = free_port().expect("the OS can spare a port");
        assert!(port > 0);
        assert!(!responding(port), "nothing should be listening there yet");
    }

    #[test]
    fn multipart_carries_the_wav_and_the_format() {
        let body = multipart(b"RIFFfake");
        let text = String::from_utf8_lossy(&body);
        assert!(text.contains("name=\"file\""));
        assert!(text.contains("filename=\"take.wav\""));
        assert!(text.contains("audio/wav"));
        assert!(text.contains("name=\"response_format\""));
        assert!(text.contains("json"));
        assert!(text.ends_with(&format!("--{BOUNDARY}--\r\n")));
        assert!(body.windows(8).any(|w| w == b"RIFFfake"), "the audio survived");
    }

    #[test]
    fn reads_the_transcript_out_of_json() {
        assert_eq!(extract_text(r#"{"text":"status ticket two"}"#), "status ticket two");
        assert_eq!(extract_text(r#"{ "text" : "  padded  " }"#), "padded");
    }

    #[test]
    fn unescapes_what_json_escaped() {
        assert_eq!(extract_text(r#"{"text":"line one\nline two"}"#), "line one\nline two");
        assert_eq!(extract_text(r#"{"text":"he said \"go\""}"#), "he said \"go\"");
    }

    #[test]
    fn a_plain_text_answer_is_still_a_transcript() {
        // Tolerated because a transcript is worth having even if the
        // wrapper's shape changed between engine versions.
        assert_eq!(extract_text("just the words"), "just the words");
    }

    #[test]
    fn chunked_length_lines_are_not_mistaken_for_speech() {
        // Without this, a transcript could come back as "1a status 0".
        assert_eq!(extract_text("1a\nstatus ticket two\n0\n"), "status ticket two");
    }

    /// The whole speech-to-text path, against the real engine: a WAV of
    /// synthesised speech in, the words back out.
    ///
    /// The fixture is committed (`desktop/tests/fixtures/`) and was produced
    /// by the OS synthesiser, so this needs no microphone and no person — and
    /// it is the only test that proves the engine is actually wired up rather
    /// than merely present. Skipped loudly when the engine has not been
    /// fetched.
    #[test]
    fn transcribes_a_spoken_command_from_a_fixture() {
        let root = repo();
        if !available(&root) {
            eprintln!("skipped: {}", hint(&root));
            return;
        }
        let fixture = root.join("desktop/tests/fixtures/status-ticket-two.wav");
        if !fixture.is_file() {
            eprintln!("skipped: no fixture at {}", fixture.display());
            return;
        }
        let wav = std::fs::read(&fixture).expect("the fixture is readable");
        let heard = transcribe(&root, &wav).expect("the engine should transcribe this");
        // Stop the engine before asserting. A test that leaves a 270 MB
        // process holding a loaded model behind it keeps the test harness
        // waiting on exit, which looks exactly like a hang.
        shutdown();
        eprintln!("stt: model={} heard {:?}", model_name(&root), heard);
        let lower = heard.to_lowercase();
        assert!(
            lower.contains("status"),
            "expected the word 'status' in {heard:?}"
        );
        // The ticket id matters more than the exact wording, and the wording
        // is genuinely not "two": base.en transcribes it as the homophone
        // "too". That is why `assistant_commands._DIGIT_HOMOPHONES` exists —
        // this assertion accepts what a speech engine really produces, and
        // the console's own tests prove that resolves to T-002.
        assert!(
            ["two", "too", "to", "2"].iter().any(|w| lower.contains(w)),
            "expected the ticket number, however transcribed, in {heard:?}"
        );
    }

    #[test]
    fn an_empty_answer_is_empty_not_garbage() {
        assert_eq!(extract_text(""), "");
        assert_eq!(extract_text(r#"{"text":""}"#), "");
    }
}

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
//! Models are fetched from Settings (Assistant, Speech models), and on Windows
//! `desktop/get-whisper.ps1` installs the engine too; a person does either
//! deliberately. If they are absent, this reports that with where to fix it
//! (`hint`), and the tray shows listening as unavailable. A feature that
//! silently pulls 150 MB the first time you click a tray icon is not a
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
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use std::sync::{Arc, Condvar, Mutex, OnceLock};
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

/// A process the slot can check on and stop. `Child` in production; a fake in
/// the tests, so the slot's behaviour can be tested without an engine.
trait Proc: Send {
    fn alive(&mut self) -> bool;
    /// Stop it and reap it. Safe to call on one that already exited.
    fn kill(&mut self);
}

impl Proc for Child {
    fn alive(&mut self) -> bool {
        matches!(self.try_wait(), Ok(None))
    }

    fn kill(&mut self) {
        let _ = Child::kill(self);
        let _ = self.wait();
    }
}

/// One engine process, shared by the slot and by every `Lease` on it.
///
/// A take that has been given this engine's port may be mid-inference for up
/// to `INFER_TIMEOUT`, so swapping a new model in must not kill it under that
/// take. The leases count the takes; a retired engine is stopped when the last
/// one lets go.
struct Running {
    /// `None` once stopped, so stopping is safe to ask for twice.
    proc: Mutex<Option<Box<dyn Proc>>>,
    leases: AtomicUsize,
    retired: AtomicBool,
}

impl Running {
    fn new(proc: Box<dyn Proc>) -> Arc<Running> {
        Arc::new(Running {
            proc: Mutex::new(Some(proc)),
            leases: AtomicUsize::new(0),
            retired: AtomicBool::new(false),
        })
    }

    fn alive(&self) -> bool {
        let mut proc = self.proc.lock().unwrap_or_else(|e| e.into_inner());
        proc.as_mut().map(|p| p.alive()).unwrap_or(false)
    }

    fn stopped(&self) -> bool {
        self.proc.lock().unwrap_or_else(|e| e.into_inner()).is_none()
    }

    /// Stop the process, once. The kill happens outside the mutex.
    fn stop(&self) {
        let taken = self.proc.lock().unwrap_or_else(|e| e.into_inner()).take();
        if let Some(mut proc) = taken {
            proc.kill();
        }
    }

    /// No new take will be given this engine: stop it now if nothing is using
    /// it, else when the last lease is dropped. `SeqCst` on both sides, so one
    /// of `retire` and the final `Lease::drop` always sees the other.
    fn retire(&self) {
        self.retired.store(true, Ordering::SeqCst);
        if self.leases.load(Ordering::SeqCst) == 0 {
            self.stop();
        }
    }
}

/// A take's claim on an engine, held for the whole request. Gives the port.
struct Lease {
    run: Arc<Running>,
    port: u16,
}

impl Lease {
    fn new(run: &Arc<Running>, port: u16) -> Lease {
        run.leases.fetch_add(1, Ordering::SeqCst);
        Lease { run: run.clone(), port }
    }
}

impl Drop for Lease {
    fn drop(&mut self) {
        let last = self.run.leases.fetch_sub(1, Ordering::SeqCst) == 1;
        if last && self.run.retired.load(Ordering::SeqCst) {
            self.run.stop();
        }
    }
}

struct Engine {
    run: Arc<Running>,
    port: u16,
    model: String,
    /// What it was loaded with. Compared on every `ensure`, because it cannot
    /// be changed on a running process.
    prompt: String,
    started: Instant,
}

/// What the engine should be running now, resolved from the machine by the
/// caller. `binary` and `model` are `None` when they are not installed.
struct Wanted {
    binary: Option<PathBuf>,
    model: Option<PathBuf>,
    prompt: String,
}

impl Wanted {
    /// The resolved model file name, which is what `Engine.model` holds.
    fn model_name(&self) -> Option<String> {
        self.model
            .as_ref()
            .and_then(|p| p.file_name())
            .map(|n| n.to_string_lossy().to_string())
    }
}

/// One engine process to start.
struct Launch {
    binary: PathBuf,
    model: PathBuf,
    port: u16,
    prompt: String,
}

/// What `EngineSlot` needs from the machine: start a process, ask whether a
/// port answers, find a free port, say what is missing. Injected so the slot
/// can be driven by a fake in tests; `SystemBackend` is the real one.
trait Backend: Send + Sync {
    fn spawn(&self, launch: &Launch) -> SttResult<Box<dyn Proc>>;
    fn ready(&self, port: u16) -> bool;
    fn free_port(&self) -> SttResult<u16>;
    /// The message for "there is nothing to start".
    fn missing(&self) -> String;
    fn start_timeout(&self) -> Duration {
        START_TIMEOUT
    }
    /// How often a starting engine is asked whether it answers yet.
    fn poll_interval(&self) -> Duration {
        Duration::from_millis(100)
    }
}

/// A replacement that failed, keyed by what it was asked to load, so the same
/// request is not retried on every take (a broken model file would otherwise
/// cost a 30 s wait per take). A different request clears it.
struct Failed {
    model: String,
    prompt: String,
    message: String,
}

struct SlotState {
    /// The engine takes are given.
    engine: Option<Engine>,
    /// Swapped out, but possibly still leased by a take mid-inference.
    retired: Vec<Arc<Running>>,
    /// An engine is being started (first start or a replacement). Set and
    /// cleared under the lock; the start itself runs outside it.
    starting: bool,
    /// Counts starts, so a caller that waited can tell which start's outcome
    /// is its own.
    start_seq: u64,
    last_start_error: Option<(u64, String)>,
    failed: Option<Failed>,
    /// Callers waiting for a start, for the log line.
    waiters: usize,
    /// Bumped by `shutdown`, so a start that finishes after it stops what it
    /// started instead of publishing an engine nobody will ever stop.
    epoch: u64,
}

/// The engine behind a lock, and the rules for starting and replacing it.
///
/// The lock is held only to read or change state, never across a start or a
/// readiness probe: a start takes up to 30 s, and `bridge.rs` is
/// single-threaded and reads `running()` and `loaded_model()` for `/health`,
/// so a lock held across a start froze every bridge call behind it.
///
/// An instance rather than a process-wide static of the engine itself, so a
/// test can build its own and tests do not share one engine. Methods that can
/// start a thread take `&Arc<Self>`.
struct EngineSlot {
    state: Mutex<SlotState>,
    /// Signalled when a start finishes, for callers waiting on it.
    started: Condvar,
}

static ENGINE: OnceLock<Arc<EngineSlot>> = OnceLock::new();

fn engine() -> &'static Arc<EngineSlot> {
    ENGINE.get_or_init(|| Arc::new(EngineSlot::new()))
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

/// The model name last asked for (empty before the first ask). Read-only: the
/// settings refresh compares it to learn whether a model change is news.
pub fn preferred_model() -> String {
    PREFERRED.lock().unwrap_or_else(|e| e.into_inner()).clone()
}

/// Words this assistant hears often, given to the decoder before it starts.
///
/// Whisper's initial prompt is not a filter — it cannot make the recogniser
/// refuse anything — it is a hint about the vocabulary and spelling of what is
/// coming. That matters here for two things a general model has no reason to
/// expect: ticket ids like "T-002", and the wake word itself, which came back
/// from live audio as a different word often enough to make hands-free look
/// broken (T-019).
static PROMPT: Mutex<String> = Mutex::new(String::new());

pub fn prefer_prompt(text: &str) {
    let mut slot = PROMPT.lock().unwrap_or_else(|e| e.into_inner());
    if *slot != text {
        *slot = text.to_string();
    }
}

/// The prompt last asked for. Also read by the settings refresh, to tell a
/// changed prompt from a re-applied one.
pub(crate) fn prompt() -> String {
    PROMPT.lock().unwrap_or_else(|e| e.into_inner()).clone()
}

/// The prompt to load the engine with, built from what this machine is set up
/// to hear. Public so the caller can hand it straight to `prefer_prompt` and
/// so it can be tested without an engine.
pub fn prompt_for(wake_word: &str, ticket_prefix: &str) -> String {
    let wake = wake_word.trim();
    let prefix = ticket_prefix.trim();
    let mut parts = vec!["Delivery Console.".to_string()];
    if !wake.is_empty() {
        // Said the way it is said: as an address, at the start of a sentence.
        parts.push(format!("{wake}, what is open?"));
    }
    if !prefix.is_empty() {
        parts.push(format!("Open ticket {prefix}002, {prefix}014."));
    }
    parts.push("Status, verify, blockers, screenshot.".into());
    parts.join(" ")
}

/// The file a model name lives in. A contract shared with the console's
/// downloader (`console/server/voice_assets.py` writes `ggml-{id}.bin`), so it
/// is spelled once here and pinned by a test.
fn model_filename(name: &str) -> String {
    format!("ggml-{name}.bin")
}

/// The file `wanted` resolves to, and whether that is a fallback.
///
/// The named model if it is installed; otherwise any ggml in the directory,
/// smallest first, so a machine with only one still works. No side effects, so
/// the rule can be tested without touching the process-wide preference.
fn resolve_model(repo_root: &std::path::Path, wanted: &str) -> Option<(PathBuf, bool)> {
    let wanted = wanted.trim();
    if !wanted.is_empty() {
        let named = repo_root.join(STT_DIR).join(model_filename(wanted));
        if named.is_file() {
            return Some((named, false));
        }
    }
    smallest_model(repo_root).map(|path| (path, !wanted.is_empty()))
}

/// Remembers the last (wanted, fallback) pair that was warned about.
///
/// `ensure` and `/health` both ask for the model on every call, so a warning
/// per call is a flood. A different pair, or the named model turning up and
/// going again, is a change worth saying once more.
static WARNED: Mutex<Option<(String, String)>> = Mutex::new(None);

/// Should this (wanted, fallback) pair be warned about now? `None` clears the
/// memory, for when the named model is found. Pure apart from `last`.
fn should_warn(last: &mut Option<(String, String)>, pair: Option<(&str, &str)>) -> bool {
    match pair {
        None => {
            *last = None;
            false
        }
        Some((wanted, fallback)) => {
            let now = (wanted.to_string(), fallback.to_string());
            if last.as_ref() == Some(&now) {
                false
            } else {
                *last = Some(now);
                true
            }
        }
    }
}

/// The model to run: the named one if installed, else the smallest, and a
/// machine missing the named one says (once) which it fell back to.
fn model_file(repo_root: &std::path::Path) -> Option<PathBuf> {
    let wanted = PREFERRED.lock().unwrap_or_else(|e| e.into_inner()).clone();
    let wanted = wanted.trim().to_string();
    let resolved = resolve_model(repo_root, &wanted);
    let fallback_name = match &resolved {
        Some((path, true)) => Some(path.file_name().unwrap_or_default().to_string_lossy().to_string()),
        _ => None,
    };
    let warn = {
        let mut last = WARNED.lock().unwrap_or_else(|e| e.into_inner());
        should_warn(&mut last, fallback_name.as_deref().map(|f| (wanted.as_str(), f)))
    };
    if warn {
        log::warn!(
            "stt: {} is not in {STT_DIR}; using {} instead",
            model_filename(&wanted),
            fallback_name.unwrap_or_default()
        );
    }
    resolved.map(|(path, _)| path)
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
    hint_text(
        cfg!(windows),
        server_binary(repo_root).is_some(),
        model_file(repo_root).is_some(),
    )
}

/// The hint for one situation, as a pure function so both operating systems'
/// wording can be tested on either.
///
/// It names only what exists. Models are fetched in Settings (Assistant,
/// Speech models), on every OS. The ENGINE (`whisper-server`) is a separate
/// piece: on Windows `desktop/get-whisper.ps1` installs it; on Linux and macOS
/// there is no script, so it is installed separately and put on PATH or in
/// `desktop/stt`. The word "engine" in every non-empty variant is relied on:
/// `hands_free` stops its loop on a reason containing "engine" (or
/// "microphone"), so an engine lost mid-session ends the loop instead of
/// spinning.
fn hint_text(windows: bool, has_server: bool, has_model: bool) -> String {
    let settings = "Settings, Assistant, Speech models";
    let script = "powershell -File desktop/get-whisper.ps1";
    match (has_server, has_model, windows) {
        (true, true, _) => String::new(),
        (false, false, true) => format!(
            "no speech engine or model in {STT_DIR}. Run: {script} (or get a model in {settings})"
        ),
        (false, false, false) => format!(
            "no speech engine or model in {STT_DIR}. Get a model in {settings}; the engine \
             (whisper-server) is installed separately: put it on PATH or in {STT_DIR}"
        ),
        (false, true, true) => format!(
            "the model is there but the speech engine (whisper-server) is not. Run: {script} \
             ({settings} only manages models)"
        ),
        (false, true, false) => format!(
            "the model is there but the speech engine (whisper-server) is not. It is installed \
             separately: put it on PATH or in {STT_DIR} ({settings} only manages models)"
        ),
        (true, false, true) => format!(
            "the speech engine is there but no ggml-*.bin model. Get one in {settings} \
             (or run: {script})"
        ),
        (true, false, false) => {
            format!("the speech engine is there but no ggml-*.bin model. Get one in {settings}")
        }
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

/// What no longer matches between a running engine and what is wanted now.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Stale {
    Model,
    Prompt,
    Both,
}

impl Stale {
    fn describe(self) -> &'static str {
        match self {
            Stale::Model => "the model changed",
            Stale::Prompt => "the decoder prompt changed",
            Stale::Both => "the model and the decoder prompt changed",
        }
    }
}

/// Is a running engine loaded with something other than what is wanted now?
///
/// The model and the prompt are both fixed when the process starts, so neither
/// can reach a running engine. `wanted_model` is the RESOLVED file name from
/// `model_file`, not the raw preference: a fallback then compares like a
/// choice, and an engine already running the fallback is not restarted to load
/// the same file again. Comparing only the prompt (as this used to) left a
/// changed `stt_model` ignored until the shell was restarted.
fn engine_is_stale(
    running_model: &str,
    running_prompt: &str,
    wanted_model: &str,
    wanted_prompt: &str,
) -> Option<Stale> {
    match (running_model != wanted_model, running_prompt != wanted_prompt) {
        (false, false) => None,
        (true, false) => Some(Stale::Model),
        (false, true) => Some(Stale::Prompt),
        (true, true) => Some(Stale::Both),
    }
}

/// The real machine: `whisper-server` as a child process, and a TCP connect to
/// ask whether it answers.
struct SystemBackend {
    repo_root: PathBuf,
}

impl Backend for SystemBackend {
    fn spawn(&self, launch: &Launch) -> SttResult<Box<dyn Proc>> {
        let mut command = Command::new(&launch.binary);
        command
            .arg("-m")
            .arg(&launch.model)
            .arg("--host")
            .arg("127.0.0.1")
            .arg("--port")
            .arg(launch.port.to_string())
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
            // Vocabulary, not a filter. See `prompt_for`.
            .arg("--prompt")
            .arg(&launch.prompt)
            // The DLLs sit beside the binary.
            .current_dir(launch.binary.parent().unwrap_or(&self.repo_root))
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
            .map_err(|e| format!("cannot start {}: {e}", launch.binary.display()))?;
        Ok(Box::new(child))
    }

    fn ready(&self, port: u16) -> bool {
        responding(port)
    }

    fn free_port(&self) -> SttResult<u16> {
        free_port()
    }

    fn missing(&self) -> String {
        hint(&self.repo_root)
    }
}

const SHUT_DOWN: &str = "the speech engine was shut down";

/// Start one engine process and wait for it to answer. Takes no lock: this is
/// the up-to-`START_TIMEOUT` part.
fn start_engine(
    backend: &Arc<dyn Backend>,
    binary: PathBuf,
    model: PathBuf,
    prompt: String,
) -> SttResult<Engine> {
    let name = model.file_name().unwrap_or_default().to_string_lossy().to_string();
    let port = backend.free_port()?;
    let mut proc = backend.spawn(&Launch { binary, model, port, prompt: prompt.clone() })?;

    let timeout = backend.start_timeout();
    let poll = backend.poll_interval();
    let waited = Instant::now();
    while waited.elapsed() < timeout {
        // A process that has already exited (a model that will not load, a
        // missing DLL) is not going to answer: say so now rather than after the
        // whole timeout. Asked before `ready`, so something else that grabbed
        // the port is not mistaken for the engine.
        if !proc.alive() {
            proc.kill(); // reaps it
            return Err(format!("the speech engine exited while loading {name}"));
        }
        if backend.ready(port) {
            log::info!("stt: engine up on {port} with {name}");
            return Ok(Engine {
                run: Running::new(proc),
                port,
                model: name,
                prompt,
                started: Instant::now(),
            });
        }
        std::thread::sleep(poll);
    }

    proc.kill();
    Err(format!(
        "the speech engine did not start within {}s",
        timeout.as_secs()
    ))
}

/// Move a replaced engine to the retired list, so `shutdown` can still reach
/// it while a take holds it. The caller calls `retire` on the result AFTER
/// releasing the slot lock: stopping a process is not done under it.
fn retire_engine(state: &mut SlotState, engine: Engine) -> Arc<Running> {
    state.retired.retain(|r| !r.stopped());
    state.retired.push(engine.run.clone());
    engine.run
}

impl EngineSlot {
    fn new() -> Self {
        EngineSlot {
            state: Mutex::new(SlotState {
                engine: None,
                retired: Vec::new(),
                starting: false,
                start_seq: 0,
                last_start_error: None,
                failed: None,
                waiters: 0,
                epoch: 0,
            }),
            started: Condvar::new(),
        }
    }

    fn lock(&self) -> std::sync::MutexGuard<'_, SlotState> {
        self.state.lock().unwrap_or_else(|e| e.into_inner())
    }

    /// A lease on an engine that is running what is wanted, starting one if
    /// there is none.
    ///
    /// - Serving, answering, current: its lease, at once.
    /// - Serving and answering but NOT current (the model or the prompt
    ///   changed): the same lease, at once, and the replacement starts in the
    ///   background on another port. A take never waits on a swap, and never
    ///   fails because of one.
    /// - Nothing serving, or it died or stopped answering: it is started here,
    ///   outside the lock; callers that arrive meanwhile wait for that start
    ///   on the condvar rather than on the lock.
    fn ensure_with(
        self: &Arc<Self>,
        wanted: &Wanted,
        backend: &Arc<dyn Backend>,
    ) -> SttResult<Lease> {
        let wanted_model = wanted.model_name();
        // A caller waiting on someone else's start gives up a little after a
        // start would have.
        let give_up = Instant::now() + backend.start_timeout() + Duration::from_secs(5);
        let mut waiting_for: Option<u64> = None;

        loop {
            // A lease on whatever is serving, taken under the lock so it
            // cannot be stopped while it is looked at.
            let lease = {
                let state = self.lock();
                state.engine.as_ref().map(|e| Lease::new(&e.run, e.port))
            };
            // Is it alive and answering? A connect, up to 250 ms when the
            // engine is wedged: asked with the lock released.
            let healthy = lease
                .as_ref()
                .map(|l| l.run.alive() && backend.ready(l.port))
                .unwrap_or(false);

            let mut state = self.lock();
            let same = match (&lease, state.engine.as_ref()) {
                (Some(l), Some(e)) => Arc::ptr_eq(&l.run, &e.run),
                (None, None) => true,
                _ => false,
            };
            if !same {
                // Swapped or removed while we looked; look again.
                drop(state);
                drop(lease);
                continue;
            }

            if healthy {
                let lease = lease.expect("healthy means there is an engine");
                let engine = state.engine.as_ref().expect("same engine as the lease");
                // No model resolvable (the file went away under a running
                // engine) is no opinion on the model: keep what is running.
                let stale = engine_is_stale(
                    &engine.model,
                    &engine.prompt,
                    wanted_model.as_deref().unwrap_or(&engine.model),
                    &wanted.prompt,
                );
                match stale {
                    None => state.failed = None,
                    Some(why) => self.begin_swap(&mut state, wanted, backend, why),
                }
                return Ok(lease);
            }

            // Nothing to serve: none at all, or it died or stopped answering.
            if let Some(seq) = waiting_for {
                if !state.starting {
                    // The start we waited for has ended. If it failed, that
                    // failure is this caller's too, not a reason to start the
                    // same thing again for another 30 s.
                    if let Some((failed_seq, message)) = &state.last_start_error {
                        if *failed_seq == seq {
                            return Err(message.clone());
                        }
                    }
                    waiting_for = None;
                }
            }
            if state.starting {
                waiting_for.get_or_insert(state.start_seq);
                let now = Instant::now();
                if now >= give_up {
                    return Err("timed out waiting for the speech engine to start".into());
                }
                state.waiters += 1;
                log::debug!("stt: waiting for the engine to start ({} waiting)", state.waiters);
                let (guard, _) = self
                    .started
                    .wait_timeout(state, give_up - now)
                    .unwrap_or_else(|e| e.into_inner());
                state = guard;
                state.waiters -= 1;
                drop(state);
                drop(lease);
                continue;
            }

            // We start it.
            let dead = state.engine.take().map(|e| retire_engine(&mut state, e));
            let (Some(binary), Some(model)) = (wanted.binary.clone(), wanted.model.clone()) else {
                drop(state);
                drop(lease);
                if let Some(dead) = dead {
                    dead.retire();
                }
                return Err(backend.missing());
            };
            state.starting = true;
            state.start_seq += 1;
            let (seq, epoch) = (state.start_seq, state.epoch);
            drop(state);
            drop(lease);
            if let Some(dead) = dead {
                dead.retire();
            }

            let outcome = start_engine(backend, binary, model, wanted.prompt.clone());
            return self.finish_start(seq, epoch, outcome);
        }
    }

    /// Publish what a synchronous start produced, and wake whoever waited.
    fn finish_start(&self, seq: u64, epoch: u64, outcome: SttResult<Engine>) -> SttResult<Lease> {
        let mut state = self.lock();
        state.starting = false;
        let result = match outcome {
            Ok(engine) if state.epoch == epoch => {
                let lease = Lease::new(&engine.run, engine.port);
                state.failed = None;
                state.engine = Some(engine);
                Ok(lease)
            }
            Ok(engine) => {
                // `shutdown` ran while this was starting.
                state.last_start_error = Some((seq, SHUT_DOWN.into()));
                drop(state);
                self.started.notify_all();
                engine.run.stop();
                return Err(SHUT_DOWN.into());
            }
            Err(message) => {
                state.last_start_error = Some((seq, message.clone()));
                Err(message)
            }
        };
        drop(state);
        self.started.notify_all();
        result
    }

    /// The serving engine is not what is wanted. Start the replacement on a
    /// thread, unless one is already starting, there is nothing to start it
    /// from, or this exact request already failed (the key changing clears
    /// that). Called with the lock held, and starts no process itself.
    fn begin_swap(
        self: &Arc<Self>,
        state: &mut SlotState,
        wanted: &Wanted,
        backend: &Arc<dyn Backend>,
        why: Stale,
    ) {
        let (Some(binary), Some(model), Some(name)) =
            (wanted.binary.clone(), wanted.model.clone(), wanted.model_name())
        else {
            return;
        };
        if state.starting {
            return;
        }
        if let Some(failed) = &state.failed {
            if failed.model == name && failed.prompt == wanted.prompt {
                return;
            }
        }
        state.failed = None;
        state.starting = true;
        state.start_seq += 1;
        let (seq, epoch) = (state.start_seq, state.epoch);
        log::info!(
            "stt: restarting the engine — {}; the current one keeps serving until the new one answers",
            why.describe()
        );

        let slot = Arc::clone(self);
        let backend = Arc::clone(backend);
        let prompt = wanted.prompt.clone();
        let (thread_name, thread_prompt) = (name.clone(), prompt.clone());
        let spawned = std::thread::Builder::new().name("stt-swap".into()).spawn(move || {
            let outcome = start_engine(&backend, binary, model, thread_prompt.clone());
            slot.finish_swap(seq, epoch, thread_name, thread_prompt, outcome);
        });
        if let Err(e) = spawned {
            let message = format!("cannot start the replacement engine: {e}");
            state.starting = false;
            state.failed = Some(Failed { model: name, prompt, message });
        }
    }

    /// Publish a replacement under a short lock so new takes use it, then stop
    /// the old engine (now, or when the last take holding it lets go). A
    /// replacement that failed is dropped and the old engine stays.
    fn finish_swap(
        &self,
        seq: u64,
        epoch: u64,
        name: String,
        prompt: String,
        outcome: SttResult<Engine>,
    ) {
        let mut state = self.lock();
        match outcome {
            Ok(engine) if state.epoch == epoch => {
                let old = state.engine.replace(engine).map(|e| retire_engine(&mut state, e));
                state.failed = None;
                drop(state);
                // Published: takes from here on use the new engine, and
                // callers waiting for one are woken. `starting` stays set
                // until the old engine has been told to stop, so "no start in
                // flight" also means "nothing left to stop".
                self.started.notify_all();
                if let Some(old) = old {
                    log::info!("stt: engine swapped to {name}; stopping the old one");
                    old.retire();
                }
            }
            Ok(engine) => {
                state.last_start_error = Some((seq, SHUT_DOWN.into()));
                drop(state);
                engine.run.stop();
            }
            Err(message) => {
                log::warn!("stt: could not load {name}: {message}; the current engine stays");
                state.last_start_error = Some((seq, message.clone()));
                state.failed = Some(Failed { model: name, prompt, message });
                drop(state);
            }
        }
        self.lock().starting = false;
        self.started.notify_all();
    }

    /// Start the replacement now if the running engine is not what is wanted,
    /// without waiting for a take. Does nothing when no engine is running (it
    /// must not load a model nobody asked for) or when it is current.
    fn prewarm_with(self: &Arc<Self>, wanted: &Wanted, backend: &Arc<dyn Backend>) {
        let mut state = self.lock();
        let Some(engine) = state.engine.as_ref() else {
            return;
        };
        let stale = engine_is_stale(
            &engine.model,
            &engine.prompt,
            wanted.model_name().as_deref().unwrap_or(&engine.model),
            &wanted.prompt,
        );
        if let Some(why) = stale {
            self.begin_swap(&mut state, wanted, backend, why);
        }
    }

    /// Why the last replacement failed; empty when it did not (or since
    /// cleared). The old engine was still serving.
    fn swap_error(&self) -> String {
        self.lock().failed.as_ref().map(|f| f.message.clone()).unwrap_or_default()
    }

    fn shutdown(&self) {
        let (engine, retired) = {
            let mut state = self.lock();
            state.epoch += 1;
            state.failed = None;
            (state.engine.take(), std::mem::take(&mut state.retired))
        };
        self.started.notify_all();
        if let Some(engine) = engine {
            engine.run.stop();
            log::info!("stt: engine stopped after {:?}", engine.started.elapsed());
        }
        for run in retired {
            run.stop();
        }
    }

    fn running(&self) -> bool {
        self.lock().engine.as_ref().map(|e| e.run.alive()).unwrap_or(false)
    }

    fn loaded_model(&self) -> String {
        self.lock().engine.as_ref().map(|e| e.model.clone()).unwrap_or_default()
    }

    /// Block until no start is in flight. For tests, which have no other
    /// deterministic way to wait for a background swap to finish.
    #[cfg(test)]
    fn wait_idle(&self, timeout: Duration) -> bool {
        let give_up = Instant::now() + timeout;
        let mut state = self.lock();
        while state.starting {
            let now = Instant::now();
            if now >= give_up {
                return false;
            }
            state = self
                .started
                .wait_timeout(state, give_up - now)
                .unwrap_or_else(|e| e.into_inner())
                .0;
        }
        true
    }

    #[cfg(test)]
    fn waiters(&self) -> usize {
        self.lock().waiters
    }
}

fn system_backend(repo_root: &std::path::Path) -> Arc<dyn Backend> {
    Arc::new(SystemBackend { repo_root: repo_root.to_path_buf() })
}

/// What the engine should be running now, from what is installed and set.
fn wanted_now(repo_root: &std::path::Path) -> Wanted {
    Wanted {
        binary: server_binary(repo_root),
        model: model_file(repo_root),
        prompt: prompt(),
    }
}

/// A lease on an engine running what is wanted now, starting one if there is
/// none. The lease keeps the engine alive for the whole request.
fn ensure(repo_root: &std::path::Path) -> SttResult<Lease> {
    engine().ensure_with(&wanted_now(repo_root), &system_backend(repo_root))
}

/// If the running engine is not what is wanted now, start the replacement in
/// the background, so the swap is usually done before the next take. Returns
/// at once; does nothing when no engine is running.
pub fn prewarm(repo_root: &std::path::Path) {
    engine().prewarm_with(&wanted_now(repo_root), &system_backend(repo_root));
}

/// Why the last model or prompt swap failed, empty when it did not. For
/// `/listen/state`.
pub fn swap_error() -> String {
    engine().swap_error()
}

/// Stop the engine. Called when the shell quits so a 150 MB model is not left
/// resident.
pub fn shutdown() {
    engine().shutdown();
}

pub fn running() -> bool {
    engine().running()
}

pub fn loaded_model() -> String {
    engine().loaded_model()
}

/// Transcribe a WAV. Blocking; the caller is already on a worker thread.
pub fn transcribe(repo_root: &std::path::Path, wav: &[u8]) -> SttResult<String> {
    // `ensure` may have to START the engine and wait for a 150 MB model to
    // load; inference is a different cost with a different fix, so they are
    // timed apart rather than reported as one number.
    let step = Instant::now();
    // Held until this function returns: if a new model is swapped in while
    // this take is mid-inference, the engine it is talking to is stopped only
    // after the lease is dropped.
    let lease = ensure(repo_root)?;
    let port = lease.port;
    let ensured_ms = step.elapsed().as_millis();
    let inferring = Instant::now();
    let stream = TcpStream::connect(("127.0.0.1", port))
        .map_err(|e| format!("cannot reach the speech engine: {e}"))?;
    let payload = infer(stream, port, &multipart(wav), INFER_TIMEOUT)?;

    log::info!(
        "stt: engine ready in {ensured_ms}ms, inference {}ms",
        inferring.elapsed().as_millis()
    );
    Ok(extract_text(&payload))
}

/// One inference request over `stream`, connected to the engine on `port`: the
/// multipart `body` out, the answer's payload back.
///
/// `timeout` bounds each read and each write. An engine that accepts the
/// connection and then never reads (wedged, or suspended) would otherwise block
/// `write_all` for good once the socket buffers fill, and the caller's lease
/// would keep that engine from being retired until the shell quit.
fn infer(mut stream: TcpStream, port: u16, body: &[u8], timeout: Duration) -> SttResult<String> {
    stream
        .set_read_timeout(Some(timeout))
        .map_err(|e| e.to_string())?;
    stream
        .set_write_timeout(Some(timeout))
        .map_err(|e| e.to_string())?;

    let head = format!(
        "POST /inference HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n\
         Content-Type: multipart/form-data; boundary={BOUNDARY}\r\n\
         Content-Length: {}\r\nConnection: close\r\n\r\n",
        body.len()
    );
    stream
        .write_all(head.as_bytes())
        .and_then(|()| stream.write_all(body))
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
    Ok(payload)
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
        // "Unavailable" alone is not actionable; the message has to say where
        // to fix it. Per OS: Windows has a script that installs the engine,
        // the other systems have none, so the hint must not name one.
        let empty = std::env::temp_dir().join("t006-no-stt-here");
        let h = hint(&empty);
        if cfg!(windows) {
            assert!(h.contains("get-whisper.ps1"), "{h}");
        } else {
            assert!(h.contains("Settings") && h.contains("whisper-server"), "{h}");
            assert!(!h.contains("get-whisper"), "{h}");
        }
    }

    /// Every situation the hint distinguishes, on both operating systems.
    fn every_hint() -> Vec<(bool, bool, bool, String)> {
        let mut all = Vec::new();
        for windows in [true, false] {
            for (server, model) in [(false, false), (false, true), (true, false), (true, true)] {
                all.push((windows, server, model, hint_text(windows, server, model)));
            }
        }
        all
    }

    #[test]
    fn a_hint_exists_exactly_when_something_is_missing() {
        for (windows, server, model, h) in every_hint() {
            assert_eq!(h.is_empty(), server && model, "windows={windows} server={server} model={model}: {h:?}");
        }
    }

    #[test]
    fn every_hint_says_where_models_are_fetched() {
        // AC-44: the Settings screen is the one place that works on every OS.
        for (windows, server, model, h) in every_hint().into_iter().filter(|e| !e.3.is_empty()) {
            assert!(
                h.contains("Settings, Assistant, Speech models"),
                "windows={windows} server={server} model={model}: {h}"
            );
        }
    }

    #[test]
    fn every_script_a_hint_names_exists() {
        // AC-44: a shell script that never existed was named here for a long
        // time. Every `get-*.ps1` / `get-*.sh` a hint mentions must be a file
        // in `desktop/`, and the systems with no script name none.
        let root = repo();
        let mut named = 0;
        for (windows, server, model, h) in every_hint() {
            for word in h.split_whitespace() {
                let word = word.trim_matches(|c: char| ",.()".contains(c));
                if let Some(file) = word.strip_prefix("desktop/get-") {
                    named += 1;
                    assert!(
                        (file.ends_with(".ps1") || file.ends_with(".sh"))
                            && root.join("desktop").join(format!("get-{file}")).is_file(),
                        "windows={windows} server={server} model={model}: {h} names {word}, which is not in desktop/"
                    );
                    assert!(windows, "a non-Windows hint names a script: {h}");
                }
            }
        }
        assert!(named > 0, "the Windows hints should name the script that exists");
        assert!(!hint_text(false, false, false).contains("get-"));
    }

    #[test]
    fn a_non_windows_hint_says_the_engine_is_installed_separately() {
        // D-3: the console downloads models and voices, not `whisper-server`,
        // and there is no script for it off Windows.
        for (server, model) in [(false, false), (false, true)] {
            let h = hint_text(false, server, model);
            assert!(h.contains("installed separately"), "{h}");
            assert!(h.contains("PATH") && h.contains(STT_DIR), "{h}");
        }
    }

    #[test]
    fn every_hint_contains_the_word_the_hands_free_loop_stops_on() {
        // `hands_free.rs` ends its loop when a take fails with a reason
        // containing "microphone" or "engine" (a broken one would otherwise
        // spin it). The reason is `listen::hint`: the microphone sentence, or
        // this. Pinned from both sides: every non-empty hint says "engine",
        // and the matcher and the microphone sentence still say what this
        // relies on. Reworded without updating the other side, a mid-session
        // loss would loop forever instead of stopping.
        for (windows, server, model, h) in every_hint().into_iter().filter(|e| !e.3.is_empty()) {
            assert!(h.contains("engine"), "windows={windows} server={server} model={model}: {h}");
        }
        let hands_free = include_str!("hands_free.rs");
        assert!(
            hands_free.contains(r#"reason.contains("microphone") || reason.contains("engine")"#),
            "hands_free.rs no longer stops on \"microphone\" or \"engine\"; update the hints to match"
        );
        let listen = include_str!("listen.rs");
        assert!(
            listen.contains(r#""no microphone: nothing is set as the default input device""#),
            "listen::hint's microphone sentence changed; it must still contain \"microphone\""
        );
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
    fn the_prompt_names_the_words_a_general_model_would_not_expect() {
        let p = prompt_for("console", "T-");
        assert!(p.contains("console,"), "the wake word, said the way it is said: {p}");
        assert!(p.contains("T-002"), "a ticket id in the shape ids take: {p}");
    }

    #[test]
    fn a_machine_with_no_wake_word_still_gets_a_usable_prompt() {
        let p = prompt_for("", "T-");
        assert!(!p.is_empty());
        assert!(!p.contains(" ,"), "no gap where the wake word would have been: {p}");
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

    /// Runs `stop` when dropped, which includes a panic unwinding past it.
    struct Guard<F: FnMut()>(F);

    impl<F: FnMut()> Drop for Guard<F> {
        fn drop(&mut self) {
            (self.0)();
        }
    }

    #[test]
    fn a_guard_runs_when_the_test_passes_and_when_it_panics() {
        // F6: the real-engine test below holds one of these around its
        // transcription. A failed `expect` there must still stop the engine, or
        // `whisper-server` outlives the test process.
        let stops = AtomicUsize::new(0);
        {
            let _guard = Guard(|| {
                stops.fetch_add(1, Ordering::SeqCst);
            });
        }
        assert_eq!(stops.load(Ordering::SeqCst), 1, "dropped on the normal path");

        let unwound = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            let _guard = Guard(|| {
                stops.fetch_add(1, Ordering::SeqCst);
            });
            panic!("the transcription failed");
        }));
        assert!(unwound.is_err(), "the closure did panic");
        assert_eq!(stops.load(Ordering::SeqCst), 2, "dropped while the panic unwound");
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
        // A test that leaves a 270 MB process holding a loaded model behind it
        // keeps the test harness waiting on exit, which looks exactly like a
        // hang. The guard stops the engine on every way out, a failed
        // transcription (which starts the engine, then panics here) included,
        // so it is made before the engine can exist.
        // Shuts the one process-wide engine down on the way out, so it must not
        // overlap a take that is using it (the replay tests hold this too).
        let _serial = crate::listen::testing::serial();
        let _stop = Guard(shutdown);
        let heard = transcribe(&root, &wav).expect("the engine should transcribe this");
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

    /// A throwaway repo root whose `desktop/stt` holds files of the given
    /// sizes. Never the process-wide preference: tests that set it would race
    /// every other test (and the real-engine one) that reads it.
    fn scratch_models(tag: &str, files: &[(&str, usize)]) -> PathBuf {
        let root = std::env::temp_dir().join(format!("t031-{tag}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&root);
        let dir = root.join(STT_DIR);
        std::fs::create_dir_all(&dir).expect("a scratch directory");
        for (name, len) in files {
            std::fs::write(dir.join(name), vec![0u8; *len]).expect("a scratch file");
        }
        root
    }

    fn file_name_of(path: &std::path::Path) -> String {
        path.file_name().unwrap_or_default().to_string_lossy().to_string()
    }

    // ---- a fake engine, so the slot is tested with no process and no network

    use std::collections::{HashSet, VecDeque};
    use std::sync::atomic::AtomicU16;
    use std::sync::atomic::AtomicU64;
    use std::sync::mpsc::{channel, Receiver, Sender};

    /// What the next `spawn` does. Anything not scripted starts and answers.
    enum Step {
        /// Reports it was entered, waits until the test lets it go (dropping
        /// the sender lets it go too), then starts and answers, or fails.
        Block {
            entered: Sender<()>,
            release: Receiver<()>,
            then_fail: Option<&'static str>,
        },
        /// `spawn` itself fails.
        Fail(&'static str),
        /// Starts, but does not answer until the test calls `World::answer`.
        Silent,
        /// Starts and has exited by the time anyone looks, without ever
        /// answering: what a process does when the model will not load.
        Exits,
    }

    /// What a fake engine process can see and be told, shared by the backend,
    /// its processes and the test. `log` is the ordered record of what
    /// happened; `wait_event` blocks on it, so a test never sleeps to wait.
    struct World {
        log: Mutex<Vec<String>>,
        logged: Condvar,
        /// Ports that answer.
        up: Mutex<HashSet<u16>>,
        /// Processes that exited by themselves.
        dead: Mutex<HashSet<u16>>,
        ports: AtomicU16,
        spawns: AtomicUsize,
    }

    impl World {
        fn new() -> Arc<World> {
            Arc::new(World {
                log: Mutex::new(Vec::new()),
                logged: Condvar::new(),
                up: Mutex::new(HashSet::new()),
                dead: Mutex::new(HashSet::new()),
                ports: AtomicU16::new(9001),
                spawns: AtomicUsize::new(0),
            })
        }

        fn note(&self, event: String) {
            self.log.lock().unwrap().push(event);
            self.logged.notify_all();
        }

        fn events(&self) -> Vec<String> {
            self.log.lock().unwrap().clone()
        }

        fn position(&self, event: &str) -> Option<usize> {
            self.events().iter().position(|e| e == event)
        }

        /// Block until `event` has been logged.
        fn wait_event(&self, event: &str) {
            let give_up = Instant::now() + Duration::from_secs(10);
            let mut log = self.log.lock().unwrap();
            while !log.iter().any(|e| e == event) {
                let now = Instant::now();
                assert!(now < give_up, "timed out waiting for {event:?}; log: {log:?}");
                log = self.logged.wait_timeout(log, give_up - now).unwrap().0;
            }
        }

        fn spawns(&self) -> usize {
            self.spawns.load(Ordering::SeqCst)
        }

        fn kills(&self, port: u16) -> usize {
            let wanted = format!("kill:{port}");
            self.events().iter().filter(|e| **e == wanted).count()
        }

        /// Make a silent engine start answering.
        fn answer(&self, port: u16) {
            self.up.lock().unwrap().insert(port);
        }
    }

    struct FakeProc {
        port: u16,
        world: Arc<World>,
        killed: bool,
    }

    impl Proc for FakeProc {
        fn alive(&mut self) -> bool {
            !self.killed && !self.world.dead.lock().unwrap().contains(&self.port)
        }

        fn kill(&mut self) {
            if !self.killed {
                self.killed = true;
                self.world.up.lock().unwrap().remove(&self.port);
                self.world.note(format!("kill:{}", self.port));
            }
        }
    }

    struct FakeBackend {
        world: Arc<World>,
        script: Mutex<VecDeque<Step>>,
        /// Ports already reported as answering, so `ready:{port}` is logged
        /// once, at the moment it first answers.
        reported: Mutex<HashSet<u16>>,
        timeout_ms: AtomicU64,
    }

    impl FakeBackend {
        fn push(&self, step: Step) {
            self.script.lock().unwrap().push_back(step);
        }

        fn set_timeout(&self, timeout: Duration) {
            self.timeout_ms.store(timeout.as_millis() as u64, Ordering::SeqCst);
        }
    }

    impl Backend for FakeBackend {
        fn spawn(&self, launch: &Launch) -> SttResult<Box<dyn Proc>> {
            self.world.spawns.fetch_add(1, Ordering::SeqCst);
            self.world.note(format!(
                "spawn:{}:{}:{}",
                launch.port,
                file_name_of(&launch.model),
                launch.prompt
            ));
            let step = self.script.lock().unwrap().pop_front();
            let mut answers = true;
            match step {
                None => {}
                Some(Step::Fail(message)) => return Err(message.to_string()),
                Some(Step::Silent) => answers = false,
                Some(Step::Exits) => {
                    answers = false;
                    self.world.dead.lock().unwrap().insert(launch.port);
                }
                Some(Step::Block { entered, release, then_fail }) => {
                    let _ = entered.send(());
                    // Err means the sender was dropped: also a release.
                    let _ = release.recv();
                    if let Some(message) = then_fail {
                        return Err(message.to_string());
                    }
                }
            }
            if answers {
                self.world.up.lock().unwrap().insert(launch.port);
            }
            Ok(Box::new(FakeProc {
                port: launch.port,
                world: self.world.clone(),
                killed: false,
            }))
        }

        fn ready(&self, port: u16) -> bool {
            let up = self.world.up.lock().unwrap().contains(&port);
            if up && self.reported.lock().unwrap().insert(port) {
                self.world.note(format!("ready:{port}"));
            }
            up
        }

        fn free_port(&self) -> SttResult<u16> {
            Ok(self.world.ports.fetch_add(1, Ordering::SeqCst))
        }

        fn missing(&self) -> String {
            "nothing is installed".into()
        }

        fn start_timeout(&self) -> Duration {
            Duration::from_millis(self.timeout_ms.load(Ordering::SeqCst))
        }

        fn poll_interval(&self) -> Duration {
            Duration::from_millis(2)
        }
    }

    /// A private slot, its fake world and its backend.
    struct Rig {
        slot: Arc<EngineSlot>,
        world: Arc<World>,
        fake: Arc<FakeBackend>,
        backend: Arc<dyn Backend>,
    }

    impl Rig {
        fn new() -> Rig {
            let world = World::new();
            let fake = Arc::new(FakeBackend {
                world: world.clone(),
                script: Mutex::new(VecDeque::new()),
                reported: Mutex::new(HashSet::new()),
                timeout_ms: AtomicU64::new(5_000),
            });
            let backend: Arc<dyn Backend> = fake.clone();
            Rig { slot: Arc::new(EngineSlot::new()), world, fake, backend }
        }

        fn ensure(&self, wanted: &Wanted) -> SttResult<Lease> {
            self.slot.ensure_with(wanted, &self.backend)
        }

        /// The port a take is given, the lease dropped at once.
        fn port(&self, wanted: &Wanted) -> SttResult<u16> {
            self.ensure(wanted).map(|lease| lease.port)
        }

        /// Script the next spawn to block, and return the two ends the test
        /// drives it with: wait on the receiver until the spawn is entered,
        /// send on (or drop) the sender to let it go.
        fn block_next_spawn(&self) -> (Receiver<()>, Sender<()>) {
            let (entered_tx, entered_rx) = channel();
            let (release_tx, release_rx) = channel();
            self.fake.push(Step::Block {
                entered: entered_tx,
                release: release_rx,
                then_fail: None,
            });
            (entered_rx, release_tx)
        }
    }

    fn want(model: &str, prompt: &str) -> Wanted {
        Wanted {
            binary: Some(PathBuf::from("desktop/stt/whisper-server")),
            model: Some(PathBuf::from(format!("desktop/stt/{model}"))),
            prompt: prompt.to_string(),
        }
    }

    fn base() -> Wanted {
        want("ggml-base.en.bin", "p")
    }

    fn tiny() -> Wanted {
        want("ggml-tiny.en.bin", "p")
    }

    const WAIT: Duration = Duration::from_secs(10);

    #[test]
    fn a_slot_starts_the_engine_once_and_reuses_it() {
        let rig = Rig::new();
        assert!(!rig.slot.running(), "a new slot has no engine");
        assert_eq!(rig.slot.loaded_model(), "");

        let first = rig.port(&base()).expect("the fake engine starts");
        for _ in 0..3 {
            assert_eq!(rig.port(&base()), Ok(first), "reused, same port");
        }
        assert_eq!(rig.world.spawns(), 1, "started once");
        assert!(rig.slot.running());
        assert_eq!(rig.slot.loaded_model(), "ggml-base.en.bin");
        assert_eq!(rig.world.events()[0], format!("spawn:{first}:ggml-base.en.bin:p"));
    }

    #[test]
    fn shutdown_stops_the_engine_through_the_process_handle() {
        let rig = Rig::new();
        let port = rig.port(&base()).expect("the fake engine starts");

        rig.slot.shutdown();
        assert_eq!(rig.world.kills(port), 1, "the fake process was killed");
        assert!(!rig.slot.running());
        assert_eq!(rig.slot.loaded_model(), "");
        rig.slot.shutdown();
        assert_eq!(rig.world.kills(port), 1, "a second shutdown has nothing to stop");
    }

    #[test]
    fn nothing_to_start_says_what_is_missing() {
        let rig = Rig::new();
        let mut no_binary = base();
        no_binary.binary = None;
        assert_eq!(rig.port(&no_binary), Err("nothing is installed".into()));
        let mut no_model = base();
        no_model.model = None;
        assert_eq!(rig.port(&no_model), Err("nothing is installed".into()));
        assert_eq!(rig.world.spawns(), 0, "nothing was started");
    }

    #[test]
    fn an_engine_that_never_answers_is_killed_and_reported() {
        let rig = Rig::new();
        rig.fake.set_timeout(Duration::from_millis(300));
        rig.fake.push(Step::Silent);

        let err = rig.port(&base()).expect_err("it never answers");
        assert!(err.contains("did not start"), "{err}");
        assert_eq!(rig.world.kills(9001), 1, "the process that never answered is stopped");
        assert!(!rig.slot.running());
        assert_eq!(rig.slot.loaded_model(), "", "nothing was published");
    }

    #[test]
    fn an_engine_that_exits_while_loading_fails_at_once_not_after_the_start_timeout() {
        // F1-lite: a model that will not load makes the process exit. Waiting
        // out the whole start timeout for a process that is already gone cost
        // 30 s per attempt. The injected timeout here is 2 s; the answer must
        // come far sooner than that.
        let rig = Rig::new();
        rig.fake.set_timeout(Duration::from_secs(2));
        rig.fake.push(Step::Exits);

        let started = Instant::now();
        let err = rig.port(&base()).expect_err("the process is gone");
        let took = started.elapsed();

        assert!(took < Duration::from_millis(500), "waited {took:?} on a process that had already exited: {err}");
        assert!(err.contains("exited"), "{err}");
        assert!(err.contains("ggml-base.en.bin"), "the message names the model: {err}");
        assert!(!err.contains("did not start"), "that is the timeout's message: {err}");
        assert_eq!(rig.world.kills(9001), 1, "the dead process is still reaped");
        assert_eq!(rig.world.spawns(), 1);
        assert!(!rig.slot.running());
        assert_eq!(rig.slot.loaded_model(), "", "nothing was published");
    }

    #[test]
    fn a_replacement_that_exits_while_loading_is_abandoned_at_once_and_the_old_engine_kept() {
        let rig = Rig::new();
        assert_eq!(rig.port(&base()), Ok(9001));
        rig.fake.set_timeout(Duration::from_secs(2));
        rig.fake.push(Step::Exits);

        let started = Instant::now();
        assert_eq!(rig.port(&tiny()), Ok(9001), "the take is served by the old engine");
        assert!(rig.slot.wait_idle(WAIT), "the attempt ended");
        let took = started.elapsed();

        assert!(took < Duration::from_millis(500), "the swap took {took:?} to give up on a dead process");
        let error = rig.slot.swap_error();
        assert!(error.contains("exited") && error.contains("ggml-tiny.en.bin"), "{error:?}");
        assert_eq!(rig.world.kills(9002), 1, "the dead replacement is reaped");
        assert_eq!(rig.world.kills(9001), 0, "the old engine is kept");
        assert_eq!(rig.slot.loaded_model(), "ggml-base.en.bin");
    }

    // ---- the HTTP exchange with an engine that is wedged (F3)

    /// A stand-in engine on loopback that accepts one connection and then does
    /// not read it, holding it open until the sender is sent to or dropped.
    fn engine_that_accepts_and_never_reads() -> (u16, Sender<()>, std::thread::JoinHandle<()>) {
        let listener = std::net::TcpListener::bind("127.0.0.1:0").expect("a loopback port");
        let port = listener.local_addr().expect("it has an address").port();
        let (release, held) = channel::<()>();
        let thread = std::thread::spawn(move || {
            let _connection = listener.accept().expect("the take connects");
            let _ = held.recv();
        });
        (port, release, thread)
    }

    /// Write until the kernel will take no more, so that the next write blocks.
    /// One huge write is no help: Windows accepts a single write of any size,
    /// then blocks the one after it. The write timeout used to find the limit
    /// is cleared again, so the code under test has to bring its own.
    fn fill_the_send_buffers(stream: &mut TcpStream) {
        stream.set_write_timeout(Some(Duration::from_millis(100))).expect("a timeout");
        let chunk = vec![0u8; 64 << 10];
        let mut sent = 0usize;
        loop {
            match stream.write(&chunk) {
                Ok(n) => {
                    sent += n;
                    assert!(sent < 1 << 30, "1 GB went in and the connection is still not full");
                }
                Err(e) if matches!(e.kind(), std::io::ErrorKind::TimedOut | std::io::ErrorKind::WouldBlock) => break,
                Err(e) => panic!("filling the connection failed: {e}"),
            }
        }
        stream.set_write_timeout(None).expect("no timeout");
    }

    /// `infer` on its own thread over a connection to the stand-in, so a call
    /// that never returns fails the test after `give_up` instead of hanging the
    /// run. The stand-in is released afterwards either way, which also unblocks
    /// a stuck writer. `full` first saturates the connection's send side.
    fn infer_against_a_wedged_engine(
        full: bool,
        body: Vec<u8>,
        timeout: Duration,
        give_up: Duration,
    ) -> (SttResult<String>, Duration) {
        let (port, release, held) = engine_that_accepts_and_never_reads();
        let mut stream = TcpStream::connect(("127.0.0.1", port)).expect("the stand-in accepts");
        if full {
            fill_the_send_buffers(&mut stream);
        }
        let (tx, rx) = channel();
        let started = Instant::now();
        std::thread::spawn(move || {
            let _ = tx.send(infer(stream, port, &body, timeout));
        });
        let outcome = rx.recv_timeout(give_up);
        let took = started.elapsed();
        drop(release);
        held.join().expect("the stand-in engine thread finished");
        let outcome = outcome.unwrap_or_else(|_| {
            panic!("infer was still blocked after {give_up:?} against an engine that never reads")
        });
        (outcome, took)
    }

    #[test]
    fn an_engine_that_accepts_and_never_reads_fails_the_take_instead_of_hanging_it() {
        // The engine's end of the connection is full and nothing drains it, so
        // `write_all` blocks. With only a read timeout set it blocked for good.
        let (outcome, took) = infer_against_a_wedged_engine(
            true,
            vec![0u8; 1024],
            Duration::from_millis(300),
            Duration::from_secs(10),
        );
        let err = outcome.expect_err("an engine that never reads cannot have answered");
        assert!(err.starts_with("cannot send the audio"), "{err}");
        assert!(took < Duration::from_secs(5), "took {took:?} against a 300 ms timeout");
    }

    #[test]
    fn an_engine_that_takes_the_audio_and_never_answers_fails_the_take_too() {
        // The read side of the same timeout, so it stays pinned alongside it.
        let (outcome, took) = infer_against_a_wedged_engine(
            false,
            b"RIFFfake".to_vec(),
            Duration::from_millis(300),
            Duration::from_secs(10),
        );
        let err = outcome.expect_err("it never answered");
        assert!(err.starts_with("no answer from the speech engine"), "{err}");
        assert!(took < Duration::from_secs(5), "took {took:?} against a 300 ms timeout");
    }

    #[test]
    fn staleness_covers_every_combination() {
        let (m, p) = ("ggml-base.en.bin", "Delivery Console.");
        assert_eq!(engine_is_stale(m, p, m, p), None, "same model, same prompt");
        assert_eq!(
            engine_is_stale(m, p, "ggml-small.en.bin", p),
            Some(Stale::Model),
            "the model differs"
        );
        assert_eq!(engine_is_stale(m, p, m, "Console."), Some(Stale::Prompt), "the prompt differs");
        assert_eq!(
            engine_is_stale(m, p, "ggml-small.en.bin", "Console."),
            Some(Stale::Both),
            "both differ"
        );
    }

    #[test]
    fn a_changed_model_alone_is_stale() {
        // The regression row (AC-35): `ensure` used to compare only the
        // prompt, so choosing tiny.en while base.en ran changed nothing until
        // the shell was restarted.
        assert_eq!(
            engine_is_stale("ggml-base.en.bin", "same prompt", "ggml-tiny.en.bin", "same prompt"),
            Some(Stale::Model)
        );
    }

    #[test]
    fn a_fallback_that_is_already_running_is_not_stale() {
        // small.en is wanted but not installed, so the resolver gives the only
        // model there is. Compared as the resolved file name, an engine that
        // is already running that file is left alone instead of restarted
        // into the same thing on every take.
        let root = scratch_models("fallback-stale", &[("ggml-tiny.en.bin", 5)]);
        let (path, fell_back) = resolve_model(&root, "small.en").expect("tiny.en is installed");
        assert!(fell_back);
        assert_eq!(
            engine_is_stale("ggml-tiny.en.bin", "p", &file_name_of(&path), "p"),
            None
        );
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn model_file_prefers_the_named_file_over_the_smallest() {
        // Tiny is smaller, but base was asked for.
        let root = scratch_models("named", &[("ggml-tiny.en.bin", 5), ("ggml-base.en.bin", 10)]);
        let (path, fell_back) = resolve_model(&root, "base.en").expect("base.en is installed");
        assert_eq!(file_name_of(&path), "ggml-base.en.bin");
        assert!(!fell_back, "the named file is a choice, not a fallback");
        let (path, _) = resolve_model(&root, "  base.en ").expect("a padded name still resolves");
        assert_eq!(file_name_of(&path), "ggml-base.en.bin");
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn model_file_falls_back_to_the_smallest_when_the_named_one_is_absent() {
        let root = scratch_models("smallest", &[("ggml-base.en.bin", 10), ("ggml-tiny.en.bin", 5)]);
        let (path, fell_back) = resolve_model(&root, "small.en").expect("something is installed");
        assert_eq!(file_name_of(&path), "ggml-tiny.en.bin", "smallest first");
        assert!(fell_back, "the named file is absent, so this is a fallback");
        // No preference at all is the smallest too, but not a fallback.
        let (path, fell_back) = resolve_model(&root, "").expect("something is installed");
        assert_eq!(file_name_of(&path), "ggml-tiny.en.bin");
        assert!(!fell_back, "a blank preference has nothing to fall back from");
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn no_model_at_all_resolves_to_nothing() {
        let root = scratch_models("none", &[]);
        assert!(resolve_model(&root, "base.en").is_none());
        let absent = std::env::temp_dir().join("t031-no-such-root");
        assert!(resolve_model(&absent, "base.en").is_none());
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn the_fallback_warning_is_given_once_per_distinct_pair() {
        let mut last = None;
        assert!(should_warn(&mut last, Some(("small.en", "ggml-tiny.en.bin"))), "first time");
        for _ in 0..5 {
            assert!(
                !should_warn(&mut last, Some(("small.en", "ggml-tiny.en.bin"))),
                "the same pair again is not news"
            );
        }
        assert!(
            should_warn(&mut last, Some(("medium.en", "ggml-tiny.en.bin"))),
            "a different wanted model is"
        );
        assert!(
            should_warn(&mut last, Some(("medium.en", "ggml-base.en.bin"))),
            "so is a different fallback"
        );
        assert!(!should_warn(&mut last, Some(("medium.en", "ggml-base.en.bin"))));
    }

    #[test]
    fn finding_the_named_model_lets_a_later_fallback_warn_again() {
        let mut last = None;
        assert!(should_warn(&mut last, Some(("small.en", "ggml-tiny.en.bin"))));
        assert!(!should_warn(&mut last, None), "installed: nothing to warn about");
        assert!(
            should_warn(&mut last, Some(("small.en", "ggml-tiny.en.bin"))),
            "deleted again: that is a change"
        );
    }

    #[test]
    fn model_files_follow_the_ggml_contract() {
        // AC-2, Rust half. The console downloader writes exactly these names
        // (and `.part` / `.manifest.json` beside them while it works); the
        // shell must resolve what it writes and ignore what it is still
        // writing.
        assert_eq!(model_filename("base.en"), "ggml-base.en.bin");
        assert_eq!(model_filename("tiny.en"), "ggml-tiny.en.bin");
        let root = scratch_models(
            "contract",
            &[
                ("ggml-small.en.bin", 50),
                ("ggml-tiny.en.bin.part", 1),
                ("ggml-tiny.en.bin.manifest.json", 1),
                ("README.txt", 1),
                ("tiny.en.bin", 1),
            ],
        );
        let (path, _) = resolve_model(&root, "").expect("one real model is installed");
        assert_eq!(file_name_of(&path), "ggml-small.en.bin", "only ggml-*.bin counts");
        let (path, fell_back) = resolve_model(&root, "tiny.en").expect("falls back");
        assert_eq!(file_name_of(&path), "ggml-small.en.bin", "a .part is not an installed model");
        assert!(fell_back);
        let _ = std::fs::remove_dir_all(&root);
    }

    // ---- the live swap (T-031-04). Every test blocks on channels or on the
    // ---- slot's own condvar; none of them waits for a duration to pass.

    const PROMPTLY: Duration = Duration::from_millis(100);

    /// Call `f` on its own thread and return its result and how long it took,
    /// failing unless that is under `PROMPTLY`. A call that is stuck (the
    /// slot's lock held across a start) fails the test after 3 s with that
    /// reason, rather than hanging the test run.
    fn promptly<T: Send + 'static>(what: &str, f: impl FnOnce() -> T + Send + 'static) -> (T, Duration) {
        let (tx, rx) = channel();
        let started = Instant::now();
        std::thread::spawn(move || {
            let _ = tx.send(f());
        });
        let out = rx.recv_timeout(Duration::from_secs(3)).unwrap_or_else(|_| {
            panic!("{what} did not return in 3 s: the slot's lock is held across a start")
        });
        let took = started.elapsed();
        assert!(took < PROMPTLY, "{what} took {took:?}");
        (out, took)
    }

    /// A slot serving base.en, with the replacement for tiny.en started and
    /// blocked inside the spawner. Returns the old lease too: the take that
    /// asked for tiny.en and was given the old engine.
    fn swap_in_flight(rig: &Rig) -> (Lease, Sender<()>) {
        let old = rig.port(&base()).expect("base.en starts");
        assert_eq!(old, 9001);
        let (entered, release) = rig.block_next_spawn();
        let (slot, backend) = (rig.slot.clone(), rig.backend.clone());
        let (lease, _) = promptly("the take that triggers the swap", move || {
            slot.ensure_with(&tiny(), &backend).expect("the old engine serves the take")
        });
        entered.recv_timeout(WAIT).expect("the replacement's spawn was entered");
        (lease, release)
    }

    #[test]
    fn two_concurrent_takes_start_one_replacement_and_the_old_one_stops_after_it_answers() {
        // AC-37.
        let rig = Rig::new();
        assert_eq!(rig.port(&base()), Ok(9001));
        rig.fake.push(Step::Silent); // the replacement starts but does not answer yet

        let ports: Vec<u16> = std::thread::scope(|scope| {
            let takes: Vec<_> = (0..2).map(|_| scope.spawn(|| rig.port(&tiny()))).collect();
            takes.into_iter().map(|t| t.join().unwrap().expect("a take is served")).collect()
        });
        assert_eq!(ports, vec![9001, 9001], "both takes were given the old engine");

        rig.world.wait_event("spawn:9002:ggml-tiny.en.bin:p");
        assert_eq!(rig.world.spawns(), 2, "the old engine and ONE replacement");
        assert_eq!(rig.world.kills(9001), 0, "the old engine is not stopped while the new one is silent");
        assert_eq!(rig.slot.loaded_model(), "ggml-base.en.bin", "still the old model");

        rig.world.answer(9002);
        assert!(rig.slot.wait_idle(WAIT), "the swap finished");

        let spawned = rig.world.position("spawn:9002:ggml-tiny.en.bin:p").unwrap();
        let answered = rig.world.position("ready:9002").unwrap();
        let stopped = rig.world.position("kill:9001").unwrap();
        assert!(spawned < answered, "{:?}", rig.world.events());
        assert!(answered < stopped, "the old process stops only after the new one answers: {:?}", rig.world.events());
        assert_eq!(rig.slot.loaded_model(), "ggml-tiny.en.bin");
        assert_eq!(rig.port(&tiny()), Ok(9002), "new takes use the new engine");
        assert_eq!(rig.world.spawns(), 2, "still one replacement");
    }

    #[test]
    fn while_a_spawn_is_blocked_the_slot_still_answers_promptly() {
        // AC-38, the mandatory proof that the engine lock is not held across
        // the start: `bridge.rs` calls both of these for `/health`, on its one
        // thread.
        let rig = Rig::new();
        let (_old, release) = swap_in_flight(&rig);

        let mut worst = Duration::ZERO;
        for _ in 0..20 {
            let slot = rig.slot.clone();
            let (model, took) = promptly("loaded_model()", move || slot.loaded_model());
            assert_eq!(model, "ggml-base.en.bin", "the old engine is still the loaded one");
            worst = worst.max(took);
            let slot = rig.slot.clone();
            let (running, took) = promptly("running()", move || slot.running());
            assert!(running);
            worst = worst.max(took);
        }
        assert!(worst < PROMPTLY, "worst call took {worst:?} with the spawn blocked");

        release.send(()).unwrap();
        assert!(rig.slot.wait_idle(WAIT));
    }

    #[test]
    fn a_take_during_a_blocked_swap_is_given_the_old_port_promptly() {
        // AC-37/38: a take never waits on a swap.
        let rig = Rig::new();
        let (old, release) = swap_in_flight(&rig);
        assert_eq!(old.port, 9001);

        for _ in 0..5 {
            let (slot, backend) = (rig.slot.clone(), rig.backend.clone());
            let (lease, _) = promptly("a take during the swap", move || {
                slot.ensure_with(&tiny(), &backend).expect("served")
            });
            assert_eq!(lease.port, 9001, "the OLD port, while the replacement starts");
        }
        assert_eq!(rig.world.spawns(), 2, "no second replacement was started");

        release.send(()).unwrap();
        assert!(rig.slot.wait_idle(WAIT));
        assert_eq!(rig.port(&tiny()), Ok(9002));
    }

    #[test]
    fn a_failed_replacement_leaves_the_old_engine_serving() {
        // AC-39: no `transcribe` error because of a swap.
        let rig = Rig::new();
        assert_eq!(rig.port(&base()), Ok(9001));
        rig.fake.push(Step::Fail("cannot load ggml-tiny.en.bin"));

        assert_eq!(rig.port(&tiny()), Ok(9001), "the take is served by the old engine");
        assert!(rig.slot.wait_idle(WAIT));

        assert!(rig.slot.swap_error().contains("cannot load"), "{:?}", rig.slot.swap_error());
        assert_eq!(rig.port(&tiny()), Ok(9001), "still Ok(old port), not an error");
        assert!(rig.slot.running());
        assert_eq!(rig.slot.loaded_model(), "ggml-base.en.bin");
        assert_eq!(rig.world.kills(9001), 0, "the old engine was not touched");
    }

    #[test]
    fn a_failed_replacement_is_not_retried_on_every_take() {
        let rig = Rig::new();
        assert_eq!(rig.port(&base()), Ok(9001));
        rig.fake.push(Step::Fail("bad file"));
        assert_eq!(rig.port(&tiny()), Ok(9001));
        assert!(rig.slot.wait_idle(WAIT));
        assert_eq!(rig.world.spawns(), 2, "the old engine and the one failed attempt");

        for _ in 0..5 {
            assert_eq!(rig.port(&tiny()), Ok(9001));
            assert!(rig.slot.wait_idle(WAIT));
        }
        assert_eq!(rig.world.spawns(), 2, "five more takes started nothing");
        assert!(rig.slot.swap_error().contains("bad file"));
    }

    #[test]
    fn a_changed_request_after_a_failure_is_tried_once() {
        let rig = Rig::new();
        assert_eq!(rig.port(&base()), Ok(9001));
        rig.fake.push(Step::Fail("bad file"));
        assert_eq!(rig.port(&tiny()), Ok(9001));
        assert!(rig.slot.wait_idle(WAIT));
        assert_eq!(rig.world.spawns(), 2);

        // A different model: one attempt, and it works.
        let small = want("ggml-small.en.bin", "p");
        assert_eq!(rig.port(&small), Ok(9001), "served by the old engine meanwhile");
        assert!(rig.slot.wait_idle(WAIT));
        assert_eq!(rig.world.spawns(), 3, "exactly one attempt for the new key");
        assert_eq!(rig.slot.swap_error(), "", "a success clears the error");
        assert_eq!(rig.slot.loaded_model(), "ggml-small.en.bin");
        assert_eq!(rig.port(&small), Ok(9003));
        assert_eq!(rig.world.spawns(), 3);

        // The same model with a different prompt is a different request too.
        rig.fake.push(Step::Fail("bad prompt"));
        let prompted = want("ggml-small.en.bin", "q");
        assert_eq!(rig.port(&prompted), Ok(9003));
        assert!(rig.slot.wait_idle(WAIT));
        assert_eq!(rig.world.spawns(), 4);
        assert_eq!(rig.port(&prompted), Ok(9003));
        assert!(rig.slot.wait_idle(WAIT));
        assert_eq!(rig.world.spawns(), 4, "not retried");
        let changed = want("ggml-small.en.bin", "r");
        assert_eq!(rig.port(&changed), Ok(9003));
        assert!(rig.slot.wait_idle(WAIT));
        assert_eq!(rig.world.spawns(), 5, "a changed prompt clears the memory of the failure");
    }

    #[test]
    fn with_no_engine_the_starter_blocks_but_the_slot_answers_and_a_second_caller_waits() {
        let rig = Rig::new();
        let (entered, release) = rig.block_next_spawn();

        std::thread::scope(|scope| {
            // Moved in, so a failed assertion below drops it, which lets the
            // blocked spawn go and the scope join instead of hanging.
            let release = release;
            let starter = scope.spawn(|| rig.port(&base()));
            entered.recv_timeout(WAIT).expect("the starter is inside the spawner");

            // The starter holds no lock: the slot answers at once.
            let mut worst = Duration::ZERO;
            for _ in 0..20 {
                let slot = rig.slot.clone();
                let (model, took) = promptly("loaded_model()", move || slot.loaded_model());
                assert_eq!(model, "", "nothing is loaded yet");
                worst = worst.max(took);
                let slot = rig.slot.clone();
                let (running, took) = promptly("running()", move || slot.running());
                assert!(!running);
                worst = worst.max(took);
            }
            assert!(worst < PROMPTLY, "worst call took {worst:?} with the first start blocked");

            let second = scope.spawn(|| rig.port(&base()));
            while rig.slot.waiters() < 1 {
                std::thread::yield_now();
            }
            release.send(()).unwrap();

            let a = starter.join().unwrap().expect("the starter is served");
            let b = second.join().unwrap().expect("the waiter is served");
            assert_eq!(a, b, "the waiter got the same port");
        });
        assert_eq!(rig.world.spawns(), 1, "one start for both callers");
        assert_eq!(rig.slot.loaded_model(), "ggml-base.en.bin");
    }

    #[test]
    fn a_caller_that_waited_for_a_start_that_failed_gets_that_failure() {
        let rig = Rig::new();
        let (entered_tx, entered) = channel();
        let (release, release_rx) = channel();
        rig.fake.push(Step::Block {
            entered: entered_tx,
            release: release_rx,
            then_fail: Some("the model is corrupt"),
        });

        std::thread::scope(|scope| {
            let starter = scope.spawn(|| rig.port(&base()));
            entered.recv_timeout(WAIT).unwrap();
            let second = scope.spawn(|| rig.port(&base()));
            while rig.slot.waiters() < 1 {
                std::thread::yield_now();
            }
            release.send(()).unwrap();
            assert_eq!(starter.join().unwrap(), Err("the model is corrupt".into()));
            assert_eq!(second.join().unwrap(), Err("the model is corrupt".into()));
        });
        assert_eq!(rig.world.spawns(), 1, "the waiter did not start the same thing again");
    }

    #[test]
    fn a_replacement_that_never_answers_is_abandoned_and_the_old_engine_kept() {
        let rig = Rig::new();
        assert_eq!(rig.port(&base()), Ok(9001));
        rig.fake.set_timeout(Duration::from_millis(250));
        rig.fake.push(Step::Silent);

        assert_eq!(rig.port(&tiny()), Ok(9001), "the take is not held up");
        assert!(rig.slot.wait_idle(WAIT), "the injected timeout ended the attempt");

        assert!(rig.slot.swap_error().contains("did not start"), "{:?}", rig.slot.swap_error());
        assert_eq!(rig.world.kills(9002), 1, "the replacement that never answered is stopped");
        assert_eq!(rig.world.kills(9001), 0, "the old engine is kept");
        assert_eq!(rig.slot.loaded_model(), "ggml-base.en.bin");
        assert_eq!(rig.port(&tiny()), Ok(9001));
    }

    #[test]
    fn an_engine_that_died_is_replaced_synchronously() {
        let rig = Rig::new();
        assert_eq!(rig.port(&base()), Ok(9001));
        rig.world.dead.lock().unwrap().insert(9001);
        assert!(!rig.slot.running(), "the slot notices the process is gone");

        // Nothing to keep serving, so this take waits for the new engine.
        assert_eq!(rig.port(&base()), Ok(9002), "a new process on a new port");
        assert_eq!(rig.world.spawns(), 2);
        assert_eq!(rig.world.kills(9001), 1, "the dead one is cleared");
        assert_eq!(rig.slot.loaded_model(), "ggml-base.en.bin");
    }

    #[test]
    fn a_take_holding_the_old_engine_keeps_it_alive_until_it_lets_go() {
        // CR-36: killing at once would fail a take that is mid-inference.
        let rig = Rig::new();
        let mid_inference = rig.ensure(&base()).expect("the old engine");
        assert_eq!(mid_inference.port, 9001);

        assert_eq!(rig.port(&tiny()), Ok(9001));
        assert!(rig.slot.wait_idle(WAIT), "the replacement is published");
        assert_eq!(rig.slot.loaded_model(), "ggml-tiny.en.bin", "new takes use the new engine");
        assert_eq!(rig.world.kills(9001), 0, "the old engine is held by a take");

        drop(mid_inference);
        assert_eq!(rig.world.kills(9001), 1, "stopped once the last take let go");
        assert_eq!(rig.port(&tiny()), Ok(9002));
        assert_eq!(rig.world.kills(9002), 0);
    }

    #[test]
    fn shutdown_stops_a_retired_engine_a_take_is_still_holding() {
        let rig = Rig::new();
        let held = rig.ensure(&base()).expect("the old engine");
        assert_eq!(rig.port(&tiny()), Ok(9001));
        assert!(rig.slot.wait_idle(WAIT));
        assert_eq!(rig.world.kills(9001), 0);

        rig.slot.shutdown();
        assert_eq!(rig.world.kills(9001), 1, "the retired engine does not outlive the shell");
        assert_eq!(rig.world.kills(9002), 1, "nor does the current one");
        drop(held);
        assert_eq!(rig.world.kills(9001), 1, "the late drop does not stop it twice");
    }

    #[test]
    fn a_swap_that_finishes_after_shutdown_stops_what_it_started() {
        let rig = Rig::new();
        let (_old, release) = swap_in_flight(&rig);

        rig.slot.shutdown();
        assert_eq!(rig.world.kills(9001), 1, "shutdown stops the serving engine even while a take holds it");
        release.send(()).unwrap();
        assert!(rig.slot.wait_idle(WAIT));
        assert_eq!(rig.world.kills(9002), 1, "the replacement is not left running");
        assert_eq!(rig.slot.loaded_model(), "", "and nothing was published after shutdown");
    }

    #[test]
    fn a_prompt_only_change_takes_the_same_path() {
        let rig = Rig::new();
        assert_eq!(rig.port(&base()), Ok(9001));
        let reworded = want("ggml-base.en.bin", "q");

        assert_eq!(rig.port(&reworded), Ok(9001), "the old engine serves while the new one loads");
        assert!(rig.slot.wait_idle(WAIT));
        assert!(rig.world.position("spawn:9002:ggml-base.en.bin:q").is_some(), "{:?}", rig.world.events());
        assert!(
            rig.world.position("ready:9002").unwrap() < rig.world.position("kill:9001").unwrap(),
            "killed after, not before: {:?}",
            rig.world.events()
        );
        assert_eq!(rig.port(&reworded), Ok(9002));
    }

    #[test]
    fn prewarm_starts_the_replacement_only_when_there_is_something_to_replace() {
        let rig = Rig::new();
        rig.slot.prewarm_with(&tiny(), &rig.backend);
        assert!(rig.slot.wait_idle(WAIT));
        assert_eq!(rig.world.spawns(), 0, "no engine running: nothing is loaded for nobody");

        assert_eq!(rig.port(&base()), Ok(9001));
        rig.slot.prewarm_with(&base(), &rig.backend);
        assert!(rig.slot.wait_idle(WAIT));
        assert_eq!(rig.world.spawns(), 1, "the engine is already current");

        rig.slot.prewarm_with(&tiny(), &rig.backend);
        assert!(rig.slot.wait_idle(WAIT));
        assert_eq!(rig.world.spawns(), 2, "a stale engine gets its replacement in the background");
        assert_eq!(rig.slot.loaded_model(), "ggml-tiny.en.bin", "no take was needed");
    }

    #[test]
    fn a_swap_needs_something_to_swap_to() {
        // The model file was removed while base.en ran, and the prompt moved
        // on: no replacement can be started, and the old engine keeps serving.
        let rig = Rig::new();
        assert_eq!(rig.port(&base()), Ok(9001));
        let mut gone = want("ggml-base.en.bin", "q");
        gone.model = None;
        assert_eq!(rig.port(&gone), Ok(9001));
        assert!(rig.slot.wait_idle(WAIT));
        assert_eq!(rig.world.spawns(), 1);
    }
}

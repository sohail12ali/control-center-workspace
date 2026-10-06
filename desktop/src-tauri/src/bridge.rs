//! The loopback bridge: how the Python console asks the shell to do something
//! only a native process can.
//!
//! ## Why the shell listens, rather than the console pushing
//!
//! The console's tool thread is already blocking when it runs a tool call, so
//! a plain request/response is the shape that fits: `urllib` call, get an
//! answer, return it to the model. The alternative — the console queueing work
//! for the shell to long-poll — needs correlation ids, a queue, and a timeout
//! story, to solve a problem that does not exist on loopback.
//!
//! ## Auth, and what it is actually for
//!
//! The console itself has no authentication: it binds 127.0.0.1 and treats
//! "can run code as this user" as the trust boundary. The bearer token here is
//! not a stronger claim than that. It exists so that *another* local process —
//! a browser page doing a DNS-rebinding trick, a stray script — cannot drive
//! screen capture or the clipboard just by knowing the port. The token lives
//! in a file only this user can read, which is the same boundary the console
//! already relies on, and the decision log says so plainly rather than
//! implying this is real authentication.
//!
//! ## What is deliberately NOT here
//!
//! No approval logic. The console owns the "Permission needed" card, decides
//! whether a clipboard read may proceed, and only then calls. Duplicating that
//! judgement here would create two places for it to disagree, and the one in
//! the console is the one a human can see.

use std::io::Read;
use std::net::SocketAddr;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};

use serde_json::{json, Value};
use tiny_http::{Header, Request, Response, Server};

use crate::capture::{self, Target};
use crate::clipboard;
use crate::ocr;
use crate::tray_state::Event;
use crate::tts;
use crate::voice_test;
use crate::listen;
use crate::hands_free;
use crate::tray_state::Assistant;

/// Where the pointer file goes, relative to the repo root. The console reads
/// this to find us; nothing else advertises the port.
const POINTER_REL: &str = "console/.cache/desktop/bridge.json";

/// A request body larger than this is refused unread. Nothing legitimate here
/// is big — the largest is a clipboard write.
const MAX_BODY: usize = 1024 * 1024;

pub struct Bridge {
    pub base_url: String,
    pub pointer: PathBuf,
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

fn token() -> String {
    let mut buf = [0u8; 32];
    // A failure to seed would mean a predictable token, so fall back to
    // something unpredictable-ish and log it rather than shipping zeros.
    if getrandom::fill(&mut buf).is_err() {
        log::warn!("bridge: getrandom failed, falling back to a time-seeded token");
        let nanos = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_nanos())
            .unwrap_or(0);
        for (i, b) in buf.iter_mut().enumerate() {
            *b = ((nanos >> (i % 16)) as u8) ^ (i as u8);
        }
    }
    hex(&buf)
}

fn json_response(status: u16, body: Value) -> Response<std::io::Cursor<Vec<u8>>> {
    let header = Header::from_bytes(&b"Content-Type"[..], &b"application/json"[..])
        .expect("a literal header always parses");
    Response::from_string(body.to_string())
        .with_status_code(status)
        .with_header(header)
}

fn err(status: u16, code: &str, message: impl AsRef<str>) -> Response<std::io::Cursor<Vec<u8>>> {
    json_response(
        status,
        json!({"ok": false, "error": code, "message": message.as_ref()}),
    )
}

fn ok(mut body: Value) -> Response<std::io::Cursor<Vec<u8>>> {
    if let Some(map) = body.as_object_mut() {
        map.insert("ok".into(), Value::Bool(true));
    }
    json_response(200, body)
}

fn is_loopback(request: &Request) -> bool {
    match request.remote_addr() {
        Some(SocketAddr::V4(a)) => a.ip().is_loopback(),
        Some(SocketAddr::V6(a)) => a.ip().is_loopback(),
        None => false,
    }
}

fn bearer(request: &Request) -> Option<String> {
    for header in request.headers() {
        if header.field.equiv("Authorization") {
            let value = header.value.as_str();
            return value
                .strip_prefix("Bearer ")
                .map(|t| t.trim().to_string());
        }
    }
    None
}

/// Constant-time-ish comparison. The token is not a password and an attacker
/// on loopback has better options, but a length-and-content compare costs
/// nothing and avoids the habit of writing `==` on secrets.
fn token_matches(expected: &str, given: &str) -> bool {
    if expected.len() != given.len() {
        return false;
    }
    expected
        .bytes()
        .zip(given.bytes())
        .fold(0u8, |acc, (a, b)| acc | (a ^ b))
        == 0
}

fn read_body(request: &mut Request) -> Result<Value, String> {
    let len = request.body_length().unwrap_or(0);
    if len > MAX_BODY {
        return Err(format!("body is {len} bytes, over the {MAX_BODY} limit"));
    }
    let mut raw = String::new();
    request
        .as_reader()
        .take(MAX_BODY as u64)
        .read_to_string(&mut raw)
        .map_err(|e| format!("cannot read the body: {e}"))?;
    if raw.trim().is_empty() {
        return Ok(json!({}));
    }
    serde_json::from_str(&raw).map_err(|e| format!("body is not JSON: {e}"))
}

fn write_pointer(pointer: &Path, base_url: &str, token: &str) -> std::io::Result<()> {
    if let Some(parent) = pointer.parent() {
        std::fs::create_dir_all(parent)?;
    }
    let body = json!({
        "base_url": base_url,
        "token": token,
        "pid": std::process::id(),
        "started": std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_secs())
            .unwrap_or(0),
    });
    std::fs::write(pointer, body.to_string())
}

/// Start the bridge on an ephemeral loopback port and write the pointer file.
///
/// Returns once the socket is bound, so a caller can be sure the console will
/// find a live port in the pointer rather than racing it.
pub fn start(
    repo_root: &Path,
    assistant: Arc<Mutex<Assistant>>,
    console_url: String,
) -> Result<Bridge, String> {
    let server = Server::http("127.0.0.1:0")
        .map_err(|e| format!("cannot bind the bridge to loopback: {e}"))?;
    let port = match server.server_addr() {
        tiny_http::ListenAddr::IP(addr) => addr.port(),
        #[allow(unreachable_patterns)]
        other => return Err(format!("bridge bound to an unexpected address: {other:?}")),
    };
    let base_url = format!("http://127.0.0.1:{port}");
    let secret = token();
    let pointer = repo_root.join(POINTER_REL);

    write_pointer(&pointer, &base_url, &secret)
        .map_err(|e| format!("cannot write {}: {e}", pointer.display()))?;
    log::info!("bridge: listening on {base_url}, pointer at {}", pointer.display());

    let root = repo_root.to_path_buf();
    let url = console_url;
    std::thread::Builder::new()
        .name("bridge".into())
        .spawn(move || {
            for mut request in server.incoming_requests() {
                let response = route(&root, &secret, &assistant, &url, &mut request);
                if let Err(e) = request.respond(response) {
                    log::warn!("bridge: could not respond: {e}");
                }
            }
            log::info!("bridge: listener stopped");
        })
        .map_err(|e| format!("cannot start the bridge thread: {e}"))?;

    Ok(Bridge { base_url, pointer })
}

/// Remove the pointer so the console stops believing a dead shell is up.
pub fn clear_pointer(repo_root: &Path) {
    let pointer = repo_root.join(POINTER_REL);
    match std::fs::remove_file(&pointer) {
        Ok(()) => log::info!("bridge: pointer removed"),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}
        Err(e) => log::warn!("bridge: could not remove the pointer: {e}"),
    }
}

fn capabilities(repo_root: &Path) -> Value {
    json!({
        "capture": true,
        "windows": true,
        "clipboard_read": true,
        "clipboard_write": true,
        // Probed, not assumed: `ocr::available()` asks whether an engine
        // answers on THIS machine (a WinRT language pack, or tesseract on
        // PATH), because "the platform supports OCR" and "this box can OCR"
        // are different claims and the console repeats whichever it is told.
        "ocr": ocr::available(),
        // Probed, like `ocr`: whether a synthesiser answers on THIS machine.
        "speak": tts::available(),
        "speak_backend": tts::backend_name(),
        // Which neural voices are installed, so Settings can offer them
        // instead of asking someone to type a filename.
        "speak_voices": crate::piper::voices(repo_root),
        // Probed like the rest: a microphone AND an installed engine.
        "stt": listen::available(repo_root),
        "stt_model": crate::stt::model_name(repo_root),
        // The model file the engine is running right now (empty when none):
        // after a live swap this is what proves it took effect.
        "loaded_model": crate::stt::loaded_model(),
        // The installed voice the settings resolve to (null when none). Never
        // logs, so polling `/health` does not repeat the fallback warning.
        "speak_voice_in_use": crate::piper::voice_in_use(repo_root, &tts::chosen_voice()),
        "stt_hint": listen::hint(repo_root),
        // A wakeword recorded on THIS machine. Hands-free runs either way —
        // without one it falls back to transcribing every utterance — so this
        // says which of the two Settings should describe.
        "wake": crate::wake::available(repo_root),
        "wake_words": crate::wake::installed(repo_root),
        "wake_hint": crate::wake::hint(repo_root),
    })
}

/// Record one utterance of a wake phrase.
///
/// Deliberately not a `listen` take: nothing here is transcribed, gated,
/// dispatched or shown in the tray. It is a few seconds of audio going
/// straight to a file that will be built into a template — the shortest path
/// there is, and the one with the fewest ways to surprise someone who pressed
/// a button labelled "say it".
fn record_phrase() -> Result<Vec<u8>, String> {
    let mut mic = crate::audio::Mic::open()?;
    let take = mic.take(
        Arc::new(Mutex::new(false)),
        crate::audio::Limits {
            // A wake phrase is two or three words. A longer cap would just
            // record the room after someone had finished saying it, and a
            // template padded with silence matches silence.
            max_take: std::time::Duration::from_secs(3),
            trailing_silence: std::time::Duration::from_millis(500),
            first_pause: std::time::Duration::from_millis(500),
        },
    )?;
    if take.ending == crate::audio::Ending::NothingHeard {
        return Err("nothing heard - say the phrase once, right after pressing".into());
    }
    Ok(take.wav())
}

/// The body of `GET /listen/state`.
pub(crate) fn listen_state_json(repo_root: &Path) -> Value {
    json!({
        "listening": listen::listening(),
        "available": listen::available(repo_root),
        "hint": listen::hint(repo_root),
        "microphone": crate::audio::device_name(),
        "engine_running": crate::stt::running(),
        "model": crate::stt::loaded_model(),
        // Why the last model or prompt swap failed, empty when it did not.
        "swap_error": crate::stt::swap_error(),
        // The Settings "Test microphone" state: running, peak, device.
        "mic_test": voice_test::state_json(&voice_test::shell_state()),
        "hands_free": hands_free::running(),
        // Why it stopped, so a loop that ended by itself (time limit, a
        // microphone that went away) can say so instead of just going
        // quiet.
        "hands_free_stopped": hands_free::last_stop_reason(),
        // T-019. What the wake-word spotter can see, for the diagnostics
        // panel. Before this the only evidence a user had that listening
        // was working at all was a log file — which is why a broken wake
        // word went five takes without anyone being able to say why.
        "wake": {
            "installed": crate::wake::installed(repo_root),
            "available": crate::wake::available(repo_root),
            "hint": crate::wake::hint(repo_root),
            "score": crate::wake::last_score(),
            "level": crate::audio::level(),
            "fired": crate::wake::last_fired().map(|f| json!({
                "name": f.name, "score": f.score, "avg_score": f.avg_score,
            })),
        },
    })
}

/// One direction's verdict: what was asked for and what is in use. The only
/// matcher is `devices::resolve_name`; nothing else decides this (D-17).
fn verdict_json(v: &crate::devices::Verdict) -> Value {
    json!({
        "configured": v.configured,
        "resolved": v.resolved,
        "match": v.match_kind.as_str(),
        "fallback": v.fallback,
        "candidates": v.candidates,
    })
}

/// The body of `GET /audio/devices`: the names on offer, the OS defaults and,
/// per direction, the verdict for the shell's APPLIED preference.
pub(crate) fn devices_json(
    list: &crate::devices::DeviceList,
    input_pref: &str,
    output_pref: &str,
) -> Value {
    use crate::devices::{resolve_name, Direction};
    json!({
        "inputs": list.inputs,
        "outputs": list.outputs,
        "default_input": list.default_input,
        "default_output": list.default_output,
        "input": verdict_json(&resolve_name(Direction::Input, input_pref, list)),
        "output": verdict_json(&resolve_name(Direction::Output, output_pref, list)),
    })
}

/// `POST /audio/test/mic`: refused with 409 and the reason while the
/// microphone is busy, else started (answering at once).
fn mic_test_response(
    busy: Option<&str>,
    start: impl FnOnce() -> Result<(), String>,
) -> Response<std::io::Cursor<Vec<u8>>> {
    if let Some(why) = busy {
        return err(409, "busy", why);
    }
    match start() {
        Ok(()) => ok(json!({"started": true})),
        Err(e) => err(503, "unavailable", e),
    }
}

/// `POST /audio/test/speaker`: the output is resolved before anything plays,
/// so an unresolved one is a 503 with the reason.
fn speaker_test_response(
    start: impl FnOnce() -> Result<String, String>,
) -> Response<std::io::Cursor<Vec<u8>>> {
    match start() {
        Ok(device) => ok(json!({"playing": true, "device": device})),
        Err(e) => err(503, "unavailable", e),
    }
}

fn route(
    repo_root: &Path,
    secret: &str,
    assistant: &Arc<Mutex<Assistant>>,
    console_url: &str,
    request: &mut Request,
) -> Response<std::io::Cursor<Vec<u8>>> {
    if !is_loopback(request) {
        log::warn!("bridge: refused a non-loopback peer {:?}", request.remote_addr());
        return err(403, "forbidden", "the bridge answers loopback only");
    }

    let url = request.url().to_string();
    let path = url.split('?').next().unwrap_or("/").trim_end_matches('/');
    let path = if path.is_empty() { "/" } else { path };
    let method = request.method().as_str().to_string();

    // `/health` is the one unauthenticated route: the console needs to tell
    // "no shell running" from "wrong token", and a 401 on a liveness probe
    // would make a stale pointer indistinguishable from a real problem.
    if path == "/health" {
        return ok(json!({
            "version": env!("CARGO_PKG_VERSION"),
            "pid": std::process::id(),
            "caps": capabilities(repo_root),
        }));
    }

    match bearer(request) {
        Some(given) if token_matches(secret, &given) => {}
        Some(_) => return err(401, "unauthorized", "that bearer token is not this shell's"),
        None => return err(401, "unauthorized", "a bearer token is required"),
    }

    match (method.as_str(), path) {
        ("GET", "/state") => {
            let a = assistant.lock().expect("the tray state mutex is never poisoned");
            ok(json!({
                "state": a.state().as_str(),
                "muted": a.muted(),
                "needs_approval": a.needs_approval(),
                "listen_paused": a.listen_paused(),
            }))
        }
        ("GET", "/monitors") => match capture::list_monitors() {
            Ok(monitors) => ok(json!({"monitors": monitors})),
            Err(e) => err(500, "unavailable", e),
        },
        ("GET", "/windows") => match capture::list_windows() {
            Ok(windows) => ok(json!({"windows": windows})),
            Err(e) => err(500, "unavailable", e),
        },
        ("GET", "/clipboard/peek") => match clipboard::peek() {
            Ok(p) => ok(json!({"clipboard": p})),
            Err(e) => err(500, "unavailable", e),
        },
        ("POST", "/clipboard/read") => match clipboard::read_text() {
            Ok(text) => ok(json!({"text": text})),
            Err(e) => err(500, "unavailable", e),
        },
        ("POST", "/clipboard/write") => {
            let body = match read_body(request) {
                Ok(v) => v,
                Err(e) => return err(400, "bad_request", e),
            };
            let text = body.get("text").and_then(Value::as_str).unwrap_or("");
            match clipboard::write_text(text) {
                Ok(n) => ok(json!({"chars": n})),
                Err(e) => err(500, "unavailable", e),
            }
        }
        ("POST", "/listen") => {
            let body = match read_body(request) {
                Ok(v) => v,
                Err(e) => return err(400, "bad_request", e),
            };
            let mode = body.get("mode").and_then(Value::as_str).unwrap_or("start");
            match mode {
                "cancel" | "release" | "stop" => {
                    listen::release();
                    ok(json!({"listening": false}))
                }
                "start" | "short_take" => {
                    if !listen::available(repo_root) {
                        return err(503, "unavailable", listen::hint(repo_root));
                    }
                    if listen::listening() {
                        return err(409, "busy", "already listening");
                    }
                    // The take runs on its own thread: recording plus
                    // transcription is seconds, and holding the response open
                    // would time out the caller for no benefit. The transcript
                    // arrives at the assistant by itself.
                    let root = repo_root.to_path_buf();
                    let shared = assistant.clone();
                    let url = console_url.to_string();
                    let spawned = std::thread::Builder::new()
                        .name("listen-bridge".into())
                        .spawn(move || match listen::take(&root, &shared, &url) {
                            Ok(text) => log::info!("listen: sent {text:?}"),
                            Err(e) => log::info!("listen: {e}"),
                        });
                    match spawned {
                        Ok(_) => ok(json!({"listening": true})),
                        Err(e) => err(500, "internal", format!("cannot start a take: {e}")),
                    }
                }
                // Always-on listening. A separate mode rather than a separate
                // route: from the caller's side this is still "start or stop
                // listening", and the difference is how long it lasts.
                "hands_free" => {
                    if !listen::available(repo_root) {
                        return err(503, "unavailable", listen::hint(repo_root));
                    }
                    let policy = hands_free::fetch_policy(console_url);
                    match hands_free::start(
                        repo_root,
                        assistant.clone(),
                        console_url.to_string(),
                        policy,
                    ) {
                        Ok(()) => ok(json!({"hands_free": true})),
                        Err(e) => err(409, "busy", e),
                    }
                }
                "hands_free_off" => {
                    hands_free::stop("asked to stop");
                    ok(json!({"hands_free": false}))
                }
                other => err(400, "bad_request", format!("unknown listen mode {other:?}")),
            }
        }
        ("GET", "/listen/state") => ok(listen_state_json(repo_root)),
        ("GET", "/audio/devices") => {
            let list = crate::devices::refresh();
            ok(devices_json(
                &list,
                &crate::devices::PREFS.input_preference(),
                &crate::devices::PREFS.output_preference(),
            ))
        }
        ("POST", "/audio/test/mic") => mic_test_response(
            voice_test::refuse_reason(
                listen::take_in_progress(),
                hands_free::running(),
                voice_test::running(&voice_test::shell_state()),
            ),
            voice_test::start_mic_test,
        ),
        ("POST", "/audio/test/speaker") => speaker_test_response(voice_test::start_speaker_test),
        // The console saved a setting and is telling us. Answered AT ONCE and
        // applied on a thread of its own: this bridge handles one request at a
        // time, and the settings fetch it implies stalls for ~3 seconds one
        // request in fifteen (`console_settings.rs`). Doing the fetch here would
        // freeze every other bridge call, and the console only waits one second
        // for this answer anyway (T-031 D-15).
        ("POST", "/settings/refresh") => {
            let root = repo_root.to_path_buf();
            let url = console_url.to_string();
            let spawned = std::thread::Builder::new()
                .name("settings-refresh".into())
                .spawn(move || {
                    let _ = listen::refresh_settings(&root, &url);
                });
            match spawned {
                Ok(_) => ok(json!({"applying": true})),
                Err(e) => err(500, "internal", format!("cannot start the refresh: {e}")),
            }
        }
        // -- recording a wake word ------------------------------------------
        //
        // Three steps, deliberately: say it, say it again, build. A phrase
        // recorded once is a template of one reading of it, and the detector
        // is only as forgiving as the recordings it was given.
        ("POST", "/wake/sample") => {
            let body = match read_body(request) {
                Ok(v) => v,
                Err(e) => return err(400, "bad_request", e),
            };
            let name = body.get("name").and_then(Value::as_str).unwrap_or("").to_string();
            if crate::wake::sanitise(&name).is_empty() {
                return err(400, "bad_request", "say what the wake word is called");
            }
            match record_phrase() {
                Ok(wav) => match crate::wake::save_sample(repo_root, &name, &wav) {
                    Ok(count) => ok(json!({
                        "samples": count,
                        "enough": count >= crate::wake::MIN_SAMPLES,
                    })),
                    Err(e) => err(500, "internal", e),
                },
                Err(e) => err(503, "unavailable", e),
            }
        }
        ("POST", "/wake/train") => {
            let body = match read_body(request) {
                Ok(v) => v,
                Err(e) => return err(400, "bad_request", e),
            };
            let name = body.get("name").and_then(Value::as_str).unwrap_or("");
            let recordings = crate::wake::samples(repo_root, name);
            match crate::wake::train(repo_root, name, &recordings, None, None) {
                Ok(path) => {
                    crate::wake::clear_samples(repo_root, name);
                    ok(json!({
                        "wakeword": path.file_name().unwrap_or_default().to_string_lossy(),
                        "installed": crate::wake::installed(repo_root),
                    }))
                }
                Err(e) => err(400, "bad_request", e),
            }
        }
        ("POST", "/wake/forget") => {
            let body = match read_body(request) {
                Ok(v) => v,
                Err(e) => return err(400, "bad_request", e),
            };
            let name = body.get("name").and_then(Value::as_str).unwrap_or("");
            match crate::wake::forget(repo_root, name) {
                Ok(()) => ok(json!({"installed": crate::wake::installed(repo_root)})),
                Err(e) => err(500, "internal", e),
            }
        }
        ("POST", "/speak") => {
            let body = match read_body(request) {
                Ok(v) => v,
                Err(e) => return err(400, "bad_request", e),
            };
            let text = body.get("text").and_then(Value::as_str).unwrap_or("");
            // Voice and speed: what the request names wins (Preview speaks a
            // choice before it is saved), anything it leaves out comes from the
            // console's settings, read fresh so a change on the Settings tab
            // takes effect on the next thing spoken, not the next launch.
            let settings = crate::console_settings::all(console_url);
            let (voice, rate) = tts::speak_params(&settings, &body);
            tts::choose(&tts::speak_params(&settings, &json!({})).0);
            tts::configure(repo_root, &voice, rate);
            match tts::speak(text) {
                Ok(chars) => {
                    // The tray shows speaking as soon as the utterance
                    // starts, not when the console decides it should: the
                    // icon and the sound come from the same event.
                    if chars > 0 {
                        note(assistant, Event::SpeakStart);
                    }
                    ok(json!({"chars": chars, "backend": tts::backend_name()}))
                }
                Err(e) => err(500, "unavailable", e),
            }
        }
        ("POST", "/speak/stop") => {
            let was_speaking = tts::stop();
            note(assistant, Event::SpeakStop);
            ok(json!({"stopped": was_speaking}))
        }
        ("GET", "/speak/state") => {
            // Lets the console drive the tray out of the speaking state
            // without holding a request open for the length of the speech.
            let done = tts::finished();
            if done {
                note(assistant, Event::SpeakStop);
            }
            ok(json!({"speaking": !done}))
        }
        ("POST", "/ocr") => {
            let body = match read_body(request) {
                Ok(v) => v,
                Err(e) => return err(400, "bad_request", e),
            };
            // A capture id, never a free path: the id comes from a model's
            // tool call, and `path_for` is what stops `../../.env` being
            // passed off as a screenshot to read text out of.
            let capture_id = match body.get("capture_id").and_then(Value::as_str) {
                Some(id) if !id.trim().is_empty() => id,
                _ => return err(400, "bad_request", "OCR needs a capture_id"),
            };
            let path = match capture::path_for(repo_root, capture_id) {
                Ok(p) => p,
                Err(e) => return err(404, "not_found", e),
            };
            match ocr::recognize(&path) {
                Ok(result) => ok(json!({"ocr": result})),
                Err(e) => err(500, "unavailable", e),
            }
        }
        ("POST", "/capture") => {
            let body = match read_body(request) {
                Ok(v) => v,
                Err(e) => return err(400, "bad_request", e),
            };
            let target = match parse_target(&body) {
                Ok(t) => t,
                Err(e) => return err(400, "bad_request", e),
            };
            let max_side = body
                .get("max_side")
                .and_then(Value::as_u64)
                .map(|v| v as u32)
                .unwrap_or(capture::DEFAULT_MAX_SIDE);
            match capture::capture(repo_root, target, max_side) {
                Ok((info, where_from)) => {
                    // After the pixels are grabbed, never before: a flash
                    // drawn first would be in the screenshot.
                    crate::shutter::fire(where_from);
                    ok(json!({"capture": info}))
                }
                Err(e) => err(500, "unavailable", e),
            }
        }
        ("GET", _) | ("POST", _) => err(404, "not_found", format!("no route {method} {path}")),
        _ => err(405, "bad_request", format!("{method} is not used here")),
    }
}

/// Fold one event into the shared tray state.
///
/// The tray's own repainting is `tray_link`'s job — it watches the console's
/// stream. This exists for the things only the shell knows, like "the
/// synthesiser actually started", which no console event can report.
fn note(assistant: &Arc<Mutex<Assistant>>, event: Event) {
    if let Ok(mut a) = assistant.lock() {
        a.apply(event);
    }
}

fn parse_target(body: &Value) -> Result<Target, String> {
    let target = body
        .get("target")
        .and_then(Value::as_str)
        .unwrap_or("screen");
    match target {
        "screen" => Ok(Target::Screen),
        "monitor" => body
            .get("monitor_id")
            .and_then(Value::as_u64)
            .map(|id| Target::Monitor(id as u32))
            .ok_or_else(|| "a monitor capture needs monitor_id".to_string()),
        "window" => body
            .get("window_title")
            .and_then(Value::as_str)
            .filter(|s| !s.trim().is_empty())
            .map(|t| Target::Window(t.to_string()))
            .ok_or_else(|| "a window capture needs window_title".to_string()),
        "region" => {
            let get = |k: &str| body.get(k).and_then(Value::as_u64).map(|v| v as u32);
            match (get("x"), get("y"), get("width"), get("height")) {
                (Some(x), Some(y), Some(width), Some(height)) => {
                    Ok(Target::Region { x, y, width, height })
                }
                _ => Err("a region capture needs x, y, width and height".into()),
            }
        }
        other => Err(format!("unknown capture target {other:?}")),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_token_matches_only_itself() {
        let t = token();
        assert!(token_matches(&t, &t));
        assert!(!token_matches(&t, "short"));
        assert!(!token_matches(&t, &t[..t.len() - 1]));
        let mut flipped = t.clone();
        flipped.replace_range(0..1, if t.starts_with('a') { "b" } else { "a" });
        assert!(!token_matches(&t, &flipped));
    }

    #[test]
    fn tokens_are_long_and_not_repeated() {
        let (a, b) = (token(), token());
        assert_eq!(a.len(), 64, "32 bytes as hex");
        assert_ne!(a, b);
    }

    #[test]
    fn the_pointer_carries_what_the_console_needs_to_find_us() {
        let dir = std::env::temp_dir().join(format!("t005-ptr-{}", std::process::id()));
        let pointer = dir.join("bridge.json");
        write_pointer(&pointer, "http://127.0.0.1:1234", "abc").expect("write");
        let raw = std::fs::read_to_string(&pointer).expect("read");
        let v: Value = serde_json::from_str(&raw).expect("json");
        assert_eq!(v["base_url"], "http://127.0.0.1:1234");
        assert_eq!(v["token"], "abc");
        assert!(v["pid"].as_u64().is_some());
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn every_capture_target_shape_is_understood() {
        assert!(matches!(parse_target(&json!({})), Ok(Target::Screen)));
        assert!(matches!(
            parse_target(&json!({"target": "screen"})),
            Ok(Target::Screen)
        ));
        assert!(matches!(
            parse_target(&json!({"target": "monitor", "monitor_id": 3})),
            Ok(Target::Monitor(3))
        ));
        assert!(matches!(
            parse_target(&json!({"target": "window", "window_title": "Notepad"})),
            Ok(Target::Window(_))
        ));
        assert!(matches!(
            parse_target(&json!({"target": "region", "x": 1, "y": 2, "width": 3, "height": 4})),
            Ok(Target::Region { .. })
        ));
    }

    #[test]
    fn an_incomplete_target_is_rejected_with_a_reason() {
        // The model fills these in, so the message has to tell it what is
        // missing rather than just failing.
        for (body, want) in [
            (json!({"target": "monitor"}), "monitor_id"),
            (json!({"target": "window"}), "window_title"),
            (json!({"target": "window", "window_title": "  "}), "window_title"),
            (json!({"target": "region", "x": 1}), "width"),
            (json!({"target": "nonsense"}), "unknown capture target"),
        ] {
            let e = parse_target(&body).unwrap_err();
            assert!(e.contains(want), "{body} -> {e}");
        }
    }

    #[test]
    fn capabilities_never_claim_what_is_not_built() {
        let caps = capabilities(&std::env::temp_dir());
        assert_eq!(caps["stt"], false, "speech-to-text lands later in T-006");
        // `speak` and `ocr` are PROBED, so these assert they agree with the
        // probe rather than pinning a constant — the point of those fields is
        // that they describe this machine.
        assert_eq!(caps["speak"], crate::tts::available());
        assert_eq!(caps["capture"], true);
        // OCR is PROBED, so this asserts it agrees with the probe rather than
        // pinning a constant — the point of the field is that it tells the
        // truth about this machine.
        assert_eq!(caps["ocr"], crate::ocr::available());
    }

    #[test]
    fn ocr_needs_a_capture_id_not_a_path() {
        // The id is the confinement boundary: a free path would let a tool
        // call read text out of any file on disk.
        let body = json!({"path": "../../.env"});
        assert!(body.get("capture_id").is_none(),
                "a caller cannot smuggle a path in place of an id");
    }

    // -- real requests against a real bridge (T-031) ------------------------
    //
    // A route is only tested when something asks it over a socket: the handler
    // is private, takes a live `Request`, and the parts most likely to be wrong
    // (auth, status codes, the response arriving at all) sit around it.

    use std::io::Write as _;
    use std::net::TcpStream;
    use std::sync::atomic::{AtomicUsize, Ordering};
    use std::time::{Duration, Instant};

    /// A real `bridge::start` on a temp repo root: its own random port, its own
    /// token, and a pointer file that is NOT the repo's (so a test never
    /// repoints the running app's console). Dropped, it removes the root; the
    /// listener thread ends with the test process.
    struct Loopback {
        port: u16,
        token: String,
        root: PathBuf,
    }

    impl Loopback {
        fn start(console_url: &str) -> Loopback {
            static NEXT: AtomicUsize = AtomicUsize::new(0);
            let root = std::env::temp_dir().join(format!(
                "t031-bridge-{}-{}",
                std::process::id(),
                NEXT.fetch_add(1, Ordering::SeqCst)
            ));
            let bridge = start(
                &root,
                Arc::new(Mutex::new(Assistant::default())),
                console_url.to_string(),
            )
            .expect("the bridge binds to loopback");
            assert!(bridge.pointer.starts_with(&root), "the pointer is under the temp root");
            let pointer: Value = serde_json::from_str(
                &std::fs::read_to_string(&bridge.pointer).expect("the pointer was written"),
            )
            .expect("the pointer is JSON");
            Loopback {
                port: bridge.base_url.rsplit(':').next().unwrap().parse().expect("a port"),
                token: pointer["token"].as_str().expect("a token").to_string(),
                root,
            }
        }

        /// One request, and its answer as `(status, JSON body)`. `token` is sent
        /// as the bearer token when given.
        fn request(
            &self,
            method: &str,
            path: &str,
            token: Option<&str>,
            body: Option<&str>,
        ) -> (u16, Value) {
            let mut stream = TcpStream::connect(("127.0.0.1", self.port)).expect("connect");
            stream.set_read_timeout(Some(Duration::from_secs(15))).unwrap();
            let body = body.unwrap_or("");
            let mut head = format!("{method} {path} HTTP/1.1\r\nHost: 127.0.0.1:{}\r\n", self.port);
            if let Some(t) = token {
                head.push_str(&format!("Authorization: Bearer {t}\r\n"));
            }
            head.push_str(&format!(
                "Content-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
                body.len()
            ));
            stream.write_all(head.as_bytes()).and_then(|()| stream.write_all(body.as_bytes())).unwrap();
            let mut raw = Vec::new();
            stream.read_to_end(&mut raw).expect("the bridge answers");
            let text = String::from_utf8_lossy(&raw).into_owned();
            let (head, payload) = text.split_once("\r\n\r\n").expect("a complete response");
            let status = head
                .lines()
                .next()
                .and_then(|l| l.split_whitespace().nth(1))
                .and_then(|s| s.parse().ok())
                .unwrap_or_else(|| panic!("no status line in {head:?}"));
            (status, serde_json::from_str(payload.trim()).unwrap_or(Value::Null))
        }

        /// The same, with this bridge's own token.
        fn call(&self, method: &str, path: &str, body: Option<&str>) -> (u16, Value) {
            self.request(method, path, Some(&self.token), body)
        }
    }

    impl Drop for Loopback {
        fn drop(&mut self) {
            let _ = std::fs::remove_dir_all(&self.root);
        }
    }

    #[test]
    fn the_loopback_helper_reaches_a_real_bridge() {
        let bridge = Loopback::start("http://127.0.0.1:1");
        // `/health` is the one open route, and answers with the shell's caps.
        let (status, body) = bridge.request("GET", "/health", None, None);
        assert_eq!(status, 200);
        assert_eq!(body["ok"], true);
        assert!(body["caps"].is_object());
        // An unknown route is a 404 from the real router, not from the helper.
        let (status, body) = bridge.call("GET", "/no/such/route", None);
        assert_eq!(status, 404);
        assert_eq!(body["error"], "not_found");
    }

    #[test]
    fn a_settings_refresh_needs_this_shells_token() {
        let bridge = Loopback::start("http://127.0.0.1:1");
        let (status, body) = bridge.request("POST", "/settings/refresh", None, Some("{}"));
        assert_eq!((status, body["error"].as_str()), (401, Some("unauthorized")));
        let (status, body) = bridge.request("POST", "/settings/refresh", Some("not-the-token"), Some("{}"));
        assert_eq!((status, body["error"].as_str()), (401, Some("unauthorized")));
    }

    #[test]
    fn a_settings_refresh_answers_applying_at_once_when_the_console_is_unreachable() {
        // Port 1 on loopback is closed: the console is "not running".
        let bridge = Loopback::start("http://127.0.0.1:1");
        let began = Instant::now();
        let (status, body) = bridge.call("POST", "/settings/refresh", Some("{}"));
        let took = began.elapsed();
        assert_eq!(status, 200);
        assert_eq!(body["applying"], true);
        assert_eq!(body["ok"], true);
        assert!(took < Duration::from_millis(500), "the poke took {took:?}");
    }

    #[test]
    fn a_console_that_never_answers_does_not_hold_the_poke() {
        // The case D-15 exists for: the settings fetch STALLS. A console that
        // accepts the connection and then says nothing is exactly that. The
        // route must still answer at once, and the fetch must still happen.
        let stalled = std::net::TcpListener::bind("127.0.0.1:0").expect("a free port");
        stalled.set_nonblocking(true).unwrap();
        let bridge = Loopback::start(&format!("http://{}", stalled.local_addr().unwrap()));

        let began = Instant::now();
        let (status, body) = bridge.call("POST", "/settings/refresh", Some("{}"));
        let took = began.elapsed();
        assert_eq!((status, &body["applying"]), (200, &Value::Bool(true)));
        assert!(took < Duration::from_millis(500), "the poke took {took:?} behind a stalled console");

        // The refresh really went to the console (so it was deferred, not
        // skipped). Holding the connection keeps the fetch waiting; dropping it
        // lets that thread finish instead of lingering for the read timeout.
        let deadline = Instant::now() + Duration::from_secs(5);
        let held = loop {
            match stalled.accept() {
                Ok((conn, _)) => break conn,
                Err(e) if e.kind() == std::io::ErrorKind::WouldBlock && Instant::now() < deadline => {
                    std::thread::sleep(Duration::from_millis(20));
                }
                Err(e) => panic!("the refresh never asked the console: {e}"),
            }
        };
        drop(held);
    }

    /// A console that answers `GET /api/assistant/settings` with these settings
    /// and nothing else, on a port of its own. Stops when dropped.
    struct FakeConsole {
        url: String,
        stop: Arc<std::sync::atomic::AtomicBool>,
    }

    impl FakeConsole {
        fn start(settings: Value) -> FakeConsole {
            let listener = std::net::TcpListener::bind("127.0.0.1:0").expect("a free port");
            listener.set_nonblocking(true).unwrap();
            let url = format!("http://{}", listener.local_addr().unwrap());
            let stop = Arc::new(std::sync::atomic::AtomicBool::new(false));
            let flag = stop.clone();
            let body = json!({"settings": settings}).to_string();
            std::thread::spawn(move || {
                while !flag.load(Ordering::SeqCst) {
                    match listener.accept() {
                        Ok((mut conn, _)) => {
                            let _ = conn.set_nonblocking(false);
                            let _ = conn.set_read_timeout(Some(Duration::from_secs(1)));
                            let mut request = [0u8; 2048];
                            let _ = conn.read(&mut request);
                            let reply = format!(
                                "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\
                                 Content-Length: {}\r\nConnection: close\r\n\r\n{body}",
                                body.len()
                            );
                            let _ = conn.write_all(reply.as_bytes());
                        }
                        Err(_) => std::thread::sleep(Duration::from_millis(5)),
                    }
                }
            });
            FakeConsole { url, stop }
        }
    }

    impl Drop for FakeConsole {
        fn drop(&mut self) {
            self.stop.store(true, Ordering::SeqCst);
        }
    }

    #[test]
    fn speak_takes_voice_and_speed_from_the_request_else_from_the_settings() {
        // The whole route, over a socket, with empty text: every line of the arm
        // runs and nothing is said out loud.
        let console = FakeConsole::start(json!({"speak_voice": "from-settings", "speak_rate_percent": 90}));
        let bridge = Loopback::start(&console.url);
        crate::console_settings::forget();

        let (status, body) = bridge.call(
            "POST", "/speak", Some(r#"{"text": "", "voice": "from-request", "rate_percent": 150}"#));
        assert_eq!((status, body["chars"].as_u64()), (200, Some(0)), "{body}");
        let (voice, rate) = tts::configured();
        assert_eq!(voice, "from-request");
        assert!((rate - 1.5).abs() < 1e-6, "{rate}");

        // A request that names neither gets the settings, so Preview's choice
        // did not leak into the next ordinary reply.
        let (status, _) = bridge.call("POST", "/speak", Some(r#"{"text": ""}"#));
        assert_eq!(status, 200);
        let (voice, rate) = tts::configured();
        assert_eq!(voice, "from-settings");
        assert!((rate - 0.9).abs() < 1e-6, "{rate}");
        crate::console_settings::forget();
    }

    // -- the audio routes and the new caps (T-031-24) -----------------------

    fn body_of(response: Response<std::io::Cursor<Vec<u8>>>) -> (u16, Value) {
        let status = response.status_code().0;
        let mut text = String::new();
        response.into_reader().read_to_string(&mut text).unwrap();
        (status, serde_json::from_str(&text).unwrap_or(Value::Null))
    }

    #[test]
    fn the_devices_route_lists_both_directions_with_a_verdict_each() {
        let bridge = Loopback::start("http://127.0.0.1:1");
        let (status, body) = bridge.request("GET", "/audio/devices", None, None);
        assert_eq!((status, body["error"].as_str()), (401, Some("unauthorized")));
        let (status, body) = bridge.call("GET", "/audio/devices", None);
        assert_eq!(status, 200, "{body}");
        assert!(body["inputs"].is_array() && body["outputs"].is_array(), "{body}");
        for side in ["input", "output"] {
            let v = &body[side];
            for key in ["configured", "resolved", "match", "fallback", "candidates"] {
                assert!(v.get(key).is_some(), "{side} has no {key}: {body}");
            }
        }
    }

    #[test]
    fn a_verdict_comes_from_the_one_matcher_per_direction() {
        let list = crate::devices::DeviceList {
            inputs: vec!["Array Mic".into(), "USB Headset Mic".into()],
            outputs: vec!["Speakers".into()],
            default_input: Some("Array Mic".into()),
            default_output: Some("Speakers".into()),
        };
        let v = devices_json(&list, " usb ", "Array Mic");
        assert_eq!(v["input"]["resolved"], "USB Headset Mic");
        assert_eq!(v["input"]["match"], "substring");
        assert_eq!(v["input"]["fallback"], false);
        // A name that exists only as an input is no output: the default is used.
        assert_eq!(v["output"]["resolved"], "Speakers");
        assert_eq!(v["output"]["fallback"], true);
        // No devices at all: nothing panics, nothing resolves.
        let none = devices_json(&crate::devices::DeviceList::default(), "", "x");
        assert_eq!(none["inputs"], json!([]));
        assert_eq!(none["input"]["resolved"], Value::Null);
    }

    #[test]
    fn the_mic_test_is_refused_with_a_reason_while_a_take_is_in_progress() {
        let bridge = Loopback::start("http://127.0.0.1:1");
        listen::force_busy(true);
        let (status, body) = bridge.call("POST", "/audio/test/mic", Some("{}"));
        listen::force_busy(false);
        assert_eq!(status, 409, "{body}");
        assert!(body["message"].as_str().unwrap().contains("take"), "{body}");
        // Free: the route's answer is 200 and the test starts (a fake starter,
        // so no microphone is opened here).
        let (status, body) = body_of(mic_test_response(None, || Ok(())));
        assert_eq!((status, &body["started"]), (200, &Value::Bool(true)));
        let (status, _) = body_of(mic_test_response(None, || Err("cannot open the microphone".into())));
        assert_eq!(status, 503);
    }

    #[test]
    fn the_speaker_test_without_an_output_is_a_503_with_the_reason() {
        let (status, body) = body_of(speaker_test_response(|| {
            Err("no output device: nothing is set as the default output device".into())
        }));
        assert_eq!(status, 503);
        assert!(body["message"].as_str().unwrap().contains("output"), "{body}");
        let (status, body) = body_of(speaker_test_response(|| Ok("Speakers".into())));
        assert_eq!((status, body["device"].as_str(), body["playing"].as_bool()), (200, Some("Speakers"), Some(true)));
    }

    #[test]
    fn the_listen_state_carries_the_mic_test_and_the_swap_error() {
        let state = listen_state_json(&std::env::temp_dir());
        for key in ["mic_test", "swap_error", "microphone", "engine_running", "model"] {
            assert!(state.get(key).is_some(), "no {key}");
        }
        let mut keys: Vec<_> = state["mic_test"].as_object().unwrap().keys().cloned().collect();
        keys.sort();
        assert!(keys.starts_with(&["device".into(), "peak".into(), "running".into()]), "{keys:?}");
        // And over the wire, from the real route.
        let bridge = Loopback::start("http://127.0.0.1:1");
        let (status, body) = bridge.call("GET", "/listen/state", None);
        assert_eq!(status, 200);
        assert!(body["mic_test"]["running"].is_boolean(), "{body}");
        assert!(body["swap_error"].is_string(), "{body}");
    }

    #[test]
    fn the_caps_report_the_loaded_model_and_the_voice_in_use() {
        let caps = capabilities(&std::env::temp_dir().join("t031-no-such-root"));
        assert!(caps["loaded_model"].is_string(), "{caps}");
        assert!(caps.get("speak_voice_in_use").is_some(), "{caps}");
        assert_eq!(caps["speak_voice_in_use"], Value::Null, "no voice is installed under that root");
    }

    #[test]
    fn the_open_health_route_carries_the_new_caps_over_the_wire() {
        let bridge = Loopback::start("http://127.0.0.1:1");
        let (status, body) = bridge.request("GET", "/health", None, None);
        assert_eq!(status, 200);
        assert!(body["caps"]["loaded_model"].is_string(), "{body}");
        assert!(body["caps"].get("speak_voice_in_use").is_some(), "{body}");
        // The mic and speaker routes need the token like every other.
        for path in ["/audio/test/mic", "/audio/test/speaker"] {
            let (status, _) = bridge.request("POST", path, None, Some("{}"));
            assert_eq!(status, 401, "{path}");
        }
    }

    /// [HL] A live model swap is visible where the console looks: the real
    /// engine, two models, the fixture. Skips loudly (and passes) when any of
    /// them is missing, which is the normal state on a machine with one model.
    #[test]
    fn live_swap_is_visible_in_listen_state() {
        let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
        let stt_dir = root.join("desktop/stt");
        let fixture = root.join("desktop/tests/fixtures/status-ticket-two.wav");
        if !crate::stt::available(&root) {
            eprintln!("skipped: {}", crate::stt::hint(&root));
            return;
        }
        for model in ["ggml-base.en.bin", "ggml-tiny.en.bin"] {
            if !stt_dir.join(model).is_file() {
                eprintln!("skipped: {model} is not installed under desktop/stt");
                return;
            }
        }
        if !fixture.is_file() {
            eprintln!("skipped: no fixture at {}", fixture.display());
            return;
        }
        struct Stop;
        impl Drop for Stop {
            fn drop(&mut self) {
                crate::stt::prefer_model("");
                crate::stt::shutdown();
            }
        }
        let _stop = Stop;
        let wav = std::fs::read(&fixture).unwrap();
        crate::stt::prefer_model("base.en");
        let first = crate::stt::transcribe(&root, &wav).expect("base.en transcribes");
        assert!(first.to_lowercase().contains("status"), "{first:?}");
        crate::stt::prefer_model("tiny.en");
        let began = Instant::now();
        // The next take starts the swap in the background and is served by the
        // old engine; wait for the replacement to publish.
        let _ = crate::stt::transcribe(&root, &wav);
        while crate::stt::loaded_model() != "ggml-tiny.en.bin" {
            assert!(began.elapsed() < Duration::from_secs(30), "no swap in 30 s: {}", crate::stt::swap_error());
            std::thread::sleep(Duration::from_millis(100));
        }
        let swap = began.elapsed();
        let second = crate::stt::transcribe(&root, &wav).expect("tiny.en transcribes");
        assert!(second.to_lowercase().contains("status"), "{second:?}");
        assert_eq!(listen_state_json(&root)["model"], "ggml-tiny.en.bin");
        eprintln!("live swap: base.en -> tiny.en visible in {swap:?}; heard {second:?}");
    }
}

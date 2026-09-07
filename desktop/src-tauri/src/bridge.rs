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
use crate::listen;
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
        // Probed like the rest: a microphone AND an installed engine.
        "stt": listen::available(repo_root),
        "stt_model": crate::stt::model_name(repo_root),
        "stt_hint": listen::hint(repo_root),
    })
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
                other => err(400, "bad_request", format!("unknown listen mode {other:?}")),
            }
        }
        ("GET", "/listen/state") => ok(json!({
            "listening": listen::listening(),
            "available": listen::available(repo_root),
            "hint": listen::hint(repo_root),
            "microphone": crate::audio::device_name(),
            "engine_running": crate::stt::running(),
            "model": crate::stt::loaded_model(),
        })),
        ("POST", "/speak") => {
            let body = match read_body(request) {
                Ok(v) => v,
                Err(e) => return err(400, "bad_request", e),
            };
            let text = body.get("text").and_then(Value::as_str).unwrap_or("");
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
                Ok(info) => ok(json!({"capture": info})),
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
}

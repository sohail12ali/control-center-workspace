//! The shell's one reader of the Assistant's settings.
//!
//! The console already merges the committed `console/config/assistant.toml`
//! with this machine's overrides and serves the result at
//! `GET /api/assistant/settings`. So the shell asks for the merged answer
//! rather than parsing TOML a second time — a second reader here would be a
//! second answer to the same question, and the two would disagree the first
//! time either file grew a key.
//!
//! Every getter takes a default and returns it when the console cannot be
//! reached or the value is nonsense. That is deliberate for an always-on
//! microphone: being wrong towards the cautious answer is the only acceptable
//! direction to be wrong in.

use std::io::{BufRead, BufReader, Read, Write};
use std::time::Duration;

/// How long to wait on loopback before giving up and using defaults. Generous
/// for a local socket, short enough that a click never feels stuck.
const TIMEOUT: Duration = Duration::from_secs(5);

/// The merged settings object, as the console reports it.
pub fn fetch(console_url: &str) -> Result<serde_json::Value, String> {
    let rest = console_url.strip_prefix("http://").ok_or("not an http url")?;
    let authority = rest.split('/').next().ok_or("no authority")?;
    let (host, port) = authority.rsplit_once(':').ok_or("no port")?;
    let port: u16 = port.parse().map_err(|_| "bad port")?;

    let mut stream = std::net::TcpStream::connect((host, port)).map_err(|e| e.to_string())?;
    stream
        .set_read_timeout(Some(TIMEOUT))
        .map_err(|e| e.to_string())?;
    let request = format!(
        "GET /api/assistant/settings HTTP/1.1\r\n\
         Host: {host}:{port}\r\n\
         Accept: application/json\r\n\
         Connection: close\r\n\r\n"
    );
    stream
        .write_all(request.as_bytes())
        .map_err(|e| e.to_string())?;

    let mut reader = BufReader::new(stream);
    let mut status = String::new();
    reader.read_line(&mut status).map_err(|e| e.to_string())?;
    if !status.contains(" 200") {
        return Err(format!("settings said {}", status.trim()));
    }
    loop {
        let mut line = String::new();
        let n = reader.read_line(&mut line).map_err(|e| e.to_string())?;
        // Blank line = end of headers. Trimmed, so this does not depend on
        // which line ending the server used.
        if n == 0 || line.trim().is_empty() {
            break;
        }
    }
    let mut body = String::new();
    reader.read_to_string(&mut body).map_err(|e| e.to_string())?;
    let parsed: serde_json::Value =
        serde_json::from_str(body.trim()).map_err(|e| e.to_string())?;
    parsed
        .get("settings")
        .cloned()
        .ok_or_else(|| "no settings in the answer".to_string())
}

/// Write one boolean setting back. Best-effort: the caller is a menu click,
/// and a console that cannot be reached must not make the menu feel broken —
/// the local state still changes and this says why in the log.
pub fn set_bool(console_url: &str, key: &str, value: bool) {
    if let Err(e) = post(console_url, &format!("{{\"{key}\": {value}}}")) {
        log::warn!("settings: could not store {key}={value} ({e})");
    }
}

fn post(console_url: &str, body: &str) -> Result<(), String> {
    let rest = console_url.strip_prefix("http://").ok_or("not an http url")?;
    let authority = rest.split('/').next().ok_or("no authority")?;
    let (host, port) = authority.rsplit_once(':').ok_or("no port")?;
    let port: u16 = port.parse().map_err(|_| "bad port")?;

    let mut stream = std::net::TcpStream::connect((host, port)).map_err(|e| e.to_string())?;
    stream.set_read_timeout(Some(TIMEOUT)).map_err(|e| e.to_string())?;
    // Written line by line rather than as one continued literal: an escaped
    // CRLF inside a multi-line string is easy to mangle and impossible to see
    // afterwards, and a header block with a stray space in it fails as a
    // silent no-op rather than an error.
    let mut head = String::new();
    head.push_str("POST /api/assistant/settings HTTP/1.1\r\n");
    head.push_str(&format!("Host: {host}:{port}\r\n"));
    head.push_str("Content-Type: application/json\r\n");
    // The console requires this on every POST — it is what a cross-site page
    // cannot attach without CORS.
    head.push_str("X-Console-Request: 1\r\n");
    head.push_str(&format!("Content-Length: {}\r\n", body.len()));
    head.push_str("Connection: close\r\n\r\n");
    stream
        .write_all(head.as_bytes())
        .and_then(|()| stream.write_all(body.as_bytes()))
        .map_err(|e| e.to_string())?;
    let mut status = String::new();
    BufReader::new(stream)
        .read_line(&mut status)
        .map_err(|e| e.to_string())?;
    if !status.contains(" 200") {
        return Err(format!("settings said {}", status.trim()));
    }
    Ok(())
}

/// The merged settings, or an empty object when the console cannot be asked.
///
/// For a caller that needs several keys at once: one request, then read from
/// the result with `u64_at`/`str_at`. Three `*_or` calls in a row would be
/// three round trips for one answer.
pub fn all(console_url: &str) -> serde_json::Value {
    match fetch(console_url) {
        Ok(v) => v,
        Err(e) => {
            log::debug!("settings: unavailable ({e}); using defaults");
            serde_json::Value::Null
        }
    }
}

/// One whole number out of an already-fetched settings object.
pub fn u64_at(settings: &serde_json::Value, key: &str, fallback: u64) -> u64 {
    settings.get(key).and_then(|x| x.as_u64()).unwrap_or(fallback)
}

/// One non-blank string out of an already-fetched settings object.
pub fn str_at(settings: &serde_json::Value, key: &str, fallback: &str) -> String {
    settings
        .get(key)
        .and_then(|x| x.as_str())
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .unwrap_or(fallback)
        .to_string()
}

/// One string setting, with a fallback used for every failure — unreachable
/// console, missing key, wrong type, or a blank value.
pub fn string_or(console_url: &str, key: &str, fallback: &str) -> String {
    match fetch(console_url) {
        Ok(v) => v
            .get(key)
            .and_then(|x| x.as_str())
            .map(str::trim)
            .filter(|s| !s.is_empty())
            .unwrap_or(fallback)
            .to_string(),
        Err(e) => {
            log::debug!("settings: {key} unavailable ({e}); using {fallback:?}");
            fallback.to_string()
        }
    }
}

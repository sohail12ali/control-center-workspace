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

//! Saying something to the Assistant, from anywhere in the shell.
//!
//! ## Why this is its own module
//!
//! `listen.rs` owned the only copy: a private `say` that posted a transcript
//! to `/api/assistant/say`. Then the tray needed to say "copy that" for its
//! clipboard row, and the choice was a second copy of a hand-written HTTP
//! POST or one shared one. There will be a third caller — a hotkey, the
//! overlay — and each copy is another place for the CSRF header or the 2xx
//! check to be got subtly wrong.
//!
//! ## Why it posts a sentence rather than calling a verb
//!
//! `copy that`, `new chat`, `interrupt` and `mute` are already fast commands
//! the console matches before any model sees them
//! (`console/server/assistant_commands.py`). Posting the sentence therefore
//! reuses the whole dispatch — the matching, the handler, the audit record —
//! and the tray gains no privileged path of its own. A tray row and a typed
//! phrase end up doing the identical thing, which is the property that keeps
//! them from drifting.

use std::io::{BufRead, BufReader, Write};

pub type ApiResult<T> = Result<T, String>;

/// POST text to the Assistant, exactly as the palette would.
///
/// `source` is recorded on the audit line — "voice", "tray" — so a reply that
/// arrives from nowhere can be traced to whatever asked for it.
pub fn say(console_url: &str, text: &str, source: &str) -> ApiResult<()> {
    let (host, port) = split_host_port(console_url)
        .ok_or_else(|| format!("cannot parse the console url {console_url}"))?;
    let body = format!(
        "{{\"text\":{},\"source\":{}}}",
        json_string(text),
        json_string(source)
    );
    let mut stream = std::net::TcpStream::connect((host.as_str(), port))
        .map_err(|e| format!("cannot reach the console: {e}"))?;
    let head = format!(
        "POST /api/assistant/say HTTP/1.1\r\nHost: {host}:{port}\r\n\
         Content-Type: application/json\r\nX-Console-Request: 1\r\n\
         Content-Length: {}\r\nConnection: close\r\n\r\n",
        body.len()
    );
    stream
        .write_all(head.as_bytes())
        .and_then(|()| stream.write_all(body.as_bytes()))
        .map_err(|e| format!("cannot send the message: {e}"))?;
    let mut status = String::new();
    BufReader::new(stream)
        .read_line(&mut status)
        .map_err(|e| format!("no answer from the console: {e}"))?;
    if !accepted(&status) {
        return Err(format!("the console said {}", status.trim()));
    }
    Ok(())
}

/// Say something on a worker thread, reporting failure to the overlay.
///
/// For a menu-event handler, which runs on the UI thread: this is an HTTP
/// round trip, and a tray that freezes for the length of one is the exact
/// defect T-015 exists to remove. Nothing waits for the answer, so the caller
/// stays a single line.
pub fn say_detached(console_url: &str, text: &'static str, source: &'static str) {
    let url = console_url.to_string();
    let spawned = std::thread::Builder::new()
        .name("console-say".into())
        .spawn(move || {
            if let Err(e) = say(&url, text, source) {
                log::warn!("console-api: {text:?} failed: {e}");
                // Said where the user is looking, not only in a log file. A
                // menu row that silently does nothing is indistinguishable
                // from a broken one.
                crate::tray_paint::said("could not reach the console");
            }
        });
    if let Err(e) = spawned {
        log::warn!("console-api: could not start a thread to say {text:?}: {e}");
    }
}

/// Did the console accept it?
///
/// Any 2xx, not 200 alone. The first message of a brand-new chat is answered
/// `201 Created` — found by a live hands-free run, where a perfectly
/// delivered sentence was logged as a failure because it had created the chat
/// it landed in.
pub fn accepted(status_line: &str) -> bool {
    status_line
        .split_whitespace()
        .nth(1)
        .and_then(|code| code.parse::<u16>().ok())
        .map(|code| (200..300).contains(&code))
        .unwrap_or(false)
}

pub fn split_host_port(url: &str) -> Option<(String, u16)> {
    let rest = url.strip_prefix("http://")?;
    let authority = rest.split('/').next()?;
    let (host, port) = authority.rsplit_once(':')?;
    Some((host.to_string(), port.parse().ok()?))
}

/// Minimal JSON string escaping. A transcript is model-adjacent text from a
/// speech engine listening to a room; a stray quote in it must not produce a
/// malformed body.
pub fn json_string(text: &str) -> String {
    let mut out = String::with_capacity(text.len() + 2);
    out.push('"');
    for c in text.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn any_2xx_means_the_console_took_it() {
        // 201 is not hypothetical: it is what the console answers when the
        // message starts a new chat, which is the ordinary case for the first
        // thing you say after launching.
        for line in ["HTTP/1.0 200 OK", "HTTP/1.1 201 Created", "HTTP/1.0 204 No Content"] {
            assert!(accepted(line), "{line:?}");
        }
    }

    #[test]
    fn anything_else_is_a_failure_worth_reporting() {
        for line in ["HTTP/1.0 400 Bad Request", "HTTP/1.1 500 Internal Server Error",
                     "HTTP/1.0 302 Found", "garbage", ""] {
            assert!(!accepted(line), "{line:?}");
        }
    }

    #[test]
    fn a_transcript_with_quotes_cannot_break_the_body() {
        assert_eq!(json_string(r#"say "hello""#), r#""say \"hello\"""#);
        assert_eq!(json_string("back\\slash"), r#""back\\slash""#);
        assert_eq!(json_string("two\nlines"), r#""two\nlines""#);
    }

    #[test]
    fn control_characters_are_escaped_not_emitted() {
        // Escaped as JSON requires, not dropped: a raw control byte inside a
        // string is what would make the request body malformed.
        // The expected form is built from a RAW string, so the six
        // characters backslash-u-0-0-0-7 appear once and mean themselves.
        // An escaped escape inside a normal literal is exactly the kind of
        // thing a test should not be asserting by eye.
        let want = format!("\"bell{}\"", r"\u0007");
        assert_eq!(json_string("bell\u{7}"), want);
    }

    #[test]
    fn ordinary_words_pass_through() {
        assert_eq!(json_string("status ticket two"), r#""status ticket two""#);
    }

    #[test]
    fn the_console_url_splits() {
        assert_eq!(
            split_host_port("http://127.0.0.1:8790"),
            Some(("127.0.0.1".to_string(), 8790))
        );
        assert_eq!(split_host_port("nonsense"), None);
    }

    #[test]
    fn a_url_it_cannot_use_is_rejected_rather_than_guessed() {
        // No default port: connecting to the wrong one would look like the
        // console being down, which is a confusing way to fail.
        assert_eq!(split_host_port("https://example.com/x"), None);
        assert_eq!(split_host_port("http://127.0.0.1"), None);
    }
}

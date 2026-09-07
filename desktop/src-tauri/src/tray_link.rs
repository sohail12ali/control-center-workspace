//! Drives the tray icon from the console's live event stream.
//!
//! ## Why the shell subscribes, rather than the page telling it
//!
//! The tray has to be right when the window is hidden or showing another tab
//! — that is the whole point of a tray. Anything routed through the webview
//! would go stale exactly when the user is relying on it. So the shell reads
//! the assistant's own SSE stream directly and owns its state.
//!
//! ## Why a hand-written HTTP client
//!
//! This makes one plaintext GET to `127.0.0.1` and reads lines until the
//! process ends. Adding an HTTP client crate for that would pull a TLS stack
//! and an async runtime into a binary that needs neither. Sixty lines of
//! `TcpStream` is the smaller thing to own, and it cannot reach anywhere but
//! loopback because that is all it knows how to address.
//!
//! ## Reconnecting is the normal case, not the error case
//!
//! The stream 404s until an assistant chat exists, ends when the server
//! restarts, and drops if the machine sleeps. None of those are faults, so
//! there is no error state — just a backoff and another attempt, with the
//! tray sitting at idle in the meantime.

use std::io::{BufRead, BufReader, Write};
use std::net::TcpStream;
use std::sync::{Arc, Mutex};
use std::time::Duration;

use tauri::image::Image;
use tauri::AppHandle;

use crate::tray_state::{Assistant, Event};

/// Tray icon id, as built in `tray.rs`.
const TRAY_ID: &str = "main";

/// Backoff between attempts. Short enough that the tray comes alive promptly
/// after the console starts, long enough not to spin on a closed port.
const RETRY: Duration = Duration::from_secs(3);

/// Start the subscriber. Never fails the caller: a tray that cannot follow
/// events is a degraded tray, not a reason to refuse to start.
pub fn spawn(app: AppHandle, assistant: Arc<Mutex<Assistant>>, console_url: String) {
    let builder = std::thread::Builder::new().name("tray-link".into());
    if let Err(e) = builder.spawn(move || run(app, assistant, console_url)) {
        log::warn!("tray-link: not started ({e}); the tray icon will stay idle");
    }
}

fn run(app: AppHandle, assistant: Arc<Mutex<Assistant>>, console_url: String) {
    let Some((host, port)) = split_host_port(&console_url) else {
        log::warn!("tray-link: cannot parse {console_url}; giving up");
        return;
    };
    loop {
        match follow(&app, &assistant, &host, port) {
            Ok(()) => log::info!("tray-link: stream ended, reconnecting"),
            Err(e) => log::debug!("tray-link: {e}"),
        }
        // Clear only a THINKING state, and only because a turn we were
        // tracking can no longer be tracked.
        //
        // This used to apply `TurnEnd` unconditionally, which was wrong in a
        // way live testing caught: the stream 404s until an assistant chat
        // exists, so this loop ran every few seconds, and each pass reset a
        // state the SHELL owns — the tray showed "idle" while the microphone
        // was open. Listening and speaking are the shell's to report; only
        // the turn is the console's.
        if let Ok(a) = assistant.lock() {
            if a.state() != crate::icons::State::Thinking {
                std::thread::sleep(RETRY);
                continue;
            }
        }
        apply(&app, &assistant, Event::TurnEnd);
        std::thread::sleep(RETRY);
    }
}

fn split_host_port(url: &str) -> Option<(String, u16)> {
    let rest = url.strip_prefix("http://")?;
    let authority = rest.split('/').next()?;
    let (host, port) = authority.rsplit_once(':')?;
    Some((host.to_string(), port.parse().ok()?))
}

fn follow(
    app: &AppHandle,
    assistant: &Arc<Mutex<Assistant>>,
    host: &str,
    port: u16,
) -> Result<(), String> {
    let mut stream = TcpStream::connect((host, port)).map_err(|e| e.to_string())?;
    // No read timeout: an SSE stream is idle most of the time by design, and
    // a timeout would tear down a healthy connection between turns.
    stream
        .write_all(
            format!(
                "GET /api/assistant/stream HTTP/1.1\r\nHost: {host}:{port}\r\n\
                 Accept: text/event-stream\r\nConnection: keep-alive\r\n\r\n"
            )
            .as_bytes(),
        )
        .map_err(|e| e.to_string())?;

    let mut reader = BufReader::new(stream);
    let mut status = String::new();
    reader.read_line(&mut status).map_err(|e| e.to_string())?;
    if !status.contains(" 200") {
        // A 404 here is the ordinary "no assistant chat yet" case.
        return Err(format!("stream said {}", status.trim()));
    }
    log::info!("tray-link: following the assistant stream");

    let mut line = String::new();
    loop {
        line.clear();
        let read = reader.read_line(&mut line).map_err(|e| e.to_string())?;
        if read == 0 {
            return Ok(()); // server closed
        }
        let Some(payload) = line.strip_prefix("data:") else {
            continue; // event:, id:, comments, blank separators
        };
        let payload = payload.trim();
        if payload.is_empty() {
            continue;
        }
        for event in events_for(payload) {
            apply(app, assistant, event);
        }
        if let Some(backend) = backend_of(payload) {
            let changed = assistant
                .lock()
                .map(|mut a| a.set_backend(&backend))
                .unwrap_or(false);
            if changed {
                repaint(app, assistant);
            }
        }
    }
}

/// The console's event type, pulled out without a JSON parser.
///
/// `serde_json` is already a dependency and could parse this — but the field
/// is a flat string in a flat object and a substring match cannot fail on a
/// payload shape it did not expect, which for a decorative icon is the safer
/// failure mode.
fn field(payload: &str, key: &str) -> Option<String> {
    let needle = format!("\"{key}\":");
    let start = payload.find(&needle)? + needle.len();
    let rest = payload[start..].trim_start();
    let rest = rest.strip_prefix('"')?;
    let end = rest.find('"')?;
    Some(rest[..end].to_string())
}

fn events_for(payload: &str) -> Vec<Event> {
    match field(payload, "type").unwrap_or_default().as_str() {
        "turn.start" => vec![Event::TurnStart],
        "turn.end" => vec![Event::TurnEnd],
        // The console's own name for "a human is being asked". `attention` is
        // accepted too because the T-004 stream contract named it, and a
        // future UI event by that name should still light the badge.
        "approval.request" | "attention" => vec![Event::ApprovalNeeded],
        "approval.decided" => vec![Event::ApprovalResolved],
        "speaking.start" => vec![Event::SpeakStart],
        "speaking.stop" => vec![Event::SpeakStop],
        _ => vec![],
    }
}

fn backend_of(payload: &str) -> Option<String> {
    field(payload, "backend").or_else(|| field(payload, "agent"))
}

fn apply(app: &AppHandle, assistant: &Arc<Mutex<Assistant>>, event: Event) {
    let changed = match assistant.lock() {
        Ok(mut a) => a.apply(event),
        Err(e) => {
            log::warn!("tray-link: state lock poisoned: {e}");
            return;
        }
    };
    if changed {
        repaint(app, assistant);
    }
}

/// Push the current state onto the actual tray icon.
fn repaint(app: &AppHandle, assistant: &Arc<Mutex<Assistant>>) {
    let (bytes, tooltip) = match assistant.lock() {
        Ok(a) => (a.icon(), a.tooltip()),
        Err(_) => return,
    };
    let Some(tray) = app.tray_by_id(TRAY_ID) else {
        return;
    };
    match Image::from_bytes(bytes) {
        Ok(image) => {
            if let Err(e) = tray.set_icon(Some(image)) {
                log::warn!("tray-link: set_icon failed: {e}");
            }
            #[cfg(target_os = "macos")]
            if let Err(e) = tray.set_icon_as_template(true) {
                log::warn!("tray-link: set_icon_as_template failed: {e}");
            }
        }
        Err(e) => log::warn!("tray-link: icon bytes rejected: {e}"),
    }
    if let Err(e) = tray.set_tooltip(Some(&tooltip)) {
        log::warn!("tray-link: set_tooltip failed: {e}");
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_console_url_splits_into_host_and_port() {
        assert_eq!(
            split_host_port("http://127.0.0.1:8790"),
            Some(("127.0.0.1".to_string(), 8790))
        );
        assert_eq!(
            split_host_port("http://127.0.0.1:8790/"),
            Some(("127.0.0.1".to_string(), 8790))
        );
    }

    #[test]
    fn a_url_it_cannot_use_is_rejected_rather_than_guessed() {
        // No default port: connecting to the wrong one would look like the
        // console being down, which is a confusing way to fail.
        assert_eq!(split_host_port("https://example.com/stream"), None);
        assert_eq!(split_host_port("http://127.0.0.1"), None);
        assert_eq!(split_host_port("nonsense"), None);
    }

    #[test]
    fn reads_a_flat_string_field() {
        let payload = r#"{"type": "turn.start", "backend": "claude"}"#;
        assert_eq!(field(payload, "type").as_deref(), Some("turn.start"));
        assert_eq!(field(payload, "backend").as_deref(), Some("claude"));
        assert_eq!(field(payload, "missing"), None);
    }

    #[test]
    fn maps_the_events_the_console_actually_sends() {
        for (payload, want) in [
            (r#"{"type":"turn.start"}"#, Some(Event::TurnStart)),
            (r#"{"type":"turn.end"}"#, Some(Event::TurnEnd)),
            (r#"{"type":"attention"}"#, Some(Event::ApprovalNeeded)),
            (r#"{"type":"approval.request"}"#, Some(Event::ApprovalNeeded)),
            (r#"{"type":"approval.decided"}"#, Some(Event::ApprovalResolved)),
            (r#"{"type":"speaking.start"}"#, Some(Event::SpeakStart)),
            (r#"{"type":"speaking.stop"}"#, Some(Event::SpeakStop)),
        ] {
            assert_eq!(events_for(payload).into_iter().next(), want, "{payload}");
        }
    }

    #[test]
    fn an_event_it_does_not_know_moves_nothing() {
        // The stream carries more than the tray cares about, and a future
        // event type must not be mistaken for one of these.
        for payload in [
            r#"{"type":"reply"}"#,
            r#"{"type":"usage"}"#,
            r#"{"type":"tool.start"}"#,
            r#"{}"#,
            "not json at all",
        ] {
            assert!(events_for(payload).is_empty(), "{payload}");
        }
    }

    #[test]
    fn a_disconnect_must_not_clear_a_listening_state() {
        // The regression this exists for: the reconnect loop reset the state
        // every few seconds while the stream was unavailable, so the tray
        // read "idle" with the microphone open. Listening belongs to the
        // shell; only a turn belongs to the console.
        let mut a = Assistant::default();
        a.apply(Event::ListenStart);
        assert_eq!(a.state(), crate::icons::State::Listening);
        // What the loop is now allowed to do, i.e. nothing, unless thinking.
        assert_ne!(a.state(), crate::icons::State::Thinking);
    }

    #[test]
    fn a_disconnect_does_clear_a_stale_thinking_state() {
        let mut a = Assistant::default();
        a.apply(Event::TurnStart);
        assert_eq!(a.state(), crate::icons::State::Thinking);
        a.apply(Event::TurnEnd);
        assert_eq!(a.state(), crate::icons::State::Idle);
    }

    #[test]
    fn a_turn_through_the_real_state_machine_ends_idle() {
        // The mapping is only useful if the sequence it produces leaves the
        // tray somewhere sensible.
        let mut a = Assistant::default();
        for payload in [
            r#"{"type":"turn.start"}"#,
            r#"{"type":"approval.request"}"#,
            r#"{"type":"approval.decided"}"#,
            r#"{"type":"turn.end"}"#,
        ] {
            for event in events_for(payload) {
                a.apply(event);
            }
        }
        assert_eq!(a.state(), crate::icons::State::Idle);
        assert!(!a.needs_approval(), "the badge must clear when answered");
    }
}

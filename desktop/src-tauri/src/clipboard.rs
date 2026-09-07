//! Clipboard read and write.
//!
//! ## The two halves are not equally risky, and the code says so
//!
//! WRITE replaces something the user can see and can undo by copying again.
//! READ can hand a password manager's buffer, a bank detail or a private key
//! to a hosted model, and the user may not remember what they last copied.
//!
//! So write is ungated here and in the console; read is gated behind the
//! in-chat "Permission needed" card, is never approvable from Telegram, and
//! never gets an allow-for-this-chat. This module does not enforce the gate —
//! the console does, before it calls — but `peek` exists precisely so the gate
//! can be *informative*: the card can say "will read 1,204 characters" without
//! reading the contents to find out.

use serde::Serialize;

pub type ClipResult<T> = Result<T, String>;

/// Serialises every clipboard operation in this process.
///
/// Opening the system clipboard is not a thread-safe operation — on Windows it
/// goes through OLE, and two threads doing it at once corrupted the heap
/// (0xC0000374) reliably enough to take the test binary down. The bridge
/// happens to handle requests one at a time today, so this is insurance
/// rather than a fix for an observed product bug; but the fact that the
/// clipboard is a single global resource belongs to the module that owns it,
/// not to every caller's scheduling.
fn lock() -> std::sync::MutexGuard<'static, ()> {
    static GUARD: std::sync::Mutex<()> = std::sync::Mutex::new(());
    // A poisoned guard means another thread panicked mid-operation. The
    // clipboard itself is fine, so carry on rather than refusing forever.
    GUARD.lock().unwrap_or_else(|e| e.into_inner())
}

fn open() -> ClipResult<arboard::Clipboard> {
    // A failure here is usually a headless session or a Wayland compositor
    // without the data-control protocol. The message is passed through so the
    // console can show the real reason rather than "clipboard unavailable".
    arboard::Clipboard::new().map_err(|e| format!("cannot open the clipboard: {e}"))
}

/// Metadata only — never the contents. This is what makes an approval card
/// specific ("1,204 characters of text") without the read it is gating.
#[derive(Serialize)]
pub struct Peek {
    pub has_text: bool,
    pub text_len: usize,
    /// First line, truncated hard, for a card that wants a hint of shape.
    /// Never more than this: a preview long enough to be useful is a read.
    pub preview: String,
}

const PREVIEW_CHARS: usize = 40;

pub fn peek() -> ClipResult<Peek> {
    let _guard = lock();
    let mut cb = open()?;
    match cb.get_text() {
        Ok(text) => {
            let first = text.lines().next().unwrap_or("");
            let preview: String = first.chars().take(PREVIEW_CHARS).collect();
            Ok(Peek {
                has_text: !text.is_empty(),
                text_len: text.chars().count(),
                preview,
            })
        }
        // An empty or non-text clipboard is not an error — it is an answer.
        Err(_) => Ok(Peek {
            has_text: false,
            text_len: 0,
            preview: String::new(),
        }),
    }
}

/// The gated half. The console must have an answered approval before calling.
pub fn read_text() -> ClipResult<String> {
    let _guard = lock();
    let mut cb = open()?;
    cb.get_text()
        .map_err(|e| format!("cannot read the clipboard: {e}"))
}

/// The ungated half — audited, but no card.
pub fn write_text(text: &str) -> ClipResult<usize> {
    let _guard = lock();
    let mut cb = open()?;
    cb.set_text(text.to_string())
        .map_err(|e| format!("cannot write the clipboard: {e}"))?;
    Ok(text.chars().count())
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Round-trip and peek in ONE test, on purpose.
    ///
    /// There is one system clipboard and cargo runs tests in parallel, which
    /// broke this twice in different ways. Split into two tests, each writing
    /// its own probe, they raced on VALUES: `left: 15, right: 63`, one test's
    /// string measured against the other's. `lock()` above does not help with
    /// that — it serialises the operations, not the assertions between them —
    /// so the two halves belong in one sequential test.
    ///
    /// The mutex is for the other failure: two threads OPENING the clipboard
    /// at once corrupted the heap. Different problem, different fix, and both
    /// are needed.
    ///
    /// Skipped, loudly, where there is no clipboard to talk to — a CI
    /// container or a headless Linux session. Skipping beats a test that
    /// passes because it quietly asserted nothing.
    #[test]
    fn write_read_and_peek_against_the_real_clipboard() {
        let probe = format!("t005-probe-{}", std::process::id());
        if let Err(e) = write_text(&probe) {
            eprintln!("skipped: no clipboard in this session ({e})");
            return;
        }
        assert_eq!(
            read_text().expect("a clipboard that accepted a write can be read"),
            probe
        );

        let secret = "correct horse battery staple and a great deal more text besides";
        write_text(secret).expect("the clipboard already accepted one write");
        let p = peek().expect("peek works wherever a write worked");
        assert_eq!(p.text_len, secret.chars().count());
        assert!(p.has_text);
        // The point of the cap: a card must be able to describe the clipboard
        // without disclosing it.
        assert!(p.preview.chars().count() <= PREVIEW_CHARS);
        assert!(!p.preview.contains("besides"));
    }
}

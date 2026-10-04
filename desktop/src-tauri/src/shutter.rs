//! What a screenshot looks and sounds like.
//!
//! ## Why a capture needs to announce itself
//!
//! Every other way to take a screenshot on this machine tells you it happened
//! — Print Screen dims the screen, the Snipping Tool clicks. The assistant's
//! captures were silent and invisible, which makes two bad things possible at
//! once: you ask for a capture and cannot tell whether it worked, and
//! something captures your screen without you noticing. The second is the
//! serious one. A shutter sound is a privacy feature that happens to also be
//! good feedback.
//!
//! ## After, never before
//!
//! `fire` is called once the pixels are already grabbed. A flash drawn first
//! would be IN the screenshot — which is the one bug this kind of overlay
//! reliably ships with.
//!
//! ## Best effort, always
//!
//! A machine with no output device, or a window server that refuses another
//! overlay, still takes screenshots. Every failure here is logged at debug and
//! swallowed: none of it is a reason to fail a capture that already succeeded.

use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Duration;

use tauri::{WebviewUrl, WebviewWindowBuilder};

/// Where the capture came from, in physical screen pixels — the flash covers
/// exactly that, so a region capture flashes a region and not the display.
#[derive(Clone, Copy, Debug)]
pub struct Rect {
    pub x: i32,
    pub y: i32,
    pub width: u32,
    pub height: u32,
}

/// A fresh label per flash.
///
/// It was one reused label, and closing the previous window first. That does
/// not work: `close()` is asynchronous, so a second capture within the
/// linger hit "a webview with label `capture-flash` already exists" and got
/// no flash at all — which the two-captures-in-a-row test caught. Counting
/// means overlapping captures each get their own pane and each closes its
/// own, in order.
static SEQ: AtomicU64 = AtomicU64::new(0);

/// Long enough to be seen, short enough not to be in the way. The page's own
/// animation is 240ms; this is that plus a margin, because the window closing
/// mid-fade is a visible snap.
const LINGER: Duration = Duration::from_millis(320);

/// Announce a capture: the shutter, then the flash.
pub fn fire(rect: Option<Rect>) {
    crate::cue::play(crate::cue::Cue::Shutter);
    flash(rect);
}

fn flash(rect: Option<Rect>) {
    let Some(rect) = rect else {
        // No geometry means no honest place to put the pane. The sound
        // already said the capture happened; a flash over a guessed
        // rectangle would be worse than none.
        return;
    };
    let Some(app) = crate::tray_paint::app() else {
        return;
    };
    let console_url = crate::tray_paint::console_url();
    if console_url.is_empty() {
        return;
    }

    let url = match format!("{}/flash.html", console_url.trim_end_matches('/')).parse() {
        Ok(u) => u,
        Err(e) => {
            log::debug!("shutter: cannot build a url from {console_url}: {e}");
            return;
        }
    };

    let label = format!("capture-flash-{}", SEQ.fetch_add(1, Ordering::Relaxed));

    #[allow(unused_mut)]
    let mut builder = WebviewWindowBuilder::new(&app, &label, WebviewUrl::External(url))
        .title("Capture")
        .position(rect.x as f64, rect.y as f64)
        .inner_size(rect.width as f64, rect.height as f64)
        .resizable(false)
        .decorations(false)
        .always_on_top(true)
        .skip_taskbar(true)
        // Never takes focus: a flash that steals the caret from whatever you
        // were typing in would be a worse bug than no flash at all.
        .focused(false)
        .shadow(false);
    #[cfg(not(target_os = "macos"))]
    {
        builder = builder.transparent(true);
    }

    let window = match builder.build() {
        Ok(w) => w,
        Err(e) => {
            log::debug!("shutter: no flash ({e})");
            return;
        }
    };
    // Clicks go to whatever is underneath. For a quarter of a second the pane
    // covers a region of someone's screen, and it must not eat the click they
    // were already making.
    let _ = window.set_ignore_cursor_events(true);

    // Closed on a timer rather than by the page, so a page that fails to load
    // cannot leave a white rectangle on the screen.
    std::thread::Builder::new()
        .name("capture-flash".into())
        .spawn(move || {
            std::thread::sleep(LINGER);
            let _ = window.close();
        })
        .ok();
}

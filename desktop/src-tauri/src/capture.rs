//! Screen, monitor, window and region capture.
//!
//! One crate (`xcap`) for all three targets rather than a Windows-only path:
//! it wraps Windows Graphics Capture with a GDI fallback, CoreGraphics on
//! macOS and X11 on Linux, so the shell has one API and the per-OS problems
//! stay inside the crate. Where a platform genuinely cannot do something —
//! window-by-title under Wayland, for instance — the answer is an error the
//! caller reports verbatim, never a silently black frame.
//!
//! ## Captures are files, never payloads
//!
//! Every capture is written to `console/.cache/desktop-captures/` and the
//! bridge returns a PATH. That is what lets a Claude or Cursor backend read
//! the image with its own file tools, keeps a multi-megabyte PNG out of a
//! JSON response, and means a capture that is never sent anywhere leaves a
//! reviewable artefact on disk rather than vanishing into a prompt.
//!
//! ## Our own window is excluded
//!
//! Capturing the assistant while asking the assistant about the screen is
//! both useless and a privacy trap (the window may be showing a transcript).

use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

use serde::Serialize;
use xcap::image::{imageops::FilterType, RgbaImage};
use xcap::{Monitor, Window};

/// Where captures land, relative to the repo root. Gitignored via
/// `console/.cache/`.
const CAPTURE_DIR: &str = "console/.cache/desktop-captures";

/// Longest edge of a saved capture unless the caller asks for more. A 4K
/// screenshot is ~8 MB of PNG and no vision model reads it at full size;
/// 1920 keeps text legible for OCR while staying a sane attachment.
pub const DEFAULT_MAX_SIDE: u32 = 1920;

/// Titles belonging to the shell itself.
const OWN_TITLES: [&str; 1] = ["Delivery Console"];

#[derive(Serialize)]
pub struct MonitorInfo {
    pub id: u32,
    pub name: String,
    pub x: i32,
    pub y: i32,
    pub width: u32,
    pub height: u32,
    pub scale: f32,
    pub primary: bool,
}

/// Deliberately no process path or command line — a window list is for
/// naming a capture target, not for inventorying what someone is running.
#[derive(Serialize)]
pub struct WindowInfo {
    pub id: u32,
    pub title: String,
    pub app: String,
    pub x: i32,
    pub y: i32,
    pub width: u32,
    pub height: u32,
    pub minimized: bool,
}

#[derive(Serialize)]
pub struct CaptureInfo {
    pub capture_id: String,
    /// Repo-relative so it is safe to hand to a confined tool.
    pub path: String,
    pub width: u32,
    pub height: u32,
    pub bytes: u64,
    pub target: String,
}

pub type CaptureResult<T> = Result<T, String>;

fn is_own(title: &str) -> bool {
    OWN_TITLES.iter().any(|t| title == *t)
}

pub fn list_monitors() -> CaptureResult<Vec<MonitorInfo>> {
    let monitors = Monitor::all().map_err(|e| format!("cannot enumerate monitors: {e}"))?;
    let mut out = Vec::new();
    for m in monitors {
        // One unreadable monitor must not blank the whole list, so each
        // field is defaulted rather than propagated.
        out.push(MonitorInfo {
            id: m.id().unwrap_or(0),
            name: m.friendly_name().or_else(|_| m.name()).unwrap_or_default(),
            x: m.x().unwrap_or(0),
            y: m.y().unwrap_or(0),
            width: m.width().unwrap_or(0),
            height: m.height().unwrap_or(0),
            scale: m.scale_factor().unwrap_or(1.0),
            primary: m.is_primary().unwrap_or(false),
        });
    }
    Ok(out)
}

pub fn list_windows() -> CaptureResult<Vec<WindowInfo>> {
    let windows = Window::all().map_err(|e| format!("cannot enumerate windows: {e}"))?;
    let mut out = Vec::new();
    for w in windows {
        let title = w.title().unwrap_or_default();
        // An untitled window cannot be named as a target, and our own is
        // never a useful one.
        if title.trim().is_empty() || is_own(&title) {
            continue;
        }
        out.push(WindowInfo {
            id: w.id().unwrap_or(0),
            title,
            app: w.app_name().unwrap_or_default(),
            x: w.x().unwrap_or(0),
            y: w.y().unwrap_or(0),
            width: w.width().unwrap_or(0),
            height: w.height().unwrap_or(0),
            minimized: w.is_minimized().unwrap_or(false),
        });
    }
    Ok(out)
}

fn primary_monitor() -> CaptureResult<Monitor> {
    let monitors = Monitor::all().map_err(|e| format!("cannot enumerate monitors: {e}"))?;
    if monitors.is_empty() {
        return Err("no monitors reported by the system".into());
    }
    for m in &monitors {
        if m.is_primary().unwrap_or(false) {
            return Ok(m.clone());
        }
    }
    Ok(monitors[0].clone())
}

/// Best window whose title contains `needle`, case-insensitively.
///
/// Ranked rather than first-match: a title substring often hits several
/// windows (a browser's tabs, a tool window beside its main window), and the
/// largest non-minimized one is almost always the one a person meant.
fn find_window(needle: &str) -> CaptureResult<Window> {
    let needle_lc = needle.to_lowercase();
    let windows = Window::all().map_err(|e| format!("cannot enumerate windows: {e}"))?;
    let mut best: Option<(u64, Window)> = None;
    for w in windows {
        let title = w.title().unwrap_or_default();
        if title.trim().is_empty() || is_own(&title) {
            continue;
        }
        if !title.to_lowercase().contains(&needle_lc) {
            continue;
        }
        let minimized = w.is_minimized().unwrap_or(false);
        let area = w.width().unwrap_or(0) as u64 * w.height().unwrap_or(0) as u64;
        // Minimized windows sort below every visible one, whatever their size.
        let score = if minimized { area } else { area + u32::MAX as u64 };
        if best.as_ref().map(|(s, _)| score > *s).unwrap_or(true) {
            best = Some((score, w));
        }
    }
    best.map(|(_, w)| w)
        .ok_or_else(|| format!("no window title contains {needle:?}"))
}

fn stamp() -> String {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    format!("{nanos:x}")
}

fn shrink(image: RgbaImage, max_side: u32) -> RgbaImage {
    let (w, h) = (image.width(), image.height());
    let longest = w.max(h);
    if max_side == 0 || longest <= max_side {
        return image;
    }
    let ratio = max_side as f32 / longest as f32;
    let (nw, nh) = (((w as f32 * ratio) as u32).max(1), ((h as f32 * ratio) as u32).max(1));
    // Triangle: cheap, and softer than Nearest on text, which matters because
    // OCR runs on these.
    xcap::image::imageops::resize(&image, nw, nh, FilterType::Triangle)
}

fn save(repo_root: &Path, image: RgbaImage, target: &str) -> CaptureResult<CaptureInfo> {
    let dir = repo_root.join(CAPTURE_DIR);
    std::fs::create_dir_all(&dir).map_err(|e| format!("cannot create {}: {e}", dir.display()))?;
    let capture_id = stamp();
    let path: PathBuf = dir.join(format!("{capture_id}.png"));
    let (width, height) = (image.width(), image.height());
    image
        .save(&path)
        .map_err(|e| format!("cannot write {}: {e}", path.display()))?;
    let bytes = std::fs::metadata(&path).map(|m| m.len()).unwrap_or(0);
    Ok(CaptureInfo {
        capture_id,
        path: format!("{CAPTURE_DIR}/{}", path.file_name().unwrap().to_string_lossy()),
        width,
        height,
        bytes,
        target: target.to_string(),
    })
}

/// What to capture. `Screen` is the primary monitor rather than the whole
/// virtual desktop: on a multi-monitor setup the union is mostly empty space
/// and costs a model a lot of tokens to look at.
#[derive(Debug)]
pub enum Target {
    Screen,
    Monitor(u32),
    Window(String),
    Region { x: u32, y: u32, width: u32, height: u32 },
}

pub fn capture(repo_root: &Path, target: Target, max_side: u32) -> CaptureResult<CaptureInfo> {
    let (image, label) = match target {
        Target::Screen => {
            let m = primary_monitor()?;
            let img = m
                .capture_image()
                .map_err(|e| format!("screen capture failed: {e}"))?;
            (img, "screen".to_string())
        }
        Target::Monitor(id) => {
            let monitors = Monitor::all().map_err(|e| format!("cannot enumerate monitors: {e}"))?;
            let m = monitors
                .into_iter()
                .find(|m| m.id().unwrap_or(0) == id)
                .ok_or_else(|| format!("no monitor with id {id}"))?;
            let img = m
                .capture_image()
                .map_err(|e| format!("monitor capture failed: {e}"))?;
            (img, format!("monitor {id}"))
        }
        Target::Window(needle) => {
            let w = find_window(&needle)?;
            let title = w.title().unwrap_or_default();
            if w.is_minimized().unwrap_or(false) {
                // Say it rather than returning the blank frame a minimized
                // window gives back.
                return Err(format!("the window {title:?} is minimized - restore it first"));
            }
            let img = w
                .capture_image()
                .map_err(|e| format!("window capture failed: {e}"))?;
            (img, format!("window {title:?}"))
        }
        Target::Region { x, y, width, height } => {
            if width == 0 || height == 0 {
                return Err("a region needs a non-zero width and height".into());
            }
            let m = primary_monitor()?;
            let img = m
                .capture_region(x, y, width, height)
                .map_err(|e| format!("region capture failed: {e}"))?;
            (img, format!("region {width}x{height} at {x},{y}"))
        }
    };
    save(repo_root, shrink(image, max_side), &label)
}

/// Resolve a capture id back to its file, refusing anything that escapes the
/// capture directory. The bridge takes ids from a model's tool call, so this
/// is the boundary that stops `../../.env` being passed off as a capture.
pub fn path_for(repo_root: &Path, capture_id: &str) -> CaptureResult<PathBuf> {
    if capture_id.is_empty()
        || !capture_id
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || c == '-' || c == '_')
    {
        return Err(format!("not a capture id: {capture_id:?}"));
    }
    let path = repo_root.join(CAPTURE_DIR).join(format!("{capture_id}.png"));
    if !path.is_file() {
        return Err(format!("no capture {capture_id}"));
    }
    Ok(path)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn our_own_window_is_never_a_target() {
        assert!(is_own("Delivery Console"));
        assert!(!is_own("Delivery Console - Notepad"));
    }

    #[test]
    fn shrink_leaves_a_small_image_alone() {
        let img = RgbaImage::new(100, 50);
        let out = shrink(img, 1920);
        assert_eq!((out.width(), out.height()), (100, 50));
    }

    #[test]
    fn shrink_preserves_aspect_ratio() {
        let img = RgbaImage::new(3840, 2160);
        let out = shrink(img, 1920);
        assert_eq!((out.width(), out.height()), (1920, 1080));
    }

    #[test]
    fn shrink_uses_the_longest_edge_for_a_tall_image() {
        let img = RgbaImage::new(1000, 4000);
        let out = shrink(img, 1000);
        assert_eq!((out.width(), out.height()), (250, 1000));
    }

    #[test]
    fn a_max_side_of_zero_means_no_shrinking() {
        let img = RgbaImage::new(3840, 2160);
        let out = shrink(img, 0);
        assert_eq!(out.width(), 3840);
    }

    #[test]
    fn a_traversal_dressed_as_a_capture_id_is_refused() {
        // The ids reach here from a model's tool arguments.
        let root = std::env::temp_dir();
        for bad in ["../../.env", "a/b", "..", "", "id with space", "x.png"] {
            assert!(
                path_for(&root, bad).is_err(),
                "{bad:?} should not resolve to a path"
            );
        }
    }

    #[test]
    fn a_wellformed_but_absent_id_says_so() {
        let root = std::env::temp_dir();
        let err = path_for(&root, "deadbeef").unwrap_err();
        assert!(err.contains("no capture"), "{err}");
    }
}

//! Text out of a capture.
//!
//! ## Why OCR is worth having even with vision models
//!
//! Two reasons, and the second is the load-bearing one. A text-only model —
//! most local ones — cannot see a screenshot at all, so OCR is the difference
//! between "describe this error" working and not working. And a vision model
//! that CAN see pixels still costs an image's worth of tokens per turn and
//! reads small UI text unreliably; OCR of a dialog is cheaper and more exact.
//!
//! ## Two backends, chosen by what is actually present
//!
//! * **WinRT** (`Windows.Media.Ocr`) on Windows: ships with the OS, needs no
//!   model download and no build tooling. This is the one verified here.
//! * **`tesseract`** as a process, anywhere it is on PATH: the substitute for
//!   macOS and Linux, so the capability degrades rather than disappearing on
//!   those platforms. **Not exercised on this machine** — tesseract is not
//!   installed here, so the code path is written but unproven, and it says so
//!   rather than implying otherwise.
//!
//! Neither present is reported as unavailable with an install hint, never as
//! empty text — "no text found" and "no OCR engine" are different answers and
//! a model must be able to tell them apart.

use std::path::Path;

use serde::Serialize;

pub type OcrResultT<T> = Result<T, String>;

#[derive(Serialize, Debug)]
pub struct Line {
    pub text: String,
    pub x: i32,
    pub y: i32,
    pub width: i32,
    pub height: i32,
}

#[derive(Serialize, Debug)]
pub struct Recognized {
    pub text: String,
    pub lines: Vec<Line>,
    pub engine: String,
    pub language: String,
}

/// Is any OCR engine usable right now? Drives `/health`'s `caps.ocr`, so it
/// must answer for THIS machine, not for the platform in principle.
pub fn available() -> bool {
    #[cfg(windows)]
    {
        if winrt::engine_ready() {
            return true;
        }
    }
    tesseract_path().is_some()
}

pub fn recognize(path: &Path) -> OcrResultT<Recognized> {
    // Checked here, once, before any engine is involved: an engine asked
    // about a file that does not exist is entitled to do anything, and the
    // answer a caller needs is "that capture is gone", not an engine error.
    if !path.is_file() {
        return Err(format!("no such capture: {}", path.display()));
    }
    #[cfg(windows)]
    {
        match winrt::recognize(path) {
            Ok(result) => return Ok(result),
            Err(e) => {
                // Fall through to tesseract rather than failing outright: a
                // machine with no OCR language pack can still have tesseract.
                log::warn!("ocr: WinRT failed ({e}), trying tesseract");
            }
        }
    }
    match tesseract_path() {
        Some(exe) => tesseract_recognize(&exe, path),
        None => Err(no_engine_hint()),
    }
}

fn no_engine_hint() -> String {
    if cfg!(windows) {
        "no OCR engine: WinRT OCR needs a language pack (Settings > Time & \
         language > Language & region), or put `tesseract` on PATH"
            .into()
    } else if cfg!(target_os = "macos") {
        "no OCR engine: install tesseract (`brew install tesseract`)".into()
    } else {
        "no OCR engine: install tesseract (`apt install tesseract-ocr`)".into()
    }
}

// -- tesseract, the cross-platform substitute --------------------------------

fn tesseract_path() -> Option<std::path::PathBuf> {
    let exe = if cfg!(windows) { "tesseract.exe" } else { "tesseract" };
    std::env::var_os("PATH").and_then(|paths| {
        std::env::split_paths(&paths)
            .map(|dir| dir.join(exe))
            .find(|candidate| candidate.is_file())
    })
}

fn tesseract_recognize(exe: &Path, path: &Path) -> OcrResultT<Recognized> {
    // `-` writes plain text to stdout, so there is no temp file to clean up.
    let mut cmd = std::process::Command::new(exe);
    cmd.arg(path).arg("-").arg("--psm").arg("3");
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x0800_0000); // CREATE_NO_WINDOW
    }
    let out = cmd
        .output()
        .map_err(|e| format!("cannot run tesseract: {e}"))?;
    if !out.status.success() {
        let why = String::from_utf8_lossy(&out.stderr);
        return Err(format!("tesseract failed: {}", why.trim()));
    }
    let text = String::from_utf8_lossy(&out.stdout).trim().to_string();
    // Plain-text output carries no geometry. Reporting empty rects rather
    // than inventing them keeps "we do not know where" honest.
    let lines = text
        .lines()
        .filter(|l| !l.trim().is_empty())
        .map(|l| Line {
            text: l.to_string(),
            x: 0,
            y: 0,
            width: 0,
            height: 0,
        })
        .collect();
    Ok(Recognized {
        text,
        lines,
        engine: "tesseract".into(),
        language: String::new(),
    })
}

// -- WinRT -------------------------------------------------------------------

#[cfg(windows)]
mod winrt {
    use super::{Line, OcrResultT, Recognized};
    use std::path::Path;

    use windows::Graphics::Imaging::{BitmapPixelFormat, SoftwareBitmap};
    use windows::Media::Ocr::OcrEngine;
    use windows::Security::Cryptography::CryptographicBuffer;
    use windows::Win32::System::WinRT::{RoInitialize, RO_INIT_MULTITHREADED};

    /// WinRT class activation needs an initialised apartment, and the bridge's
    /// worker threads have none. `RPC_E_CHANGED_MODE` means someone already
    /// initialised this thread differently, which is fine — the OCR classes do
    /// not care which apartment they are in.
    /// Initialise the worker thread's apartment. Called exactly once, on the
    /// thread that will make every WinRT call for the life of the process, so
    /// there is no matching `RoUninitialize` — the process exiting is it.
    fn init_apartment() -> bool {
        // Called only on the thread `on_winrt_thread` just created, so this
        // should always be the first initialisation that thread has seen.
        // CHANGED_MODE is still tolerated rather than fatal — being wrong
        // about that should degrade OCR, not take the shell down — but it is
        // NOT ours to uninitialise in that case.
        const RPC_E_CHANGED_MODE: i32 = -2147417850; // 0x80010106
        unsafe {
            match RoInitialize(RO_INIT_MULTITHREADED) {
                Ok(()) => true,
                // Nothing else should have initialised this thread, but if
                // something did, WinRT still works — it is just not ours.
                Err(e) if e.code().0 == RPC_E_CHANGED_MODE => false,
                Err(e) => {
                    log::warn!("ocr: RoInitialize said {e}");
                    false
                }
            }
        }
    }

    /// Every WinRT call in this module runs on ONE long-lived thread.
    ///
    /// The road here is worth recording, because two plausible designs both
    /// crashed. Calling WinRT on whatever thread the bridge handed us died
    /// with an access violation once `arboard` had put that thread in a
    /// single-threaded apartment. Giving each call its own thread, with
    /// `RoInitialize`/`RoUninitialize` paired around it, then corrupted the
    /// heap (0xC0000374) and later crashed again on the second call —
    /// initialising and tearing down an apartment repeatedly in a process
    /// that has WinRT loaded is not something to do casually.
    ///
    /// So: one thread, one apartment, initialised once and never torn down
    /// (the process exiting is the teardown), and calls serialised through a
    /// channel. OCR is not a concurrency problem — a screenshot at a time is
    /// exactly the load — so serialising costs nothing and removes the whole
    /// class of apartment bug.
    type Job = Box<dyn FnOnce() + Send + 'static>;

    fn worker() -> Option<&'static std::sync::mpsc::Sender<Job>> {
        static WORKER: std::sync::OnceLock<Option<std::sync::mpsc::Sender<Job>>> =
            std::sync::OnceLock::new();
        WORKER
            .get_or_init(|| {
                let (tx, rx) = std::sync::mpsc::channel::<Job>();
                let spawned = std::thread::Builder::new()
                    .name("winrt-ocr".into())
                    .spawn(move || {
                        init_apartment();
                        // Ends when every sender is dropped, which for a
                        // `OnceLock`-held sender means at process exit.
                        while let Ok(job) = rx.recv() {
                            job();
                        }
                    });
                match spawned {
                    Ok(_handle) => Some(tx),
                    Err(e) => {
                        log::warn!("ocr: cannot start the WinRT thread: {e}");
                        None
                    }
                }
            })
            .as_ref()
    }

    fn on_winrt_thread<T, F>(work: F) -> OcrResultT<T>
    where
        T: Send + 'static,
        F: FnOnce() -> OcrResultT<T> + Send + 'static,
    {
        let sender = worker().ok_or("the OCR thread could not be started")?;
        let (tx, rx) = std::sync::mpsc::channel();
        sender
            .send(Box::new(move || {
                // A panic inside `work` would drop `tx` and surface below as
                // "the OCR thread stopped answering" rather than killing the
                // worker silently.
                let _ = tx.send(work());
            }))
            .map_err(|_| "the OCR thread is gone".to_string())?;
        rx.recv()
            .map_err(|_| "the OCR thread stopped answering".to_string())?
    }

    pub fn engine_ready() -> bool {
        on_winrt_thread(|| {
            OcrEngine::TryCreateFromUserProfileLanguages()
                .map(|_| ())
                .map_err(|e| e.to_string())
        })
        .is_ok()
    }

    pub fn recognize(path: &Path) -> OcrResultT<Recognized> {
        let owned = path.to_path_buf();
        on_winrt_thread(move || recognize_here(&owned))
    }

    fn recognize_here(path: &Path) -> OcrResultT<Recognized> {
        let engine = OcrEngine::TryCreateFromUserProfileLanguages()
            .map_err(|e| format!("no WinRT OCR engine for your languages: {e}"))?;
        let language = engine
            .RecognizerLanguage()
            .and_then(|l| l.LanguageTag())
            .map(|t| t.to_string_lossy())
            .unwrap_or_default();

        let image = xcap::image::open(path)
            .map_err(|e| format!("cannot open {}: {e}", path.display()))?;
        let mut rgba = image.to_rgba8();

        // The engine refuses an image past its own limit, so downscale to fit
        // rather than handing it something it will reject.
        if let Ok(max) = OcrEngine::MaxImageDimension() {
            let longest = rgba.width().max(rgba.height());
            if max > 0 && longest > max {
                let ratio = max as f32 / longest as f32;
                let (w, h) = (
                    ((rgba.width() as f32 * ratio) as u32).max(1),
                    ((rgba.height() as f32 * ratio) as u32).max(1),
                );
                rgba = xcap::image::imageops::resize(
                    &rgba, w, h, xcap::image::imageops::FilterType::Triangle);
            }
        }

        let (width, height) = (rgba.width() as i32, rgba.height() as i32);
        // WinRT wants BGRA; the image crate gives RGBA. Swapping in place
        // beats allocating a second buffer the size of a screenshot.
        let mut bgra = rgba.into_raw();
        for px in bgra.chunks_exact_mut(4) {
            px.swap(0, 2);
        }

        let buffer = CryptographicBuffer::CreateFromByteArray(&bgra)
            .map_err(|e| format!("cannot wrap the pixels for WinRT: {e}"))?;
        let bitmap = SoftwareBitmap::CreateCopyFromBuffer(
            &buffer, BitmapPixelFormat::Bgra8, width, height)
            .map_err(|e| format!("cannot build a bitmap for WinRT: {e}"))?;

        // `get()` blocks until the operation completes. That is what is
        // wanted here: the bridge's worker thread is already dedicated to this
        // one request, and adding an async runtime for a single call would put
        // a second executor beside Tauri's for no benefit.
        let result = engine
            .RecognizeAsync(&bitmap)
            .map_err(|e| format!("OCR would not start: {e}"))?
            .get()
            .map_err(|e| format!("OCR failed: {e}"))?;
        let text = result
            .Text()
            .map(|t| t.to_string_lossy())
            .unwrap_or_default();

        let mut lines = Vec::new();
        if let Ok(ocr_lines) = result.Lines() {
            for line in ocr_lines {
                let line_text = line
                    .Text()
                    .map(|t| t.to_string_lossy())
                    .unwrap_or_default();
                // A line has no rect of its own; its extent is the union of
                // its words'.
                let (mut x0, mut y0, mut x1, mut y1) =
                    (i32::MAX, i32::MAX, i32::MIN, i32::MIN);
                if let Ok(words) = line.Words() {
                    for word in words {
                        if let Ok(r) = word.BoundingRect() {
                            x0 = x0.min(r.X as i32);
                            y0 = y0.min(r.Y as i32);
                            x1 = x1.max((r.X + r.Width) as i32);
                            y1 = y1.max((r.Y + r.Height) as i32);
                        }
                    }
                }
                let known = x0 != i32::MAX;
                lines.push(Line {
                    text: line_text,
                    x: if known { x0 } else { 0 },
                    y: if known { y0 } else { 0 },
                    width: if known { x1 - x0 } else { 0 },
                    height: if known { y1 - y0 } else { 0 },
                });
            }
        }

        Ok(Recognized {
            text,
            lines,
            engine: "winrt".into(),
            language,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_missing_engine_hint_names_something_installable() {
        // A model relays this to a person, so "unavailable" is not enough —
        // it has to say what to do about it.
        let hint = no_engine_hint();
        assert!(hint.contains("no OCR engine"));
        assert!(hint.contains("tesseract") || hint.contains("language pack"));
    }

    #[test]
    fn a_missing_file_is_an_error_not_empty_text() {
        // Empty text would read as "the screen had no words on it".
        let missing = std::env::temp_dir().join("t005-does-not-exist.png");
        let err = recognize(&missing).unwrap_err();
        assert!(err.contains("no such capture"), "{err}");
    }

    #[test]
    fn ocr_survives_the_clipboard_having_touched_com_first() {
        // Regression: `arboard` puts the calling thread in a single-threaded
        // apartment, and WinRT class activation on that thread crashed the
        // whole test binary with an access violation. OCR now owns its
        // thread; this test is the thing that would notice if it stopped.
        let _ = crate::clipboard::peek();
        assert!(available() || !available(), "the probe must not crash");
        let missing = std::env::temp_dir().join("t005-after-com.png");
        assert!(recognize(&missing).is_err());
    }

    /// Round-trip against the real engine: render known words, read them back.
    /// Skipped loudly where no engine is installed.
    #[test]
    fn recognizes_text_it_was_given() {
        if !available() {
            eprintln!("skipped: {}", no_engine_hint());
            return;
        }
        let path = std::env::temp_dir().join(format!("t005-ocr-{}.png", std::process::id()));
        write_probe_png(&path);
        let out = recognize(&path).expect("an available engine should read this");
        let seen = out.text.to_uppercase().replace(' ', "");
        let _ = std::fs::remove_file(&path);
        // Always reported, pass or fail. A hardware test that says only "ok"
        // cannot be told apart from one that skipped, and this one is the
        // sole proof that pixels actually reach text on this machine.
        eprintln!("ocr: engine={} language={} read {:?}", out.engine, out.language, out.text);
        assert!(
            seen.contains("HELLO"),
            "engine={} language={} read {:?}",
            out.engine, out.language, out.text
        );
    }

    /// "HELLO" in 5x7 block glyphs, scaled up — big, high-contrast and
    /// unambiguous, because the point is to prove the pipeline carries pixels
    /// to text, not to benchmark the engine on small fonts.
    fn write_probe_png(path: &std::path::Path) {
        const GLYPHS: [[&str; 7]; 5] = [
            // H
            ["#   #", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
            // E
            ["#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#####"],
            // L
            ["#    ", "#    ", "#    ", "#    ", "#    ", "#    ", "#####"],
            // L
            ["#    ", "#    ", "#    ", "#    ", "#    ", "#    ", "#####"],
            // O
            [" ### ", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "],
        ];
        let scale = 14u32;
        let pad = 40u32;
        let cell_w = 6u32; // 5 columns plus one blank
        let width = pad * 2 + scale * cell_w * GLYPHS.len() as u32;
        let height = pad * 2 + scale * 7;
        let mut img = xcap::image::RgbaImage::from_pixel(
            width, height, xcap::image::Rgba([255, 255, 255, 255]));
        for (gi, glyph) in GLYPHS.iter().enumerate() {
            for (row, line) in glyph.iter().enumerate() {
                for (col, ch) in line.chars().enumerate() {
                    if ch != '#' {
                        continue;
                    }
                    let x0 = pad + scale * (gi as u32 * cell_w + col as u32);
                    let y0 = pad + scale * row as u32;
                    for dy in 0..scale {
                        for dx in 0..scale {
                            img.put_pixel(x0 + dx, y0 + dy,
                                          xcap::image::Rgba([0, 0, 0, 255]));
                        }
                    }
                }
            }
        }
        img.save(path).expect("write the probe png");
    }
}

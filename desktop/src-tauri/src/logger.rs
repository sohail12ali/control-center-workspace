//! Rotating file logger for the desktop host.
//!
//! `console/.cache/desktop/host.log`, append, rotated to `.1` (replacing any
//! previous `.1`) once the current file reaches 1 MiB. Timestamps are UTC,
//! computed by hand from `SystemTime` — no `chrono` dependency, just the
//! well-known days-since-epoch <-> civil-date algorithm (Howard Hinnant,
//! `civil_from_days`).
//!
//! Debug/console output is gone now that the host is an unconditional GUI
//! subsystem (see `main.rs`), so this file is the only audit trail for
//! lifecycle events and the errors `tray.rs` used to swallow silently.

use std::fs::{self, File, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::Mutex;
use std::time::{SystemTime, UNIX_EPOCH};

use log::{LevelFilter, Log, Metadata, Record};

/// Rotate once the current file reaches this size.
pub const MAX_BYTES: u64 = 1024 * 1024; // 1 MiB

pub struct FileLogger {
    path: PathBuf,
    max_bytes: u64,
    file: Mutex<Option<File>>,
}

impl FileLogger {
    fn open(path: &Path) -> std::io::Result<File> {
        if let Some(dir) = path.parent() {
            fs::create_dir_all(dir)?;
        }
        OpenOptions::new().create(true).append(true).open(path)
    }

    fn rotated_path(path: &Path) -> PathBuf {
        let mut s = path.as_os_str().to_os_string();
        s.push(".1");
        PathBuf::from(s)
    }

    fn with_limit(path: PathBuf, max_bytes: u64) -> std::io::Result<Self> {
        let file = Self::open(&path)?;
        Ok(FileLogger {
            path,
            max_bytes,
            file: Mutex::new(Some(file)),
        })
    }

    fn new(path: PathBuf) -> std::io::Result<Self> {
        Self::with_limit(path, MAX_BYTES)
    }

    /// Install this as the process-wide `log` sink. Best-effort by design —
    /// a directory that cannot be created must not stop the shell from
    /// starting, so the caller treats a failure as non-fatal.
    pub fn init(path: PathBuf) -> Result<(), String> {
        let logger = Self::new(path).map_err(|e| e.to_string())?;
        log::set_boxed_logger(Box::new(logger)).map_err(|e| e.to_string())?;
        log::set_max_level(LevelFilter::Info);
        Ok(())
    }

    /// Rotate first if the write would otherwise push the file past the
    /// limit, then append. Every failure here is swallowed on purpose: a
    /// disk-full or permission error must not crash the host it is trying to
    /// audit.
    fn write_line(&self, line: &str) {
        let mut guard = match self.file.lock() {
            Ok(g) => g,
            Err(_) => return,
        };
        let over_limit = guard
            .as_ref()
            .and_then(|f| f.metadata().ok())
            .map(|m| m.len() >= self.max_bytes)
            .unwrap_or(false);
        if over_limit {
            // Close the handle before renaming — Windows refuses to rename a
            // file that is still open under a non-share-delete handle.
            *guard = None;
            let rotated = Self::rotated_path(&self.path);
            let _ = fs::remove_file(&rotated);
            let _ = fs::rename(&self.path, &rotated);
            *guard = Self::open(&self.path).ok();
        }
        if let Some(f) = guard.as_mut() {
            let _ = f.write_all(line.as_bytes());
        }
    }
}

impl Log for FileLogger {
    fn enabled(&self, metadata: &Metadata) -> bool {
        metadata.level() <= log::Level::Info
    }

    fn log(&self, record: &Record) {
        if !self.enabled(record.metadata()) {
            return;
        }
        let line = format!(
            "{} [{}] {}: {}\n",
            format_utc_now(),
            record.level(),
            record.target(),
            record.args()
        );
        self.write_line(&line);
    }

    fn flush(&self) {
        if let Ok(mut guard) = self.file.lock() {
            if let Some(f) = guard.as_mut() {
                let _ = f.flush();
            }
        }
    }
}

/// Days-since-epoch -> (year, month, day). `z` may be negative (pre-1970);
/// not reachable from `format_utc_now` but kept correct since it is cheap.
/// Algorithm: Howard Hinnant, http://howardhinnant.github.io/date_algorithms.html#civil_from_days
fn civil_from_days(z: i64) -> (i64, u32, u32) {
    let z = z + 719_468;
    let era = if z >= 0 { z } else { z - 146_096 } / 146_097;
    let doe = (z - era * 146_097) as u64; // [0, 146096]
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365; // [0, 399]
    let y = yoe as i64 + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100); // [0, 365]
    let mp = (5 * doy + 2) / 153; // [0, 11]
    let d = (doy - (153 * mp + 2) / 5 + 1) as u32; // [1, 31]
    let m = if mp < 10 { mp + 3 } else { mp - 9 } as u32; // [1, 12]
    let y = if m <= 2 { y + 1 } else { y };
    (y, m, d)
}

fn format_utc(secs_since_epoch: i64, millis: u32) -> String {
    let days = secs_since_epoch.div_euclid(86_400);
    let secs_of_day = secs_since_epoch.rem_euclid(86_400);
    let (y, m, d) = civil_from_days(days);
    let hh = secs_of_day / 3600;
    let mm = (secs_of_day % 3600) / 60;
    let ss = secs_of_day % 60;
    format!(
        "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}.{:03}Z",
        y, m, d, hh, mm, ss, millis
    )
}

fn format_utc_now() -> String {
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default();
    format_utc(now.as_secs() as i64, now.subsec_millis())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn scratch_path(name: &str) -> PathBuf {
        let mut p = std::env::temp_dir();
        p.push(format!(
            "delivery-console-logger-test-{}-{}-{}",
            std::process::id(),
            name,
            SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap_or_default()
                .as_nanos()
        ));
        p.push("host.log");
        p
    }

    #[test]
    fn utc_formatting_matches_known_instants() {
        assert_eq!(format_utc(0, 0), "1970-01-01T00:00:00.000Z");
        assert_eq!(format_utc(1_700_000_000, 123), "2023-11-14T22:13:20.123Z");
        assert_eq!(format_utc(1_234_567_890, 0), "2009-02-13T23:31:30.000Z");
        // A leap-year/leap-day boundary, and the turn of a century.
        assert_eq!(format_utc(946_684_799, 999), "1999-12-31T23:59:59.999Z");
        assert_eq!(format_utc(946_684_800, 0), "2000-01-01T00:00:00.000Z");
    }

    #[test]
    fn rotates_past_the_limit_with_no_data_loss() {
        let path = scratch_path("rotate");
        let dir = path.parent().unwrap().to_path_buf();
        // A small limit keeps the test fast without changing the logic under
        // test — rotation is size-triggered, not constant-triggered. The
        // limit is checked against the file's size BEFORE each write, so
        // crossing it takes effect on the NEXT call, never splitting a line
        // across both files.
        let logger = FileLogger::with_limit(path.clone(), 200).expect("open logger");

        let rotated = FileLogger::rotated_path(&path);
        assert!(!rotated.exists());

        logger.write_line("first line, short\n"); // well under 200 bytes
        assert!(!rotated.exists(), "must not rotate before the limit is crossed");

        let long_line = format!("{}\n", "x".repeat(250));
        logger.write_line(&long_line); // file now > 200 bytes
        assert!(!rotated.exists(), "rotation is decided on the next write, not mid-write");

        logger.write_line("after the limit\n"); // finds the file over the limit -> rotates first
        assert!(rotated.exists(), "expected a .1 file once a write finds the file over the limit");

        let rotated_contents = fs::read_to_string(&rotated).unwrap();
        assert!(rotated_contents.contains("first line, short"));
        assert!(rotated_contents.contains(&"x".repeat(250)));

        let current_contents = fs::read_to_string(&path).unwrap();
        assert_eq!(current_contents, "after the limit\n");

        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn a_second_rotation_replaces_the_previous_dot_one() {
        let path = scratch_path("rotate-twice");
        let dir = path.parent().unwrap().to_path_buf();
        let logger = FileLogger::with_limit(path.clone(), 50).expect("open logger");

        logger.write_line(&format!("{}\n", "a".repeat(60))); // rotates on next write
        logger.write_line("marker-one\n"); // triggers rotation #1, "a..." -> .1
        logger.write_line(&format!("{}\n", "b".repeat(60)));
        logger.write_line("marker-two\n"); // triggers rotation #2, replaces .1

        let rotated = FileLogger::rotated_path(&path);
        let rotated_contents = fs::read_to_string(&rotated).unwrap();
        assert!(rotated_contents.contains(&"b".repeat(60)));
        assert!(!rotated_contents.contains(&"a".repeat(60)));

        let _ = fs::remove_dir_all(&dir);
    }
}

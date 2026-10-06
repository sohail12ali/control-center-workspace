//! Headless replay: feed a take from a WAV file instead of a microphone.
//!
//! Exists so the capture path (VAD, endpointing, pre-roll, caps) can be
//! exercised with no audio device, with the same input every run. It is the
//! `Frames` implementation that is not hardware; `Mic` is the other.
//!
//! ## Time is samples
//!
//! A file source never sleeps. It hands out one VAD frame per read and the
//! take clock counts the samples it was given, so a 20 s file replays in a
//! few milliseconds and ends at the same sample every time.
//!
//! ## The cursor is the playhead
//!
//! `cursor()` is how far the file has been consumed. A take starts there and
//! leaves it where the take ended, so the next take carries on with the rest
//! of the file. That is what lets one file hold two utterances.
//!
//! ## The end of the file
//!
//! A file source has a last sample, a microphone does not. After it, `since`
//! returns nothing and `exhausted()` is true; the capture loop treats that as
//! "nothing more is coming" and ends the take rather than waiting on a sample
//! clock that can no longer advance.
//!
//! The WAV reader is hand-written for the same reason `Take::wav` is: 16-bit
//! PCM is a 44-byte header, and a crate for it would be the bigger decision.

use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::{Arc, Mutex, OnceLock};
use std::time::Duration;

use crate::audio::{self, AudioResult, Frames, FRAME, TARGET_HZ};

/// A 16-bit PCM WAV: channels, sample rate, interleaved samples.
pub struct Wav {
    pub channels: u16,
    pub hz: u32,
    pub samples: Vec<i16>,
}

/// Parse a RIFF/WAVE file held in memory. Only 16-bit PCM, which is what the
/// recogniser, Piper and `Take::wav` all produce; anything else is a clear
/// error rather than garbage audio.
pub fn parse_wav(bytes: &[u8]) -> AudioResult<Wav> {
    if bytes.len() < 12 || &bytes[0..4] != b"RIFF" || &bytes[8..12] != b"WAVE" {
        return Err("not a RIFF/WAVE file".into());
    }
    let mut at = 12usize;
    let mut fmt: Option<(u16, u16, u32, u16)> = None;
    while at + 8 <= bytes.len() {
        let id = &bytes[at..at + 4];
        let size = u32::from_le_bytes([bytes[at + 4], bytes[at + 5], bytes[at + 6], bytes[at + 7]]) as usize;
        let body = at + 8;
        // A streaming writer may leave the size at 0 or 0xFFFFFFFF; whatever
        // the header claims, never read past what is actually there.
        let end = body.saturating_add(size).min(bytes.len());
        if id == b"fmt " {
            if end - body < 16 {
                return Err("the WAV fmt chunk is truncated".into());
            }
            let f = &bytes[body..end];
            fmt = Some((
                u16::from_le_bytes([f[0], f[1]]),
                u16::from_le_bytes([f[2], f[3]]),
                u32::from_le_bytes([f[4], f[5], f[6], f[7]]),
                u16::from_le_bytes([f[14], f[15]]),
            ));
        } else if id == b"data" {
            let (tag, channels, hz, bits) = fmt.ok_or("the WAV has no fmt chunk before its data")?;
            // 1 = PCM; 0xFFFE = extensible, which carries PCM in practice.
            if (tag != 1 && tag != 0xFFFE) || bits != 16 {
                return Err(format!(
                    "only 16-bit PCM WAV is supported (this is format {tag}, {bits}-bit)"
                ));
            }
            if channels == 0 || hz == 0 {
                return Err("the WAV reports zero channels or a zero sample rate".into());
            }
            let samples = bytes[body..end]
                .chunks_exact(2)
                .map(|b| i16::from_le_bytes([b[0], b[1]]))
                .collect();
            return Ok(Wav { channels, hz, samples });
        }
        at = match body.checked_add(size).and_then(|n| n.checked_add(size & 1)) {
            Some(next) => next,
            None => break,
        };
    }
    Err("the WAV has no data chunk".into())
}

/// A RIFF/WAVE file in memory: 44-byte header, then 16-bit mono PCM at `hz`.
/// The one place this header is written (`audio::Take::wav` and the TTS file
/// sink both use it).
pub fn wav_bytes(samples: &[i16], hz: u32) -> Vec<u8> {
    let data_len = (samples.len() * 2) as u32;
    let mut out = Vec::with_capacity(44 + data_len as usize);
    out.extend_from_slice(b"RIFF");
    out.extend_from_slice(&(36 + data_len).to_le_bytes());
    out.extend_from_slice(b"WAVEfmt ");
    out.extend_from_slice(&16u32.to_le_bytes()); // fmt chunk size
    out.extend_from_slice(&1u16.to_le_bytes()); // PCM
    out.extend_from_slice(&1u16.to_le_bytes()); // mono
    out.extend_from_slice(&hz.to_le_bytes());
    out.extend_from_slice(&(hz * 2).to_le_bytes()); // byte rate
    out.extend_from_slice(&2u16.to_le_bytes()); // block align
    out.extend_from_slice(&16u16.to_le_bytes()); // bits per sample
    out.extend_from_slice(b"data");
    out.extend_from_slice(&data_len.to_le_bytes());
    for s in samples {
        out.extend_from_slice(&s.to_le_bytes());
    }
    out
}

/// Write `samples` to `path` as a WAV, replacing whatever was there.
pub fn write_wav(path: &Path, samples: &[i16], hz: u32) -> Result<(), String> {
    std::fs::write(path, wav_bytes(samples, hz))
        .map_err(|e| format!("cannot write the WAV {}: {e}", path.display()))
}

/// Silence appended after a replayed file's last sample so that its last
/// utterance can close. The settings are read per take but the file is loaded
/// once, so this covers the largest values the console accepts rather than
/// the current ones: end-of-speech silence or first pause (5 s) + merge window
/// (5 s) + half a second to spare. Silence the take never reaches costs
/// nothing, because a file feeds without sleeping.
pub const TAIL: Duration = Duration::from_millis(5_000 + 5_000 + 500);

/// What a take reads: a microphone or a replayed file, behind one trait.
pub type Input = Box<dyn Frames>;

/// The environment's say over where audio comes from, read ONCE.
///
/// `CC_REPLAY_WAV` swaps the microphone for a file; `CC_TTS_SINK_WAV` swaps the
/// speaker for one. Both are the process owner's to set and nobody else's:
/// they are not settings, not a bridge route and not a console key (D-1), so
/// no page or request can make the shell listen to a file. Held in a value and
/// passed explicitly so tests build their own instead of mutating the process
/// environment under each other.
pub struct ReplayConfig {
    wav: Option<PathBuf>,
    sink: Option<PathBuf>,
    /// The loaded file and its playhead, shared by every take and every reopen
    /// so the cursor persists (FR-3): dropping a reader never rewinds it.
    playhead: Mutex<Option<Arc<FileFrames>>>,
    warned: AtomicBool,
}

impl ReplayConfig {
    pub fn new(wav: Option<PathBuf>, sink: Option<PathBuf>) -> Self {
        Self { wav, sink, playhead: Mutex::new(None), warned: AtomicBool::new(false) }
    }

    pub fn from_env() -> Self {
        let var = |name: &str| {
            std::env::var_os(name).filter(|v| !v.is_empty()).map(PathBuf::from)
        };
        Self::new(var("CC_REPLAY_WAV"), var("CC_TTS_SINK_WAV"))
    }

    /// Is a file standing in for the microphone?
    pub fn replaying(&self) -> bool {
        self.wav.is_some()
    }

    /// `"file"` or `"mic"`, for `/listen/state`.
    pub fn source_name(&self) -> &'static str {
        if self.replaying() { "file" } else { "mic" }
    }

    pub fn sink(&self) -> Option<&Path> {
        self.sink.as_deref()
    }

    /// The warning for the first use of a replay, once. Names the file and
    /// nothing from inside it. `None` when not replaying or already said.
    pub fn first_use_warning(&self) -> Option<String> {
        let path = self.wav.as_ref()?;
        if self.warned.swap(true, Ordering::SeqCst) {
            return None;
        }
        Some(format!(
            "replay: audio comes from the file {} instead of a microphone (CC_REPLAY_WAV)",
            path.display()
        ))
    }

    /// What a take reads from: the replay file's shared playhead, else a
    /// freshly opened microphone.
    pub fn open_input(&self) -> AudioResult<Input> {
        let Some(path) = &self.wav else {
            return Ok(Box::new(audio::Mic::open()?));
        };
        let shared = {
            let mut slot = self.playhead.lock().unwrap_or_else(|e| e.into_inner());
            match slot.as_ref() {
                Some(file) => file.clone(),
                None => {
                    // "microphone" is in the text on purpose: the hands-free
                    // loop stops on that word instead of retrying forever.
                    let file = Arc::new(FileFrames::open(path, TAIL).map_err(|e| {
                        format!("{e} (CC_REPLAY_WAV stands in for the microphone)")
                    })?);
                    *slot = Some(file.clone());
                    file
                }
            }
        };
        if let Some(warning) = self.first_use_warning() {
            log::warn!("{warning}");
        }
        Ok(Box::new(shared))
    }
}

/// The process's configuration, read from the environment on first use.
pub fn config() -> &'static ReplayConfig {
    static CONFIG: OnceLock<ReplayConfig> = OnceLock::new();
    CONFIG.get_or_init(ReplayConfig::from_env)
}

/// A WAV file as a frame source.
pub struct FileFrames {
    /// 16 kHz mono, trailing silence already appended.
    samples: Vec<i16>,
    /// The playhead: how many samples have been handed out.
    pos: AtomicU64,
}

impl FileFrames {
    /// From samples already at 16 kHz mono, then `tail` of silence.
    pub fn from_samples(mut samples: Vec<i16>, tail: Duration) -> Self {
        let tail_samples = tail.as_millis() as usize * TARGET_HZ as usize / 1000;
        samples.resize(samples.len() + tail_samples, 0);
        Self { samples, pos: AtomicU64::new(0) }
    }

    /// From a WAV in any rate and channel count, converted the way a
    /// microphone's audio is.
    pub fn from_wav(wav: Wav, tail: Duration) -> Self {
        let mono = if wav.channels == 1 && wav.hz == TARGET_HZ {
            wav.samples
        } else {
            let as_f32: Vec<f32> = wav.samples.iter().map(|s| *s as f32 / i16::MAX as f32).collect();
            audio::to_mono_16k(&as_f32, wav.channels, wav.hz)
        };
        Self::from_samples(mono, tail)
    }

    pub fn open(path: &Path, tail: Duration) -> AudioResult<Self> {
        let bytes = std::fs::read(path)
            .map_err(|e| format!("cannot read the replay file {}: {e}", path.display()))?;
        let wav = parse_wav(&bytes).map_err(|e| format!("replay file {}: {e}", path.display()))?;
        Ok(Self::from_wav(wav, tail))
    }

    /// Samples held, trailing silence included.
    #[cfg(test)]
    pub fn len(&self) -> usize {
        self.samples.len()
    }
}

impl Frames for FileFrames {
    fn cursor(&self) -> u64 {
        self.pos.load(Ordering::SeqCst)
    }

    /// One frame from `cursor`, and where to read next. A frame at a time so
    /// the take that is reading stops exactly where it ends, and the next take
    /// starts there.
    fn since(&self, cursor: u64) -> (u64, Vec<i16>) {
        let start = (cursor as usize).min(self.samples.len());
        let end = (start + FRAME).min(self.samples.len());
        self.pos.fetch_max(end as u64, Ordering::SeqCst);
        (end as u64, self.samples[start..end].to_vec())
    }

    fn rewound(&self, preroll: Duration) -> u64 {
        let back = preroll.as_millis() as u64 * TARGET_HZ as u64 / 1000;
        self.cursor().saturating_sub(back)
    }

    fn exhausted(&self) -> bool {
        self.cursor() as usize >= self.samples.len()
    }
}

/// The shared handle `ReplayConfig::open_input` hands out.
impl Frames for Arc<FileFrames> {
    fn cursor(&self) -> u64 {
        (**self).cursor()
    }
    fn since(&self, cursor: u64) -> (u64, Vec<i16>) {
        (**self).since(cursor)
    }
    fn rewound(&self, preroll: Duration) -> u64 {
        (**self).rewound(preroll)
    }
    fn exhausted(&self) -> bool {
        (**self).exhausted()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::{Arc, Mutex};

    fn wav_bytes(channels: u16, hz: u32, samples: &[i16]) -> Vec<u8> {
        let data_len = (samples.len() * 2) as u32;
        let mut out = Vec::new();
        out.extend_from_slice(b"RIFF");
        out.extend_from_slice(&(36 + data_len).to_le_bytes());
        out.extend_from_slice(b"WAVEfmt ");
        out.extend_from_slice(&16u32.to_le_bytes());
        out.extend_from_slice(&1u16.to_le_bytes());
        out.extend_from_slice(&channels.to_le_bytes());
        out.extend_from_slice(&hz.to_le_bytes());
        out.extend_from_slice(&(hz * 2 * channels as u32).to_le_bytes());
        out.extend_from_slice(&(2 * channels).to_le_bytes());
        out.extend_from_slice(&16u16.to_le_bytes());
        out.extend_from_slice(b"data");
        out.extend_from_slice(&data_len.to_le_bytes());
        for s in samples {
            out.extend_from_slice(&s.to_le_bytes());
        }
        out
    }

    fn not_stopped() -> Arc<Mutex<bool>> {
        Arc::new(Mutex::new(false))
    }

    #[test]
    fn a_wav_in_any_rate_and_channels_becomes_16k_mono() {
        // 100 ms of stereo at 48 kHz -> 1600 samples at 16 kHz mono.
        let bytes = wav_bytes(2, 48_000, &vec![0i16; 4800 * 2]);
        let f = FileFrames::from_wav(parse_wav(&bytes).unwrap(), Duration::ZERO);
        assert_eq!(f.len(), 1600);
    }

    #[test]
    fn a_16k_mono_wav_is_taken_verbatim() {
        let src: Vec<i16> = (0..1000).map(|i| (i * 7 - 3000) as i16).collect();
        let f = FileFrames::from_wav(parse_wav(&wav_bytes(1, 16_000, &src)).unwrap(), Duration::ZERO);
        assert_eq!(f.samples, src);
    }

    #[test]
    fn what_is_not_16_bit_pcm_is_a_clear_error() {
        let mut eight_bit = wav_bytes(1, 16_000, &[0, 0]);
        eight_bit[34..36].copy_from_slice(&8u16.to_le_bytes());
        assert!(parse_wav(&eight_bit).err().unwrap().contains("16-bit PCM"));
        assert!(parse_wav(b"not a wav at all").is_err());
        assert!(parse_wav(&wav_bytes(1, 16_000, &[1, 2])[..40]).is_err(), "header only, no data");
    }

    #[test]
    fn a_data_size_larger_than_the_file_is_clamped() {
        let mut bytes = wav_bytes(1, 16_000, &[5, 6, 7]);
        bytes[40..44].copy_from_slice(&u32::MAX.to_le_bytes());
        assert_eq!(parse_wav(&bytes).unwrap().samples, vec![5, 6, 7]);
    }

    #[test]
    fn the_tail_is_silence_of_the_requested_length() {
        let f = FileFrames::from_samples(vec![9; 160], Duration::from_millis(500));
        assert_eq!(f.len(), 160 + 8000);
        assert!(f.samples[160..].iter().all(|s| *s == 0));
    }

    #[test]
    fn the_tail_covers_the_largest_silence_window_and_a_margin_the_console_accepts() {
        // Silence / first pause 5000, merge window 5000, plus 500 ms.
        assert!(TAIL >= Duration::from_millis(5000 + 5000 + 500));
    }

    fn fixture() -> PathBuf {
        Path::new(env!("CARGO_MANIFEST_DIR")).join("../tests/fixtures/status-ticket-two.wav")
    }

    #[test]
    fn with_no_variables_the_source_is_the_microphone_and_nothing_is_replayed() {
        let cfg = ReplayConfig::new(None, None);
        assert!(!cfg.replaying());
        assert_eq!(cfg.source_name(), "mic");
        assert!(cfg.sink().is_none());
        assert_eq!(cfg.first_use_warning(), None);
    }

    #[test]
    fn a_replay_says_file_and_warns_once_naming_only_the_file() {
        let cfg = ReplayConfig::new(Some(fixture()), None);
        assert!(cfg.replaying());
        assert_eq!(cfg.source_name(), "file");
        let first = cfg.first_use_warning().expect("the first use warns");
        assert!(first.contains("status-ticket-two.wav") && first.contains("CC_REPLAY_WAV"), "{first}");
        assert_eq!(cfg.first_use_warning(), None, "once, not per take");
    }

    #[test]
    fn the_playhead_survives_dropping_and_reopening_the_input() {
        // CR-7: a device-change reopen or a take error drops the reader. The
        // file's cursor lives in the config, so the next one carries on.
        let cfg = ReplayConfig::new(Some(fixture()), None);
        let first = cfg.open_input().expect("opens the fixture");
        let mut at = first.cursor();
        for _ in 0..10 {
            at = first.since(at).0;
        }
        assert_eq!(first.cursor(), 10 * FRAME as u64);
        drop(first);
        let second = cfg.open_input().expect("reopens");
        assert_eq!(second.cursor(), 10 * FRAME as u64, "not rewound to the start");
        assert!(!second.needs_reopen(), "a file is never on the wrong device");
    }

    #[test]
    fn a_missing_replay_file_is_an_error_that_stops_the_hands_free_loop() {
        let cfg = ReplayConfig::new(Some(PathBuf::from("no-such-dir/nothing.wav")), None);
        let why = cfg.open_input().err().expect("cannot open");
        assert!(why.contains("nothing.wav"), "{why}");
        assert!(why.contains("microphone"), "hands_free::stops_loop keys on this word: {why}");
    }

    #[test]
    fn cursor_since_and_rewound_follow_the_playhead() {
        let src: Vec<i16> = (0..1000).collect();
        let f = FileFrames::from_samples(src.clone(), Duration::ZERO);
        assert_eq!(f.cursor(), 0);
        let (next, chunk) = f.since(0);
        assert_eq!((next, chunk.len()), (FRAME as u64, FRAME));
        assert_eq!(chunk, src[..FRAME]);
        assert_eq!(f.cursor(), FRAME as u64, "reading moves the playhead");
        // Reading from an older cursor (pre-roll) never moves it back.
        let (_, again) = f.since(0);
        assert_eq!(again, src[..FRAME]);
        assert_eq!(f.cursor(), FRAME as u64);
        // 100 ms before an advanced playhead, clamped at the start.
        f.since(FRAME as u64);
        f.since(2 * FRAME as u64);
        assert_eq!(f.cursor(), 3 * FRAME as u64);
        assert_eq!(f.rewound(Duration::from_millis(16)), 2 * FRAME as u64);
        assert_eq!(f.rewound(Duration::from_secs(10)), 0);
    }

    #[test]
    fn the_last_frame_is_short_and_then_there_is_nothing() {
        let f = FileFrames::from_samples(vec![1; FRAME + 10], Duration::ZERO);
        assert!(!f.exhausted());
        let (n, c) = f.since(0);
        assert_eq!(c.len(), FRAME);
        let (n, c) = f.since(n);
        assert_eq!((n, c.len()), ((FRAME + 10) as u64, 10));
        assert!(f.exhausted());
        let (m, c) = f.since(n);
        assert_eq!((m, c.len()), (n, 0));
    }

    /// CR-1: with no new samples the sample clock never advances, so a loop
    /// that only waits for the cap would spin forever. Run it on a thread so
    /// a regression fails the test instead of hanging the suite.
    #[test]
    fn a_take_on_an_exhausted_file_is_nothing_heard_and_does_not_hang() {
        let (tx, rx) = std::sync::mpsc::channel();
        std::thread::spawn(move || {
            let mut f = FileFrames::from_samples(vec![0; 4000], Duration::ZERO);
            let first = audio::record_frames(&mut f, 0, not_stopped(), audio::Limits::default());
            let at = f.cursor();
            // Already exhausted now: a second take has nothing to read at all.
            let again = audio::record_frames(&mut f, at, not_stopped(), audio::Limits::default());
            let _ = tx.send((first.map(|t| t.ending), again.map(|t| (t.ending, t.samples.len())), at));
        });
        let (first, again, at) = rx
            .recv_timeout(Duration::from_secs(10))
            .expect("record_frames hung on an exhausted file");
        assert_eq!(first.unwrap(), audio::Ending::NothingHeard);
        assert_eq!(at, 4000);
        assert_eq!(again.unwrap(), (audio::Ending::NothingHeard, 0));
    }

    /// CR-8: the cap counts every captured sample from `from`, pre-roll
    /// included, so a take that starts a second in the past has a second less
    /// to run.
    #[test]
    fn the_cap_counts_audio_from_the_start_cursor_pre_roll_included() {
        let limits = audio::Limits { max_take: Duration::from_secs(2), ..audio::Limits::default() };
        let cap = 2 * TARGET_HZ as usize;

        let mut fresh = FileFrames::from_samples(vec![0; 10 * TARGET_HZ as usize], Duration::ZERO);
        let t = audio::record_frames(&mut fresh, 0, not_stopped(), limits).unwrap();
        assert_eq!(t.samples.len(), cap, "2 s of audio from the start");

        // Same file, playhead moved 1 s in, take rewound by that 1 s of pre-roll.
        let mut rewound = FileFrames::from_samples(vec![0; 10 * TARGET_HZ as usize], Duration::ZERO);
        let mut at = 0;
        while at < TARGET_HZ as u64 {
            at = rewound.since(at).0;
        }
        let from = rewound.rewound(Duration::from_secs(1));
        assert_eq!(from, at - TARGET_HZ as u64, "the playhead is a frame past 1 s");
        let t = audio::record_frames(&mut rewound, from, not_stopped(), limits).unwrap();
        assert_eq!(t.samples.len(), cap, "pre-roll is part of the 2 s");
        assert_eq!(rewound.cursor(), from + cap as u64, "only 1 s was read past the playhead");
    }

    /// The same capture code on a real recording: a spoken fixture ends on its
    /// silence, and does so identically every time.
    #[test]
    fn a_spoken_fixture_ends_on_silence_and_is_deterministic() {
        let path = fixture();
        let limits = audio::Limits::default();
        let run = || {
            let mut f = FileFrames::open(&path, TAIL).unwrap();
            let t = audio::record_frames(&mut f, 0, not_stopped(), limits).unwrap();
            (t.ending, t.samples.len(), f.cursor())
        };
        let a = run();
        assert_eq!(a.0, audio::Ending::Silence, "{a:?}");
        assert_eq!(a, run(), "same file, same settings, same take");
    }

    fn fixtures_dir() -> PathBuf {
        Path::new(env!("CARGO_MANIFEST_DIR")).join("../tests/fixtures")
    }

    /// Every take on `name`, in order, until the file runs out.
    fn takes(name: &str, limits: audio::Limits) -> Vec<(audio::Ending, usize)> {
        let mut file = FileFrames::open(&fixtures_dir().join(name), TAIL).unwrap();
        let mut out = Vec::new();
        loop {
            let from = file.cursor();
            let take = audio::record_frames(&mut file, from, not_stopped(), limits).unwrap();
            out.push((take.ending, take.samples.len()));
            assert!(out.len() <= 8, "never ran out: {out:?}");
            if take.ending == audio::Ending::NothingHeard {
                return out;
            }
        }
    }

    /// AC-5 / NFR-1. Fixture (a) has a 0.9 s pause, longer than 700 ms of
    /// silence, so with the merge window OFF it is TWO takes (today's
    /// behaviour; slice 1's baseline). Headless, identical every run, and far
    /// faster than the audio it covers.
    #[test]
    fn with_no_window_fixture_a_replays_as_two_takes_identically_and_fast() {
        let limits = audio::Limits::default();
        let began = std::time::Instant::now();
        let first = takes("replay-a-mid-pause.wav", limits);
        let wall = began.elapsed();
        let second = takes("replay-a-mid-pause.wav", limits);
        eprintln!("fixture a, window off: {first:?} in {wall:?}");
        assert_eq!(first.len(), 3, "{first:?}");
        assert_eq!(first[0].0, audio::Ending::Silence, "{first:?}");
        assert_eq!(first[1].0, audio::Ending::Silence, "{first:?}");
        assert_eq!(first[2], (audio::Ending::NothingHeard, first[2].1), "{first:?}");
        assert_eq!(first, second, "same wav, same settings, same takes and sample counts");
        // 5.4 s of speech plus 10.5 s of trailing silence, replayed.
        assert!(wall < Duration::from_secs(2), "capture took {wall:?}");
    }

    /// AC-1 / NFR-1, with the default window: fixture (a) is ONE take, ended
    /// by Silence, with the same sample count on a second run, and the whole
    /// 16 s file is consumed in well under 2 s of wall time.
    #[test]
    fn fixture_a_is_one_take_with_the_window_on_identically_and_fast() {
        let began = std::time::Instant::now();
        let first = takes("replay-a-mid-pause.wav", windowed());
        let wall = began.elapsed();
        let second = takes("replay-a-mid-pause.wav", windowed());
        eprintln!("fixture a, window on: {first:?} in {wall:?}");
        assert_eq!(first.len(), 2, "one take, then nothing: {first:?}");
        assert_eq!(first[0].0, audio::Ending::Silence);
        assert_eq!(first[1].0, audio::Ending::NothingHeard);
        assert_eq!(first, second, "same wav, same settings, same sample counts");
        assert!(wall < Duration::from_secs(2), "capture took {wall:?}");
    }

    // -- B3, on real audio through the seam (T-032-09, 10) -------------------

    /// The console's defaults for the merge window: 700 ms silence, 1200 ms
    /// window, 4 merges.
    fn windowed() -> audio::Limits {
        audio::Limits {
            merge_window: audio::DEFAULT_MERGE_WINDOW,
            max_merges: audio::DEFAULT_MAX_MERGES,
            ..audio::Limits::default()
        }
    }

    /// Every take on `name` in order, whole, until the file runs out.
    fn full_takes(name: &str, limits: audio::Limits) -> Vec<audio::Take> {
        let mut file = FileFrames::open(&fixtures_dir().join(name), TAIL).unwrap();
        let mut out = Vec::new();
        loop {
            let from = file.cursor();
            let take = audio::record_frames(&mut file, from, not_stopped(), limits).unwrap();
            let done = take.ending == audio::Ending::NothingHeard;
            out.push(take);
            assert!(out.len() <= 8, "never ran out");
            if done {
                return out;
            }
        }
    }

    /// The longest run of quiet 16 ms frames strictly between loud ones, and
    /// the quiet frames after the last loud one.
    fn quiet_runs(samples: &[i16]) -> (usize, usize) {
        let loud: Vec<bool> = samples.chunks_exact(FRAME).map(|f| audio::rms(f) > 0.01).collect();
        let first = loud.iter().position(|l| *l).expect("some speech");
        let last = loud.iter().rposition(|l| *l).unwrap();
        let (mut longest, mut run) = (0, 0);
        for l in &loud[first..=last] {
            run = if *l { 0 } else { run + 1 };
            longest = longest.max(run);
        }
        (longest, loud.len() - 1 - last)
    }

    /// AC-7 and FR-10 (buffer level): after a merge the pause inside the take
    /// is about 300 ms (not the 900 ms said) and the tail is about 300 ms (not
    /// 700 + 1200). 20 frames = 300 ms plus the one frame the cut can straddle.
    #[test]
    fn a_merged_take_has_its_pause_squeezed_and_its_tail_trimmed() {
        let takes = full_takes("replay-a-mid-pause.wav", windowed());
        assert_eq!(takes.len(), 2, "one take, then the file runs dry");
        let t = &takes[0];
        assert_eq!((t.ending, t.merges), (audio::Ending::Silence, 1));
        let (inner, tail) = quiet_runs(&t.samples);
        eprintln!("merged take: {} samples, inner quiet {inner} frames, tail {tail} frames", t.samples.len());
        assert!(inner >= 10, "the pause was kept, not removed: {inner}");
        assert!(inner <= 20, "inner pause {inner} frames > 300 ms");
        assert!(tail <= 20, "tail {tail} frames > 300 ms");
        // 0.9 s of pause + 0.7 s of silence + 1.2 s of window were not fed on.
        assert!(t.window_ms >= 1200, "waited a whole window at the end: {}", t.window_ms);
    }

    /// Even with the window OFF the recogniser gets at most 300 ms past the
    /// last word (FR-11 is not tied to the window).
    #[test]
    fn the_tail_is_trimmed_with_the_window_off_too() {
        let takes = full_takes("replay-a-mid-pause.wav", audio::Limits::default());
        for t in takes.iter().filter(|t| t.ending == audio::Ending::Silence) {
            let (_, tail) = quiet_runs(&t.samples);
            assert!(tail <= 20, "tail {tail} frames");
        }
    }

    /// A source that presses "stop" once the playhead passes `at`.
    struct ReleaseAt {
        inner: FileFrames,
        stop: Arc<Mutex<bool>>,
        at: u64,
    }

    impl Frames for ReleaseAt {
        fn cursor(&self) -> u64 {
            self.inner.cursor()
        }
        fn since(&self, cursor: u64) -> (u64, Vec<i16>) {
            let got = self.inner.since(cursor);
            if got.0 >= self.at {
                *self.stop.lock().unwrap() = true;
            }
            got
        }
        fn rewound(&self, preroll: Duration) -> u64 {
            self.inner.rewound(preroll)
        }
        fn exhausted(&self) -> bool {
            self.inner.exhausted()
        }
    }

    /// FR-13 / AC-8: release during a window ends the take at once, not at
    /// the end of the window.
    #[test]
    fn release_during_the_window_ends_the_take_at_once() {
        // Frame 150 is 10 frames into the quiet after the first clause, well
        // inside the 700 ms + 1200 ms the take would otherwise wait.
        let at = 150 * FRAME as u64;
        let stop = not_stopped();
        let mut src = ReleaseAt {
            inner: FileFrames::open(&fixtures_dir().join("replay-a-mid-pause.wav"), TAIL).unwrap(),
            stop: stop.clone(),
            at,
        };
        let take = audio::record_frames(&mut src, 0, stop, windowed()).unwrap();
        assert_eq!(take.ending, audio::Ending::Released);
        assert!(src.cursor() <= at + 2 * FRAME as u64, "kept reading after release: {}", src.cursor());
        let (_, tail) = quiet_runs(&take.samples);
        assert!(tail <= 20, "{tail}");
        assert!(take.window_ms < 400, "waited {} ms after the release", take.window_ms);
    }

    /// FR-12 / AC-8: the cap is audio time and covers the windows, merges and
    /// all: fixture (c) is 10.7 s with pauses; a 4 s cap ends it at 4 s of
    /// captured audio, however much of that the merges squeezed away.
    #[test]
    fn the_cap_covers_windows_and_merges_in_audio_time() {
        let limits = audio::Limits { max_take: Duration::from_secs(4), ..windowed() };
        let began = std::time::Instant::now();
        let takes = full_takes("replay-c-five-pauses.wav", limits);
        let t = &takes[0];
        assert_eq!(t.ending, audio::Ending::Capped, "{:?}", t.ending);
        assert!(t.merges >= 1, "merged at least once before the cap: {}", t.merges);
        assert!(t.samples.len() < 4 * TARGET_HZ as usize, "squeezed below the 4 s captured");
        assert!(began.elapsed() < Duration::from_secs(2), "audio time, not wall time");
    }

    /// AC-2 (buffer half + real engine): the pause is merged - one take, one
    /// merge - and the real base.en transcript of that ONE take has words from
    /// both clauses. Skipped, loudly, where there is no speech engine.
    #[test]
    fn fixture_a_merged_is_transcribed_as_both_clauses() {
        let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
        if !crate::stt::available(&root) {
            eprintln!("skipped: no speech engine under desktop/stt ({})", crate::stt::hint(&root));
            return;
        }
        let takes = full_takes("replay-a-mid-pause.wav", windowed());
        assert_eq!((takes[0].ending, takes[0].merges), (audio::Ending::Silence, 1));
        let _serial = crate::listen::testing::serial();
        let heard = crate::stt::transcribe(&root, &takes[0].wav());
        crate::stt::shutdown();
        let heard = heard.expect("base.en transcribes the merged take").to_lowercase();
        eprintln!("real base.en heard: {heard:?}");
        assert!(heard.contains("tickets"), "first clause missing: {heard:?}");
        assert!(heard.contains("blocked"), "second clause missing: {heard:?}");
    }

    /// AC-3: a 3 s gap is two takes, no merges in either.
    #[test]
    fn a_three_second_gap_is_two_takes_with_no_merges() {
        let takes = full_takes("replay-b-gap-3s.wav", windowed());
        let endings: Vec<_> = takes.iter().map(|t| (t.ending, t.merges)).collect();
        assert_eq!(endings, vec![
            (audio::Ending::Silence, 0),
            (audio::Ending::Silence, 0),
            (audio::Ending::NothingHeard, 0),
        ]);
    }

    /// AC-4 + NFR-1: five 0.9 s pauses. With 4 merges the take ends at the 5th
    /// provisional endpoint (4 merges, the 6th piece is its own take); with 0
    /// every pause splits. 21 s of audio replayed in under 2 s of wall time.
    #[test]
    fn max_merges_caps_how_many_pauses_one_take_absorbs() {
        let began = std::time::Instant::now();
        let four = full_takes("replay-c-five-pauses.wav", windowed());
        let wall = began.elapsed();
        let four: Vec<_> = four.iter().map(|t| (t.ending, t.merges)).collect();
        assert_eq!(four, vec![
            (audio::Ending::Silence, 4),
            (audio::Ending::Silence, 0),
            (audio::Ending::NothingHeard, 0),
        ]);
        assert!(wall < Duration::from_secs(2), "21 s of audio took {wall:?}");

        let none = audio::Limits { max_merges: 0, ..windowed() };
        let none: Vec<_> = full_takes("replay-c-five-pauses.wav", none)
            .iter().map(|t| (t.ending, t.merges)).collect();
        let mut expected = vec![(audio::Ending::Silence, 0); 6];
        expected.push((audio::Ending::NothingHeard, 0));
        assert_eq!(none, expected, "0 merges: every pause splits");
    }

    /// AC-5: the window off is today's two takes for fixture (a); the window
    /// on is one (above). Here: setting only the window to zero is enough.
    #[test]
    fn a_zero_window_splits_fixture_a_whatever_max_merges_says() {
        let off = audio::Limits { merge_window: Duration::ZERO, ..windowed() };
        let endings: Vec<_> = full_takes("replay-a-mid-pause.wav", off)
            .iter().map(|t| t.ending).collect();
        assert_eq!(endings, vec![
            audio::Ending::Silence, audio::Ending::Silence, audio::Ending::NothingHeard]);
    }

    /// AC-6: three 3 ms clicks after the sentence, 0.25 s apart, are inside the
    /// 700 ms + window. They do not merge and do not hold the take open: it
    /// waited exactly one 1200 ms window.
    #[test]
    fn clicks_in_the_window_do_not_extend_the_take() {
        let takes = full_takes("replay-f-clicks-in-window.wav", windowed());
        assert_eq!(takes.len(), 2, "one take, then nothing");
        assert_eq!((takes[0].ending, takes[0].merges), (audio::Ending::Silence, 0));
        assert_eq!(takes[0].window_ms, 1200);
        assert_eq!(takes[1].ending, audio::Ending::NothingHeard);
    }

    /// AC-13: replay cannot be turned on from a setting or the console.
    #[test]
    fn nothing_in_the_console_or_its_settings_can_turn_replay_on() {
        for (name, source) in [
            ("assistant.toml", include_str!("../../../console/config/assistant.toml")),
            ("assistant_config.py", include_str!("../../../console/server/assistant_config.py")),
        ] {
            let lower = source.to_lowercase();
            assert!(!lower.contains("replay"), "{name} mentions replay");
            assert!(!lower.contains("cc_tts_sink"), "{name} mentions the sink");
        }
    }

    #[test]
    fn listen_state_says_where_the_audio_comes_from() {
        let root = std::env::temp_dir();
        let file = ReplayConfig::new(Some(fixture()), None);
        assert_eq!(crate::bridge::listen_state_with(&root, &file)["source"], "file");
        assert_eq!(crate::bridge::listen_state_with(&root, &ReplayConfig::new(None, None))["source"], "mic");
    }
}

//! Microphone capture, down to the 16 kHz mono the recogniser wants.
//!
//! ## What "a short take" means here
//!
//! Recording until a fixed timer expires makes the user wait after they have
//! finished talking, and cuts them off if they pause to think. So capture ends
//! when the *speaker* stops: a voice-activity detector scores every 16 ms
//! frame, and the take ends after a stretch of silence that follows actual
//! speech. A hard cap still applies, because a stuck detector must not record
//! forever.
//!
//! ## Why the resampler is four lines
//!
//! It is linear interpolation, which is not what you would use for music. For
//! speech being handed to a recogniser it is inaudibly fine, and the
//! alternative is a resampling crate and its own trade-offs. This machine's
//! microphone already reports 16 kHz mono, so on the common path the sample
//! loop is a copy — the conversion exists for the devices that do not.
//!
//! ## Why the WAV is built by hand
//!
//! A 44-byte header in front of little-endian i16 samples. Pulling in a WAV
//! crate to write 44 known bytes would be the larger dependency to justify.

use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};

/// What the recogniser expects, and what the VAD expects. Not a preference —
/// both are fixed at this rate.
pub const TARGET_HZ: u32 = 16_000;

/// The VAD's frame size, fixed by the detector: exactly 256 samples of 16 kHz
/// audio, i.e. 16 ms.
const FRAME: usize = 256;

/// Defaults for the two limits a caller can override from settings. The cap
/// is long enough for a sentence with a pause in it and short enough that a
/// stuck detector is an annoyance rather than a recording of your afternoon —
/// and it came down from 20s once takes reliably ended on their own.
pub const DEFAULT_MAX_TAKE: Duration = Duration::from_secs(12);
pub const DEFAULT_TRAILING_SILENCE: Duration = Duration::from_millis(700);

/// Ignore a take shorter than this: a stray click or a knocked desk.
const MIN_SPEECH: Duration = Duration::from_millis(300);

/// Baseline thresholds, used as FLOORS under the adaptive ones below.
/// `earshot` documents 0.5 as the general threshold; starting is held higher
/// and stopping lower so a wavering score mid-word does not chop the take in
/// half.
const SPEECH_ON: f32 = 0.6;
const SPEECH_OFF: f32 = 0.35;

/// How long to listen to the room before trusting the thresholds.
///
/// This is the fix for the defect that made every take run to the cap: on a
/// microphone with a high noise floor — an array mic in a room with a fan —
/// the detector scores background noise above `SPEECH_OFF` forever, so the
/// silence that ends a take never arrives. Measuring the room first and
/// moving the thresholds above whatever it is doing costs 300ms once per
/// take, which is cheaper than the 20 seconds it used to cost every time.
///
/// Strictly shorter than `MIN_SPEECH`, so calibration can never be the reason
/// a take was rejected as too short — 200ms is twelve frames, plenty for a
/// mean, and it keeps that inequality true rather than merely equal.
const CALIBRATE: Duration = Duration::from_millis(200);

/// How far above the measured floor a frame has to be to count as speech, in
/// score and in loudness. Both are required: a neural VAD scores steady hum
/// surprisingly high, and a loud room is not speech.
const SCORE_MARGIN: f32 = 0.22;
const RMS_MARGIN: f32 = 2.2;

/// How many frames in a row have to look like speech before the silence
/// counter is reset.
///
/// This is the one that made the difference in practice. Thresholds alone
/// still let a SINGLE spurious frame — a keyboard tap, a chair, a fan
/// harmonic the detector likes — restart the count, and a take that needs
/// 700ms of quiet will never get it if something scores high once a second.
/// Three frames is 48ms: shorter than any real syllable, longer than any
/// click.
const SPEECH_RUN: usize = 3;

/// The noise floor keeps moving during the take, at this rate per frame.
///
/// A floor measured once at the start describes the room as it was 200ms ago.
/// Rooms change — a fan cycles, someone starts typing — and a stale floor is
/// how a take ends up waiting for a silence that, by its own definition,
/// already happened.
const FLOOR_DRIFT: f32 = 0.02;

pub type AudioResult<T> = Result<T, String>;

/// Why a take ended. The caller says different things to the user for each,
/// so this is not just diagnostics.
#[derive(Debug, PartialEq, Eq, Clone, Copy)]
pub enum Ending {
    /// The speaker stopped talking. The normal case.
    Silence,
    /// The caller asked for it (released push-to-talk, clicked the tray).
    Released,
    /// `MAX_TAKE` elapsed.
    Capped,
    /// Nothing loud enough to be speech.
    NothingHeard,
}

pub struct Take {
    /// 16 kHz mono, signed 16-bit.
    pub samples: Vec<i16>,
    pub ending: Ending,
}

impl Take {
    pub fn seconds(&self) -> f32 {
        self.samples.len() as f32 / TARGET_HZ as f32
    }

    /// A RIFF/WAVE file: 44-byte header, then the samples.
    pub fn wav(&self) -> Vec<u8> {
        let data_len = (self.samples.len() * 2) as u32;
        let mut out = Vec::with_capacity(44 + data_len as usize);
        out.extend_from_slice(b"RIFF");
        out.extend_from_slice(&(36 + data_len).to_le_bytes());
        out.extend_from_slice(b"WAVEfmt ");
        out.extend_from_slice(&16u32.to_le_bytes()); // fmt chunk size
        out.extend_from_slice(&1u16.to_le_bytes()); // PCM
        out.extend_from_slice(&1u16.to_le_bytes()); // mono
        out.extend_from_slice(&TARGET_HZ.to_le_bytes());
        out.extend_from_slice(&(TARGET_HZ * 2).to_le_bytes()); // byte rate
        out.extend_from_slice(&2u16.to_le_bytes()); // block align
        out.extend_from_slice(&16u16.to_le_bytes()); // bits per sample
        out.extend_from_slice(b"data");
        out.extend_from_slice(&data_len.to_le_bytes());
        for s in &self.samples {
            out.extend_from_slice(&s.to_le_bytes());
        }
        out
    }
}

/// Average a device's interleaved frame down to one channel, then resample to
/// 16 kHz. Separated from the capture callback so it can be tested with no
/// hardware at all.
pub fn to_mono_16k(input: &[f32], channels: u16, source_hz: u32) -> Vec<i16> {
    if input.is_empty() || channels == 0 || source_hz == 0 {
        return Vec::new();
    }
    let channels = channels as usize;
    let mono: Vec<f32> = input
        .chunks(channels)
        .map(|frame| frame.iter().sum::<f32>() / channels as f32)
        .collect();

    if source_hz == TARGET_HZ {
        // The common path on this hardware: no interpolation at all.
        return mono.iter().map(|s| to_i16(*s)).collect();
    }

    let ratio = TARGET_HZ as f64 / source_hz as f64;
    let out_len = ((mono.len() as f64) * ratio).round() as usize;
    let mut out = Vec::with_capacity(out_len);
    for i in 0..out_len {
        let pos = i as f64 / ratio;
        let left = pos.floor() as usize;
        let frac = (pos - left as f64) as f32;
        let a = mono.get(left).copied().unwrap_or(0.0);
        let b = mono.get(left + 1).copied().unwrap_or(a);
        out.push(to_i16(a + (b - a) * frac));
    }
    out
}

fn to_i16(sample: f32) -> i16 {
    (sample.clamp(-1.0, 1.0) * i16::MAX as f32) as i16
}

/// The frame duration the detector works in, in milliseconds.
fn frame_ms() -> f32 {
    (FRAME as f32 / TARGET_HZ as f32) * 1000.0
}

/// One frame's loudness, 0.0..1.0.
pub fn rms(frame: &[i16]) -> f32 {
    if frame.is_empty() {
        return 0.0;
    }
    let sum: f64 = frame.iter().map(|s| {
        let v = *s as f64 / i16::MAX as f64;
        v * v
    }).sum();
    ((sum / frame.len() as f64).sqrt() as f32).clamp(0.0, 1.0)
}

/// Decides when a take is over, from VAD scores and loudness. Pure, so the
/// interesting behaviour is testable without a microphone — which matters,
/// because the interesting behaviour is "does this end at all in a noisy
/// room", and that is not a question you can answer by listening once.
pub struct Endpointer {
    speaking: bool,
    speech_frames: usize,
    silence_frames: usize,
    /// Frames still being used to measure the room.
    calibrating: usize,
    floor_score: f32,
    floor_rms: f32,
    samples: usize,
    /// Consecutive speech-looking frames, for `SPEECH_RUN`.
    run: usize,
    trailing_silence: Duration,
}

impl Default for Endpointer {
    fn default() -> Self {
        Self::new(DEFAULT_TRAILING_SILENCE)
    }
}

impl Endpointer {
    pub fn new(trailing_silence: Duration) -> Self {
        let frames = (CALIBRATE.as_millis() as f32 / frame_ms()).round() as usize;
        Self {
            speaking: false,
            speech_frames: 0,
            silence_frames: 0,
            calibrating: frames.max(1),
            floor_score: 0.0,
            floor_rms: 0.0,
            samples: 0,
            run: 0,
            trailing_silence,
        }
    }

    /// The thresholds in force, after the room has been measured. Public so a
    /// log line can say what it decided to listen for.
    pub fn thresholds(&self) -> (f32, f32, f32) {
        (
            (self.floor_score + SCORE_MARGIN).max(SPEECH_ON),
            (self.floor_score + SCORE_MARGIN * 0.45).max(SPEECH_OFF),
            self.floor_rms * RMS_MARGIN,
        )
    }

    /// Feed one frame. Returns true when the take should end.
    pub fn push(&mut self, score: f32, loudness: f32) -> bool {
        // Measure the room first. Nothing counts as speech and nothing counts
        // as silence while this runs, so a noisy start cannot end a take
        // before it has begun.
        if self.calibrating > 0 {
            self.calibrating -= 1;
            self.samples += 1;
            let n = self.samples as f32;
            self.floor_score += (score - self.floor_score) / n;
            self.floor_rms += (loudness - self.floor_rms) / n;
            return false;
        }

        let (on, off, min_rms) = self.thresholds();
        // Both signals have to agree. The score alone was the old rule, and a
        // steady hum kept it permanently above the silence threshold.
        let looks_like_speech = score >= on && loudness >= min_rms;
        if looks_like_speech {
            self.run += 1;
            // A run, not a frame. One high-scoring frame per second is enough
            // to hold a take open forever if it resets the silence counter,
            // and a room reliably produces one.
            if self.run >= SPEECH_RUN {
                self.speaking = true;
                self.speech_frames += 1;
                self.silence_frames = 0;
            }
        } else {
            self.run = 0;
            if score < off || loudness < min_rms {
                self.silence_frames += 1;
            }
            // Let the floor follow the room while nobody is talking, so a
            // fan that starts mid-take does not become "speech".
            self.floor_score += (score - self.floor_score) * FLOOR_DRIFT;
            self.floor_rms += (loudness - self.floor_rms) * FLOOR_DRIFT;
        }
        // Only after real speech: leading silence must not end a take before
        // the user has said anything.
        if !self.speaking {
            return false;
        }
        let spoken_ms = self.speech_frames as f32 * frame_ms();
        let silent_ms = self.silence_frames as f32 * frame_ms();
        spoken_ms >= MIN_SPEECH.as_millis() as f32
            && silent_ms >= self.trailing_silence.as_millis() as f32
    }

    pub fn heard_speech(&self) -> bool {
        self.speech_frames as f32 * frame_ms() >= MIN_SPEECH.as_millis() as f32
    }
}

/// Is there an input device at all?
pub fn available() -> bool {
    cpal::default_host().default_input_device().is_some()
}

pub fn device_name() -> String {
    cpal::default_host()
        .default_input_device()
        .and_then(|d| d.name().ok())
        .unwrap_or_default()
}

/// Record until the speaker stops, `stop` flips, or the cap is reached.
///
/// Blocking, and meant to be: the caller runs it on its own thread and the
/// tray shows the listening state meanwhile.
/// How long a take may run, and how much silence ends it. Passed in rather
/// than read here so the shell has ONE settings reader (`console_settings`)
/// instead of one per module.
#[derive(Clone, Copy, Debug)]
pub struct Limits {
    pub max_take: Duration,
    pub trailing_silence: Duration,
}

impl Default for Limits {
    fn default() -> Self {
        Self { max_take: DEFAULT_MAX_TAKE, trailing_silence: DEFAULT_TRAILING_SILENCE }
    }
}

/// The current input level, 0..1000, for the HUD's meter. An integer because
/// atomics come in integers; scaled rather than bit-cast so the value is
/// readable in a debugger.
static LEVEL: std::sync::atomic::AtomicU32 = std::sync::atomic::AtomicU32::new(0);

fn set_level(value: f32) {
    LEVEL.store((value.clamp(0.0, 1.0) * 1000.0) as u32, std::sync::atomic::Ordering::Relaxed);
}

/// The last frame's level, 0.0..1.0. Zero when nothing is recording.
pub fn level() -> f32 {
    LEVEL.load(std::sync::atomic::Ordering::Relaxed) as f32 / 1000.0
}

/// An open microphone.
///
/// Exists because opening one costs the better part of a second on Windows —
/// measured, not assumed: `build_input_stream` plus `play` is 0.9-2.0s while
/// finding the device and reading its format are under 10ms between them.
/// For push-to-talk that is a price per take, and paying it keeps the OS
/// microphone indicator honest: the light is on exactly while a take is open.
///
/// For HANDS-FREE it is different. The mic is openly on for the whole
/// session, so reopening it between takes buys no privacy at all — it just
/// makes the assistant deaf for a second after every utterance, which is
/// where a wake word tends to land.
pub struct Mic {
    stream: cpal::Stream,
    collected: Arc<Mutex<Vec<i16>>>,
}

impl Mic {
    pub fn open() -> AudioResult<Mic> {
    let opening = Instant::now();
    let host = cpal::default_host();
    let device = host
        .default_input_device()
        .ok_or_else(|| "no microphone: nothing is set as the default input device".to_string())?;
    let found_ms = opening.elapsed().as_millis();
    let step = Instant::now();
    let config = device
        .default_input_config()
        .map_err(|e| format!("cannot read the microphone's format: {e}"))?;
    let config_ms = step.elapsed().as_millis();
    let channels = config.channels();
    let source_hz = config.sample_rate().0;

    let collected: Arc<Mutex<Vec<i16>>> = Arc::new(Mutex::new(Vec::new()));
    let sink = collected.clone();
    let format = config.sample_format();
    let stream_config: cpal::StreamConfig = config.into();

    let err_fn = |e| log::warn!("audio: stream error: {e}");
    let built = Instant::now();

    // Every sample format a default input config can report, converted at the
    // edge so nothing downstream has to care which one this device uses.
    let stream = match format {
        cpal::SampleFormat::F32 => device.build_input_stream(
            &stream_config,
            move |data: &[f32], _| {
                if let Ok(mut buf) = sink.lock() {
                    buf.extend(to_mono_16k(data, channels, source_hz));
                }
            },
            err_fn,
            None,
        ),
        cpal::SampleFormat::I16 => device.build_input_stream(
            &stream_config,
            move |data: &[i16], _| {
                let as_f32: Vec<f32> = data.iter().map(|s| *s as f32 / i16::MAX as f32).collect();
                if let Ok(mut buf) = sink.lock() {
                    buf.extend(to_mono_16k(&as_f32, channels, source_hz));
                }
            },
            err_fn,
            None,
        ),
        cpal::SampleFormat::U16 => device.build_input_stream(
            &stream_config,
            move |data: &[u16], _| {
                let as_f32: Vec<f32> = data
                    .iter()
                    .map(|s| (*s as f32 - 32768.0) / 32768.0)
                    .collect();
                if let Ok(mut buf) = sink.lock() {
                    buf.extend(to_mono_16k(&as_f32, channels, source_hz));
                }
            },
            err_fn,
            None,
        ),
        other => return Err(format!("this microphone reports {other:?} samples, which is not handled")),
    }
    .map_err(|e| {
        // The overwhelmingly common cause on Windows, and worth naming: the
        // OS privacy switch, not a broken device.
        format!("cannot open the microphone ({e}). On Windows check Settings > \
                 Privacy & security > Microphone > let desktop apps access it")
    })?;

    stream
        .play()
        .map_err(|e| format!("cannot start the microphone: {e}"))?;
    // Timed separately from the take: this is dead air where the user has
    // already clicked and the microphone is not open yet.
    log::info!(
        "audio: microphone open in {}ms (find {found_ms}ms, format {config_ms}ms, build {}ms)",
        opening.elapsed().as_millis(),
        built.elapsed().as_millis()
    );
        Ok(Mic { stream, collected })
    }

    /// Record one take from this already-open microphone.
    pub fn take(&mut self, stop: Arc<Mutex<bool>>, limits: Limits) -> AudioResult<Take> {
        // Whatever arrived between takes is not part of this one.
        self.collected.lock().unwrap_or_else(|e| e.into_inner()).clear();
        let collected = self.collected.clone();

    let mut detector = earshot::Detector::default_boxed();
    let mut endpointer = Endpointer::new(limits.trailing_silence);
    let started = Instant::now();
    let mut scored = 0usize;
    // Every exit below assigns this. Declared without a value so the
    // compiler proves that, rather than a default quietly standing in
    // for a path somebody forgot.
    let ending;

    loop {
        if *stop.lock().unwrap_or_else(|e| e.into_inner()) {
            ending = Ending::Released;
            break;
        }
        if started.elapsed() >= limits.max_take {
            ending = Ending::Capped;
            break;
        }
        // Score whatever whole frames have arrived since last time.
        let available_frames = {
            let buf = collected.lock().unwrap_or_else(|e| e.into_inner());
            buf.len() / FRAME
        };
        let mut ended = false;
        while scored < available_frames {
            let frame: Vec<i16> = {
                let buf = collected.lock().unwrap_or_else(|e| e.into_inner());
                buf[scored * FRAME..(scored + 1) * FRAME].to_vec()
            };
            scored += 1;
            let loudness = rms(&frame);
            // Published for the HUD's level meter, from the frame the VAD is
            // scoring anyway — a second audio path just to draw a bar would
            // be a second place for the audio to be wrong.
            set_level(loudness);
            if endpointer.push(detector.predict_i16(&frame), loudness) {
                ended = true;
                break;
            }
        }
        if ended {
            ending = Ending::Silence;
            break;
        }
        std::thread::sleep(Duration::from_millis(16));
    }

    set_level(0.0);
    let (on, off, min_rms) = endpointer.thresholds();
    log::debug!(
        "audio: room floor gave thresholds on {on:.2} off {off:.2} rms {min_rms:.4}"
    );
    let samples = collected.lock().unwrap_or_else(|e| e.into_inner()).clone();
    if !endpointer.heard_speech() {
        return Ok(Take { samples, ending: Ending::NothingHeard });
    }
        Ok(Take { samples, ending })
    }
}

impl Drop for Mic {
    fn drop(&mut self) {
        // Explicit, so the reason survives: dropping the stream is what turns
        // the OS microphone indicator off. Nothing else does.
        use cpal::traits::StreamTrait;
        let _ = self.stream.pause();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_16k_mono_device_needs_no_conversion() {
        let input: Vec<f32> = (0..100).map(|i| (i as f32 / 100.0) - 0.5).collect();
        let out = to_mono_16k(&input, 1, TARGET_HZ);
        assert_eq!(out.len(), 100);
    }

    #[test]
    fn stereo_is_averaged_to_one_channel() {
        // Left full, right silent -> half amplitude, half the samples.
        let input = vec![1.0, 0.0, 1.0, 0.0, 1.0, 0.0];
        let out = to_mono_16k(&input, 2, TARGET_HZ);
        assert_eq!(out.len(), 3);
        assert!((out[0] as f32 - i16::MAX as f32 / 2.0).abs() < 100.0, "{}", out[0]);
    }

    #[test]
    fn a_48k_device_is_resampled_to_16k() {
        let input = vec![0.0f32; 4800]; // 100 ms at 48 kHz
        let out = to_mono_16k(&input, 1, 48_000);
        assert_eq!(out.len(), 1600, "100 ms at 16 kHz");
    }

    #[test]
    fn resampling_preserves_a_tone_roughly() {
        // A 1 kHz sine at 48 kHz should still cross zero about 200 times in
        // 100 ms after resampling. This is the check that would catch a
        // ratio inverted the wrong way round.
        let hz = 1000.0;
        let input: Vec<f32> = (0..4800)
            .map(|i| (2.0 * std::f32::consts::PI * hz * (i as f32 / 48_000.0)).sin())
            .collect();
        let out = to_mono_16k(&input, 1, 48_000);
        let crossings = out.windows(2).filter(|w| (w[0] < 0) != (w[1] < 0)).count();
        assert!((190..=210).contains(&crossings), "{crossings} zero crossings");
    }

    #[test]
    fn empty_or_nonsense_input_is_empty_not_a_panic() {
        assert!(to_mono_16k(&[], 1, TARGET_HZ).is_empty());
        assert!(to_mono_16k(&[0.1], 0, TARGET_HZ).is_empty());
        assert!(to_mono_16k(&[0.1], 1, 0).is_empty());
    }

    #[test]
    fn samples_are_clamped_not_wrapped() {
        // A device reporting slightly out-of-range floats must not wrap to
        // full-scale negative, which sounds like a gunshot.
        let out = to_mono_16k(&[2.0, -2.0], 1, TARGET_HZ);
        assert_eq!(out, vec![i16::MAX, -i16::MAX]);
    }

    #[test]
    fn the_wav_header_is_a_44_byte_riff() {
        let take = Take { samples: vec![0, 1, -1], ending: Ending::Silence };
        let wav = take.wav();
        assert_eq!(&wav[0..4], b"RIFF");
        assert_eq!(&wav[8..12], b"WAVE");
        assert_eq!(&wav[36..40], b"data");
        assert_eq!(wav.len(), 44 + 6);
        // Sample rate and mono, where a recogniser will look for them.
        assert_eq!(u32::from_le_bytes(wav[24..28].try_into().unwrap()), TARGET_HZ);
        assert_eq!(u16::from_le_bytes(wav[22..24].try_into().unwrap()), 1);
    }

    /// One "frame" of scores at 16 ms each.
    /// A frame at a given score and loudness, repeated. Loudness defaults to
    /// something comfortably above a quiet room so the existing cases read as
    /// they did before the energy gate existed.
    fn feed_loud(ep: &mut Endpointer, score: f32, loudness: f32, frames: usize) -> bool {
        for _ in 0..frames {
            if ep.push(score, loudness) {
                return true;
            }
        }
        false
    }

    /// Let the endpointer measure a quiet room, so a test that means to feed
    /// speech is not spending its first frames on calibration.
    fn quiet_room(ep: &mut Endpointer) {
        feed_loud(ep, 0.02, 0.001, 32);
    }

    fn feed(ep: &mut Endpointer, score: f32, frames: usize) -> bool {
        // A score-shaped loudness: loud when the score says speech, near
        // silent when it does not, which is what a real frame looks like.
        let loudness = if score >= 0.5 { 0.08 } else { 0.001 };
        feed_loud(ep, score, loudness, frames)
    }

    #[test]
    fn silence_before_speech_never_ends_a_take() {
        // Otherwise the take would end before the user began.
        let mut ep = Endpointer::default();
        assert!(!feed(&mut ep, 0.0, 500));
        assert!(!ep.heard_speech());
    }

    #[test]
    fn speech_then_silence_ends_the_take() {
        let mut ep = Endpointer::default();
        quiet_room(&mut ep);
        assert!(!feed(&mut ep, 0.9, 30), "still talking at 480 ms");
        assert!(feed(&mut ep, 0.0, 60), "700 ms of silence should end it");
        assert!(ep.heard_speech());
    }

    #[test]
    fn a_brief_click_is_not_speech() {
        let mut ep = Endpointer::default();
        quiet_room(&mut ep);
        feed(&mut ep, 0.9, 3); // ~48 ms
        feed(&mut ep, 0.0, 60);
        assert!(!ep.heard_speech(), "48 ms is below the minimum");
    }

    #[test]
    fn a_pause_mid_sentence_does_not_end_the_take() {
        // The hysteresis between SPEECH_ON and SPEECH_OFF is what makes this
        // work: a wavering score mid-word must not chop the take.
        let mut ep = Endpointer::default();
        quiet_room(&mut ep);
        feed(&mut ep, 0.9, 30);
        assert!(!feed(&mut ep, 0.0, 20), "320 ms pause is not the end");
        assert!(!feed(&mut ep, 0.9, 20), "they carried on");
        assert!(feed(&mut ep, 0.0, 60), "now they have stopped");
    }

    #[test]
    fn a_noisy_room_still_ends_the_take() {
        // THE regression. On an array microphone with a fan in the room the
        // detector scored background noise around 0.5 forever, so the silence
        // that ends a take never came and every take ran to the cap — twenty
        // seconds of waiting after every sentence. Calibrating to the room
        // and requiring loudness above it is what fixes it.
        let mut ep = Endpointer::new(DEFAULT_TRAILING_SILENCE);
        // The room, measured first: scores high-ish, but quiet.
        feed_loud(&mut ep, 0.5, 0.004, 32);
        // Someone speaks: louder, and higher again.
        assert!(!feed_loud(&mut ep, 0.95, 0.09, 40));
        // They stop. The room carries on exactly as before, and this is the
        // frame sequence that used to hold the take open forever.
        assert!(feed_loud(&mut ep, 0.5, 0.004, 60),
                "a take must end when the speaker stops, not when the room does");
        assert!(ep.heard_speech());
    }

    #[test]
    fn one_noisy_frame_a_second_cannot_hold_a_take_open() {
        // Observed live, not imagined: after the speaker stopped, a take ran
        // 9.4 seconds for a 3-second phrase because something in the room
        // scored high every so often and reset the silence counter each time.
        // Thresholds alone did not fix it; requiring a RUN of speech frames
        // did.
        let mut ep = Endpointer::default();
        feed_loud(&mut ep, 0.1, 0.002, 32); // the room
        assert!(!feed_loud(&mut ep, 0.95, 0.09, 40)); // someone talks
        // Now silence, interrupted by one loud frame every ten.
        let mut ended = false;
        for i in 0..120 {
            let spurious = i % 10 == 0;
            let (score, loud) = if spurious { (0.98, 0.2) } else { (0.05, 0.001) };
            if ep.push(score, loud) {
                ended = true;
                break;
            }
        }
        assert!(ended, "a take must end between the taps, not wait them out");
    }

    #[test]
    fn a_real_pause_of_a_few_frames_still_does_not_end_the_take() {
        // The other side of the same rule: `SPEECH_RUN` must not be so long
        // that ordinary speech fails to register at all.
        let mut ep = Endpointer::default();
        quiet_room(&mut ep);
        assert!(!feed(&mut ep, 0.9, 20));
        assert!(!feed(&mut ep, 0.0, 20)); // a 320ms pause, mid-sentence
        assert!(!feed(&mut ep, 0.9, 20));
        assert!(ep.heard_speech(), "speech in runs must still count as speech");
    }

    #[test]
    fn the_room_moves_the_thresholds_but_never_below_the_floor() {
        let mut quiet = Endpointer::default();
        feed_loud(&mut quiet, 0.01, 0.0005, 32);
        let (on_q, off_q, _) = quiet.thresholds();
        assert_eq!((on_q, off_q), (SPEECH_ON, SPEECH_OFF),
                   "a quiet room must not make the detector MORE eager");

        let mut noisy = Endpointer::default();
        feed_loud(&mut noisy, 0.55, 0.02, 32);
        let (on_n, _, rms_n) = noisy.thresholds();
        assert!(on_n > SPEECH_ON, "a noisy room has to raise the bar");
        assert!(rms_n > 0.0, "and give the energy gate something to compare to");
    }

    #[test]
    fn calibration_cannot_swallow_the_start_of_a_sentence() {
        // Calibration is shorter than MIN_SPEECH, so a take that begins the
        // instant the mic opens still registers as speech.
        assert!(CALIBRATE < MIN_SPEECH);
    }

    #[test]
    fn a_configured_silence_window_is_honoured() {
        let mut fast = Endpointer::new(Duration::from_millis(200));
        quiet_room(&mut fast);
        assert!(!feed(&mut fast, 0.9, 30));
        // ~13 frames is 200ms; 20 is comfortably past it and well short of
        // the 700ms default.
        assert!(feed(&mut fast, 0.0, 20));
    }

    #[test]
    fn an_ambiguous_score_neither_starts_nor_stops() {
        // Between the two thresholds: not speech, not silence.
        let mut ep = Endpointer::default();
        assert!(!feed(&mut ep, 0.5, 200));
        assert!(!ep.heard_speech());
    }
}

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

/// A take never runs longer than this, however the detector behaves. Long
/// enough for a sentence with a pause in it; short enough that a stuck
/// detector is an annoyance rather than a recording of your afternoon.
const MAX_TAKE: Duration = Duration::from_secs(20);

/// Silence after speech that ends the take.
const TRAILING_SILENCE: Duration = Duration::from_millis(700);

/// Ignore a take shorter than this: a stray click or a knocked desk.
const MIN_SPEECH: Duration = Duration::from_millis(300);

/// Scores above this count as speech. `earshot` documents 0.5 as the general
/// threshold; starting is held higher and stopping lower so a wavering score
/// mid-word does not chop the take in half.
const SPEECH_ON: f32 = 0.6;
const SPEECH_OFF: f32 = 0.35;

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

/// Decides when a take is over, from VAD scores. Pure, so the interesting
/// behaviour is testable without a microphone.
pub struct Endpointer {
    speaking: bool,
    speech_frames: usize,
    silence_frames: usize,
}

impl Default for Endpointer {
    fn default() -> Self {
        Self { speaking: false, speech_frames: 0, silence_frames: 0 }
    }
}

impl Endpointer {
    /// Feed one frame's score. Returns true when the take should end.
    pub fn push(&mut self, score: f32) -> bool {
        let frame_ms = (FRAME as f32 / TARGET_HZ as f32) * 1000.0;
        if score >= SPEECH_ON {
            self.speaking = true;
            self.speech_frames += 1;
            self.silence_frames = 0;
        } else if score < SPEECH_OFF {
            self.silence_frames += 1;
        }
        // Only after real speech: leading silence must not end a take before
        // the user has said anything.
        if !self.speaking {
            return false;
        }
        let spoken_ms = self.speech_frames as f32 * frame_ms;
        let silent_ms = self.silence_frames as f32 * frame_ms;
        spoken_ms >= MIN_SPEECH.as_millis() as f32
            && silent_ms >= TRAILING_SILENCE.as_millis() as f32
    }

    pub fn heard_speech(&self) -> bool {
        let frame_ms = (FRAME as f32 / TARGET_HZ as f32) * 1000.0;
        self.speech_frames as f32 * frame_ms >= MIN_SPEECH.as_millis() as f32
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
pub fn record(stop: Arc<Mutex<bool>>) -> AudioResult<Take> {
    let host = cpal::default_host();
    let device = host
        .default_input_device()
        .ok_or_else(|| "no microphone: nothing is set as the default input device".to_string())?;
    let config = device
        .default_input_config()
        .map_err(|e| format!("cannot read the microphone's format: {e}"))?;
    let channels = config.channels();
    let source_hz = config.sample_rate().0;

    let collected: Arc<Mutex<Vec<i16>>> = Arc::new(Mutex::new(Vec::new()));
    let sink = collected.clone();
    let format = config.sample_format();
    let stream_config: cpal::StreamConfig = config.into();

    let err_fn = |e| log::warn!("audio: stream error: {e}");

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

    let mut detector = earshot::Detector::default_boxed();
    let mut endpointer = Endpointer::default();
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
        if started.elapsed() >= MAX_TAKE {
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
            if endpointer.push(detector.predict_i16(&frame)) {
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

    drop(stream);
    let samples = collected.lock().unwrap_or_else(|e| e.into_inner()).clone();
    if !endpointer.heard_speech() {
        return Ok(Take { samples, ending: Ending::NothingHeard });
    }
    Ok(Take { samples, ending })
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
    fn feed(ep: &mut Endpointer, score: f32, frames: usize) -> bool {
        for _ in 0..frames {
            if ep.push(score) {
                return true;
            }
        }
        false
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
        assert!(!feed(&mut ep, 0.9, 30), "still talking at 480 ms");
        assert!(feed(&mut ep, 0.0, 60), "700 ms of silence should end it");
        assert!(ep.heard_speech());
    }

    #[test]
    fn a_brief_click_is_not_speech() {
        let mut ep = Endpointer::default();
        feed(&mut ep, 0.9, 3); // ~48 ms
        feed(&mut ep, 0.0, 60);
        assert!(!ep.heard_speech(), "48 ms is below the minimum");
    }

    #[test]
    fn a_pause_mid_sentence_does_not_end_the_take() {
        // The hysteresis between SPEECH_ON and SPEECH_OFF is what makes this
        // work: a wavering score mid-word must not chop the take.
        let mut ep = Endpointer::default();
        feed(&mut ep, 0.9, 30);
        assert!(!feed(&mut ep, 0.0, 20), "320 ms pause is not the end");
        assert!(!feed(&mut ep, 0.9, 20), "they carried on");
        assert!(feed(&mut ep, 0.0, 60), "now they have stopped");
    }

    #[test]
    fn an_ambiguous_score_neither_starts_nor_stops() {
        // Between the two thresholds: not speech, not silence.
        let mut ep = Endpointer::default();
        assert!(!feed(&mut ep, 0.5, 200));
        assert!(!ep.heard_speech());
    }
}

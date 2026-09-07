//! Short tones: the microphone is open, the take went, nothing was heard.
//!
//! ## Why synthesise instead of playing a file or asking the OS
//!
//! The three obvious alternatives are each worse here. A bundled WAV means an
//! asset to ship and a decoder to reach for. `Beep` on Windows, `NSBeep` on
//! macOS and `paplay` on Linux means three code paths, one of which needs a
//! package installed. Generating a sine through the output device `cpal`
//! already provides is the same forty lines on all three platforms, and it is
//! the only option where the sound cannot be missing at runtime.
//!
//! ## Why it matters at all
//!
//! Opening a microphone takes the better part of a second, and for that
//! second anything you say is not being recorded. A rising tone at the moment
//! the stream goes live turns dead air into "wait for the beep", which is a
//! thing people already know how to do.

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::time::Duration;

use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};

/// Cues off entirely — set when replies are muted. A tone is a reply of a
/// sort, and someone who has asked for silence means this too.
static MUTED: AtomicBool = AtomicBool::new(false);

pub fn set_muted(muted: bool) {
    MUTED.store(muted, Ordering::SeqCst);
}

/// The three cues. Each is a pair of short notes; direction carries the
/// meaning, so they are distinguishable without being musical.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Cue {
    /// The microphone is live — talk now.
    Open,
    /// The take was sent.
    Sent,
    /// Nothing was heard, or the take was dropped.
    Dropped,
}

impl Cue {
    /// (frequency Hz, duration ms) per note.
    fn notes(self) -> &'static [(f32, u64)] {
        match self {
            // Up: something is starting.
            Cue::Open => &[(660.0, 60), (990.0, 70)],
            // Up and short: done, going somewhere.
            Cue::Sent => &[(880.0, 55), (1320.0, 55)],
            // Down: nothing came of it.
            Cue::Dropped => &[(520.0, 70), (390.0, 90)],
        }
    }
}

/// Play a cue, on its own thread. Never blocks the caller and never fails
/// loudly: a machine with no output device is a machine that gets no cues,
/// not a broken voice loop.
pub fn play(cue: Cue) {
    if MUTED.load(Ordering::SeqCst) {
        return;
    }
    let _ = std::thread::Builder::new()
        .name("cue".into())
        .spawn(move || {
            if let Err(e) = blow(cue) {
                log::debug!("cue: {cue:?} not played ({e})");
            }
        });
}

fn blow(cue: Cue) -> Result<(), String> {
    let host = cpal::default_host();
    let device = host.default_output_device().ok_or("no output device")?;
    let config = device
        .default_output_config()
        .map_err(|e| e.to_string())?;
    let rate = config.sample_rate().0 as f32;
    let channels = config.channels() as usize;

    let samples = Arc::new(render(cue.notes(), rate));
    let cursor = Arc::new(Mutex::new(0usize));
    let total = samples.len();
    let feed = samples.clone();
    let at = cursor.clone();

    // f32 output only. Every desktop device this runs on reports f32, and the
    // fallback for one that does not is silence rather than three more
    // conversion arms for a beep.
    if config.sample_format() != cpal::SampleFormat::F32 {
        return Err(format!("output is {:?}, not f32", config.sample_format()));
    }

    let stream = device
        .build_output_stream(
            &config.into(),
            move |out: &mut [f32], _: &cpal::OutputCallbackInfo| {
                let mut i = at.lock().unwrap_or_else(|e| e.into_inner());
                for frame in out.chunks_mut(channels) {
                    let v = feed.get(*i).copied().unwrap_or(0.0);
                    if *i < total {
                        *i += 1;
                    }
                    for slot in frame.iter_mut() {
                        *slot = v;
                    }
                }
            },
            |e| log::debug!("cue: stream error: {e}"),
            None,
        )
        .map_err(|e| e.to_string())?;
    stream.play().map_err(|e| e.to_string())?;

    // Hold the stream open for the length of the sound plus a little, then
    // drop it. Keeping an output device open for a 130ms beep would be rude
    // to whatever else wants it.
    let ms: u64 = cue.notes().iter().map(|(_, d)| *d).sum();
    std::thread::sleep(Duration::from_millis(ms + 90));
    Ok(())
}

/// The notes, as samples, with a short fade at each edge.
///
/// The fade is not decoration: a sine that starts or stops at a non-zero
/// sample is a step, and a step is a click. 3ms of ramp is inaudible and
/// removes it.
fn render(notes: &[(f32, u64)], rate: f32) -> Vec<f32> {
    let fade = (rate * 0.003) as usize;
    let mut out = Vec::new();
    for (freq, ms) in notes {
        let count = ((rate as f64) * (*ms as f64) / 1000.0) as usize;
        for n in 0..count {
            let t = n as f32 / rate;
            let mut v = (t * freq * std::f32::consts::TAU).sin() * 0.22;
            if n < fade {
                v *= n as f32 / fade as f32;
            } else if n + fade >= count {
                v *= (count - n) as f32 / fade as f32;
            }
            out.push(v);
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn every_cue_renders_some_audible_samples() {
        for cue in [Cue::Open, Cue::Sent, Cue::Dropped] {
            let samples = render(cue.notes(), 48_000.0);
            assert!(!samples.is_empty(), "{cue:?}");
            let peak = samples.iter().fold(0.0f32, |m, s| m.max(s.abs()));
            assert!(peak > 0.1, "{cue:?} is inaudible (peak {peak})");
            assert!(peak <= 0.25, "{cue:?} is too loud (peak {peak})");
        }
    }

    #[test]
    fn a_cue_starts_and_ends_at_silence() {
        // Otherwise the tone begins with a click, which reads as a fault
        // rather than as a signal.
        let samples = render(Cue::Open.notes(), 48_000.0);
        assert!(samples[0].abs() < 0.001);
        assert!(samples[samples.len() - 1].abs() < 0.01);
    }

    #[test]
    fn the_open_cue_rises_and_the_dropped_cue_falls() {
        // The direction IS the meaning; two cues that both went up would need
        // to be learned rather than understood.
        let up = Cue::Open.notes();
        assert!(up[1].0 > up[0].0);
        let down = Cue::Dropped.notes();
        assert!(down[1].0 < down[0].0);
    }

    #[test]
    fn muting_silences_cues() {
        set_muted(true);
        play(Cue::Open); // must return without touching an audio device
        set_muted(false);
    }

    #[test]
    fn a_cue_is_short_enough_not_to_be_in_the_way() {
        for cue in [Cue::Open, Cue::Sent, Cue::Dropped] {
            let ms: u64 = cue.notes().iter().map(|(_, d)| *d).sum();
            assert!(ms <= 200, "{cue:?} lasts {ms}ms");
        }
    }
}

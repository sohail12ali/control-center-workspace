//! The word that decides whether anything else runs.
//!
//! ## Why this module exists
//!
//! Hands-free used to answer "was that addressed to me?" by recording every
//! sound in the room, sending 5-10 seconds of it through whisper, and matching
//! the resulting TEXT against the wake word. Three things were wrong with that,
//! and all three showed up in one log on 2026-09-16: five takes in a row, each
//! costing a second of inference, each discarded, and the microphone deaf for
//! the whole of each one.
//!
//! - It was **expensive**: a recogniser ran on speech nobody addressed to it.
//! - It was **deaf**: nothing said during transcription and dispatch survived,
//!   and the words most likely to be said there are the ones you are repeating
//!   because the assistant just ignored you.
//! - It was **unreliable**: `base.en` writes "console" as a different word
//!   often enough that a string comparison is not a gate, it is a lottery.
//!
//! So detection moves off the transcript and onto the audio stream, where the
//! rest of the world does it (Home Assistant's Assist pipeline, LiveKit,
//! pipecat): a small always-on spotter scores every frame, and whisper is not
//! started at all until the spotter fires.
//!
//! ## Why a wakeword you record yourself
//!
//! `rustpotter` compares incoming audio against a few recordings of the phrase
//! rather than a model trained on thousands of speakers. That is a worse
//! detector in the abstract and a better one here: it is trained on YOUR voice
//! saying YOUR phrase, it needs no ONNX runtime and no C toolchain, and it
//! carries no non-commercial licence on a pretrained model. The trade is that
//! it cannot work until you have recorded the phrase — so `available()` is
//! honest about that rather than the tray offering a switch that does nothing.
//!
//! ## What this module never does
//!
//! It never sends audio anywhere and it never writes any down. The strongest
//! form of the privacy promise hands-free has always made is the one this
//! module makes true: unaddressed speech is not merely discarded after
//! transcription, it is never transcribed at all.

use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU32, Ordering};
use std::sync::Mutex;

use rustpotter::{
    Rustpotter, RustpotterConfig, SampleFormat, ScoreMode, WakewordLoad, WakewordRef,
    WakewordRefBuildFromFiles, WakewordSave,
};

pub type WakeResult<T> = Result<T, String>;

/// Where wakewords live, relative to the repo root.
///
/// Beside the speech engine because it is the same kind of thing — a local
/// artefact a person installed deliberately — and gitignored because it is a
/// recording of somebody's voice.
pub const WAKE_DIR: &str = "desktop/stt/wake";

/// The file extension rustpotter uses for a built wakeword.
const WAKE_EXT: &str = "rpw";

/// How many MFCC coefficients describe a frame. Rustpotter's own tooling
/// uses 16, and a wakeword built at one size cannot be scored at another — so
/// changing this would silently invalidate every wakeword already recorded.
const MFCC_SIZE: u16 = 16;

/// How many recordings of the phrase make a usable wakeword. Fewer than three
/// and one unlucky take defines the template; more than eight stops helping.
pub const MIN_SAMPLES: usize = 3;
pub const MAX_SAMPLES: usize = 8;

/// The last score the spotter saw, x1000, for the diagnostics panel.
///
/// The thing that made this ticket hard to diagnose was that a user had no
/// number to look at — only "it didn't work". A live score turns that into
/// "it reaches 0.4 when I say it, and the threshold is 0.5".
static LAST_SCORE: AtomicU32 = AtomicU32::new(0);

/// The most recent firing, for `/voice/state`.
static LAST_FIRED: Mutex<Option<Fired>> = Mutex::new(None);

#[derive(Clone, Debug)]
pub struct Fired {
    pub name: String,
    pub score: f32,
    pub avg_score: f32,
}

pub fn last_score() -> f32 {
    LAST_SCORE.load(Ordering::Relaxed) as f32 / 1000.0
}

pub fn last_fired() -> Option<Fired> {
    LAST_FIRED.lock().unwrap_or_else(|e| e.into_inner()).clone()
}

fn dir(repo_root: &Path) -> PathBuf {
    repo_root.join(WAKE_DIR)
}

/// Every wakeword installed on this machine, by name.
pub fn installed(repo_root: &Path) -> Vec<String> {
    let mut names: Vec<String> = std::fs::read_dir(dir(repo_root))
        .into_iter()
        .flatten()
        .flatten()
        .filter(|e| e.path().extension().map(|x| x == WAKE_EXT).unwrap_or(false))
        .filter_map(|e| e.path().file_stem().map(|s| s.to_string_lossy().to_string()))
        .collect();
    names.sort();
    names
}

/// Can the spotter run at all on this machine?
///
/// Mirrors `stt::available` so the tray can ask one question per capability
/// and get an answer about THIS machine rather than about the feature in
/// principle.
pub fn available(repo_root: &Path) -> bool {
    !installed(repo_root).is_empty()
}

/// What to do about it, or nothing when there is nothing to do.
///
/// Empty when a wakeword is installed, matching `listen::hint` — a panel that
/// prints whatever is in this field must not tell someone to record a wake
/// word they have already recorded.
pub fn hint(repo_root: &Path) -> String {
    if available(repo_root) {
        return String::new();
    }
    format!(
        "no wake word recorded: Settings > Listening > Wake word records {MIN_SAMPLES} \
         samples of the phrase and builds it into {}",
        dir(repo_root).display()
    )
}

fn path_for(repo_root: &Path, name: &str) -> PathBuf {
    dir(repo_root).join(format!("{name}.{WAKE_EXT}"))
}

/// Where recordings of the phrase are kept until they are built into a
/// wakeword.
///
/// Under the cache rather than beside the wakeword: these are working files
/// with a short life, and one of them is a recording of somebody's voice that
/// should not outlive the build it was made for.
pub fn samples_dir(repo_root: &Path, name: &str) -> PathBuf {
    repo_root
        .join("console/.cache/desktop/wake-samples")
        .join(sanitise(name))
}

/// A wakeword name that is safe as a filename. Names come from a text box, and
/// both a wakeword and its samples are written to paths built from one.
pub fn sanitise(name: &str) -> String {
    name.trim()
        .chars()
        .map(|c| if c.is_ascii_alphanumeric() || c == '-' || c == '_' { c } else { '-' })
        .collect::<String>()
        .trim_matches('-')
        .to_lowercase()
}

/// The recordings made so far, oldest first.
pub fn samples(repo_root: &Path, name: &str) -> Vec<PathBuf> {
    let mut found: Vec<PathBuf> = std::fs::read_dir(samples_dir(repo_root, name))
        .into_iter()
        .flatten()
        .flatten()
        .map(|e| e.path())
        .filter(|p| p.extension().map(|x| x == "wav").unwrap_or(false))
        .collect();
    found.sort();
    found
}

/// Keep one recording of the phrase. Returns how many there are now.
pub fn save_sample(repo_root: &Path, name: &str, wav: &[u8]) -> WakeResult<usize> {
    let dir = samples_dir(repo_root, name);
    std::fs::create_dir_all(&dir).map_err(|e| format!("cannot create {}: {e}", dir.display()))?;
    let next = samples(repo_root, name).len() + 1;
    let path = dir.join(format!("{next:02}.wav"));
    std::fs::write(&path, wav).map_err(|e| format!("cannot write {}: {e}", path.display()))?;
    Ok(next)
}

/// Throw the recordings away — after a successful build, or when someone
/// starts again.
pub fn clear_samples(repo_root: &Path, name: &str) {
    let dir = samples_dir(repo_root, name);
    if let Err(e) = std::fs::remove_dir_all(&dir) {
        if e.kind() != std::io::ErrorKind::NotFound {
            log::warn!("wake: could not remove {}: {e}", dir.display());
        }
    }
}

/// Remove a wakeword and anything left over from building it.
pub fn forget(repo_root: &Path, name: &str) -> WakeResult<()> {
    let path = path_for(repo_root, &sanitise(name));
    match std::fs::remove_file(&path) {
        Ok(()) => {}
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}
        Err(e) => return Err(format!("cannot remove {}: {e}", path.display())),
    }
    clear_samples(repo_root, name);
    Ok(())
}

/// Build a wakeword from recordings of the phrase and save it.
///
/// The WAVs must be 16 kHz mono 16-bit — which is what `audio::Take::wav`
/// produces, so the recording flow hands these straight over.
pub fn train(
    repo_root: &Path,
    name: &str,
    samples: &[PathBuf],
    threshold: Option<f32>,
    avg_threshold: Option<f32>,
) -> WakeResult<PathBuf> {
    let name = sanitise(name);
    if name.is_empty() {
        return Err("a wake word needs a name".into());
    }
    if samples.len() < MIN_SAMPLES {
        return Err(format!(
            "{} recordings is not enough: say the phrase at least {MIN_SAMPLES} times",
            samples.len()
        ));
    }
    if samples.len() > MAX_SAMPLES {
        return Err(format!("more than {MAX_SAMPLES} recordings stops helping"));
    }
    let paths: Vec<String> = samples
        .iter()
        .map(|p| p.to_string_lossy().to_string())
        .collect();
    let wakeword = WakewordRef::new_from_sample_files(
        name.clone(),
        threshold,
        avg_threshold,
        paths,
        MFCC_SIZE,
    )?;
    let out = path_for(repo_root, &name);
    if let Some(parent) = out.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("cannot create {}: {e}", parent.display()))?;
    }
    wakeword.save_to_file(&out.to_string_lossy())?;
    log::info!("wake: built {name:?} from {} recordings", samples.len());
    Ok(out)
}

/// An always-on spotter over the microphone stream.
pub struct Spotter {
    inner: Rustpotter,
    /// Samples rustpotter has not been given yet, because it wants an exact
    /// frame and the microphone delivers whatever the device felt like.
    pending: Vec<i16>,
    frame: usize,
}

impl Spotter {
    /// Load every installed wakeword at the given sensitivity.
    ///
    /// `sensitivity` is 0.0..1.0 in the direction a person expects — higher
    /// means it fires more readily — and is turned into rustpotter's
    /// threshold, which runs the other way.
    pub fn new(repo_root: &Path, sensitivity: f32) -> WakeResult<Spotter> {
        let names = installed(repo_root);
        if names.is_empty() {
            return Err(hint(repo_root));
        }
        let mut config = RustpotterConfig::default();
        config.fmt.sample_rate = crate::audio::TARGET_HZ as usize;
        config.fmt.sample_format = SampleFormat::I16;
        config.fmt.channels = 1;
        // A phrase is scored against the best-matching template rather than
        // the average of all of them: recordings differ in pace, and the
        // average of two paces matches neither.
        config.detector.score_mode = ScoreMode::Max;
        config.detector.threshold = threshold_for(sensitivity);
        config.detector.avg_threshold = threshold_for(sensitivity) / 2.0;

        let mut inner = Rustpotter::new(&config)?;
        for name in &names {
            let path = path_for(repo_root, name);
            let wakeword = WakewordRef::load_from_file(&path.to_string_lossy())?;
            inner.add_wakeword_ref(name, wakeword)?;
        }
        let frame = inner.get_samples_per_frame();
        log::info!(
            "wake: spotting {names:?} at threshold {:.2} ({frame} samples per frame)",
            config.detector.threshold
        );
        Ok(Spotter { inner, pending: Vec::new(), frame })
    }

    /// Feed audio. Returns the firing, if this is the moment.
    ///
    /// Takes whatever length the ring handed over and cuts it into the frames
    /// rustpotter wants, keeping the remainder for next time — so a detection
    /// is never missed because it straddled two reads.
    pub fn push(&mut self, samples: &[i16]) -> Option<Fired> {
        self.pending.extend_from_slice(samples);
        let mut fired = None;
        while self.pending.len() >= self.frame {
            let frame: Vec<i16> = self.pending.drain(..self.frame).collect();
            if let Some(detection) = self.inner.process_samples(frame) {
                let hit = Fired {
                    name: detection.name.clone(),
                    score: detection.score,
                    avg_score: detection.avg_score,
                };
                LAST_SCORE.store((hit.score.clamp(0.0, 1.0) * 1000.0) as u32, Ordering::Relaxed);
                *LAST_FIRED.lock().unwrap_or_else(|e| e.into_inner()) = Some(hit.clone());
                fired = Some(hit);
                // Drop what is left: the rest of this read belongs to the
                // utterance, and the take about to start reads it from the
                // ring instead.
                self.pending.clear();
                break;
            }
            if let Some(partial) = self.inner.get_partial_detection() {
                LAST_SCORE.store(
                    (partial.score.clamp(0.0, 1.0) * 1000.0) as u32,
                    Ordering::Relaxed,
                );
            }
        }
        fired
    }

    /// Forget everything heard so far. Called after a take, so the utterance
    /// that was just answered cannot fire the spotter a second time.
    pub fn reset(&mut self) {
        self.inner.reset();
        self.pending.clear();
        LAST_SCORE.store(0, Ordering::Relaxed);
    }
}

/// Sensitivity (higher fires more readily) to rustpotter's threshold (higher
/// fires less readily).
///
/// Clamped well inside 0..1 at both ends: a threshold of 0 fires on silence
/// and a threshold of 1 never fires at all, and neither is a setting anyone
/// means to choose.
pub fn threshold_for(sensitivity: f32) -> f32 {
    let s = sensitivity.clamp(0.0, 1.0);
    (0.8 - 0.5 * s).clamp(0.3, 0.8)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sensitivity_runs_the_opposite_way_to_the_threshold() {
        assert!(threshold_for(1.0) < threshold_for(0.0),
                "more sensitive must mean a lower bar");
        assert!((threshold_for(0.5) - 0.55).abs() < 0.001);
    }

    #[test]
    fn the_threshold_never_reaches_either_useless_extreme() {
        // 0 fires on silence, 1 never fires. Both are settings a slider can
        // reach and nobody means.
        assert!(threshold_for(-5.0) <= 0.8 && threshold_for(-5.0) >= 0.3);
        assert!(threshold_for(5.0) >= 0.3);
    }

    #[test]
    fn a_machine_with_no_wakeword_says_so_rather_than_half_working() {
        let empty = std::env::temp_dir().join("t019-no-wake-here");
        assert!(!available(&empty));
        assert!(hint(&empty).contains("Settings"), "{}", hint(&empty));
        assert!(Spotter::new(&empty, 0.5).is_err());
    }

    /// 16 kHz mono 16-bit WAV to samples. Enough of a reader for our own
    /// fixtures, which are the only WAVs this test needs to open.
    fn read_wav(path: &Path) -> Vec<i16> {
        let bytes = std::fs::read(path).expect("fixture is there");
        bytes[44..]
            .chunks_exact(2)
            .map(|b| i16::from_le_bytes([b[0], b[1]]))
            .collect()
    }

    fn fixtures() -> PathBuf {
        Path::new(env!("CARGO_MANIFEST_DIR"))
            .parent()
            .expect("desktop/")
            .join("tests/fixtures")
    }

    /// Build the fixture wakeword into a temporary root and spot with it.
    ///
    /// The recordings are SYNTHETIC — piper saying "Console." at three paces,
    /// resampled to 16 kHz, committed as fixtures. That is not a substitute
    /// for a real voice, and it is not pretending to be: what it pins is that
    /// the whole path works — build a template from WAVs, load it, frame the
    /// audio, score it, and fire on the phrase rather than on speech in
    /// general. Every one of those was broken or absent before T-019, and
    /// none of them needs a microphone to test.
    fn trained_spotter(root: &Path) -> Spotter {
        let dir = fixtures();
        let samples: Vec<PathBuf> = (1..=3)
            .map(|i| dir.join(format!("wake-console-{i}.wav")))
            .collect();
        train(root, "console", &samples, None, None).expect("builds");
        Spotter::new(root, 0.5).expect("loads")
    }

    #[test]
    fn the_spotter_fires_on_the_phrase_it_was_trained_on() {
        let root = std::env::temp_dir().join("t019-spot-yes");
        let _ = std::fs::remove_dir_all(&root);
        let mut spotter = trained_spotter(&root);
        let said = read_wav(&fixtures().join("wake-console-said.wav"));
        // Fed in ring-sized reads, the way the loop feeds it — a detection
        // must not depend on the whole utterance arriving in one call.
        let mut fired = None;
        for chunk in said.chunks(480) {
            if let Some(hit) = spotter.push(chunk) {
                fired = Some(hit);
                break;
            }
        }
        let hit = fired.expect("\"Console, what is open?\" must wake it");
        assert_eq!(hit.name, "console");
        assert!(hit.score > 0.0);
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn the_spotter_ignores_speech_that_is_not_the_phrase() {
        // The property that makes an always-on microphone tolerable: ordinary
        // talk in the room never reaches the recogniser at all.
        let root = std::env::temp_dir().join("t019-spot-no");
        let _ = std::fs::remove_dir_all(&root);
        let mut spotter = trained_spotter(&root);
        for name in ["wake-not-said.wav", "wake-mentioned.wav"] {
            spotter.reset();
            let audio = read_wav(&fixtures().join(name));
            let mut fired = false;
            for chunk in audio.chunks(480) {
                fired |= spotter.push(chunk).is_some();
            }
            assert!(!fired, "{name} must not wake it");
        }
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn a_built_wakeword_is_what_makes_the_machine_available() {
        let root = std::env::temp_dir().join("t019-spot-avail");
        let _ = std::fs::remove_dir_all(&root);
        assert!(!available(&root));
        let _ = trained_spotter(&root);
        assert!(available(&root), "the tray may only offer it once it exists");
        assert_eq!(installed(&root), vec!["console".to_string()]);
        assert!(hint(&root).is_empty(),
                "nothing to advise once it is recorded — this was live for a \
                 while, telling people to record what they already had");
        forget(&root, "console").expect("removes");
        assert!(!available(&root));
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn training_refuses_too_few_recordings() {
        let root = std::env::temp_dir().join("t019-train");
        let err = train(&root, "console", &[PathBuf::from("a.wav")], None, None)
            .unwrap_err();
        assert!(err.contains("at least"), "{err}");
    }

    #[test]
    fn training_refuses_a_nameless_wakeword() {
        let root = std::env::temp_dir().join("t019-train");
        let samples = vec![PathBuf::from("a.wav"); 3];
        assert!(train(&root, "  ", &samples, None, None).is_err());
    }
}

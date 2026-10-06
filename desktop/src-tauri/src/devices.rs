//! Which audio device to use, chosen by NAME.
//!
//! ## Why a name and not an index
//!
//! An index is a position in whatever order the OS listed the devices today.
//! Plug in a headset and every index after it moves; the saved setting then
//! points at a different device and nobody is told. A name survives that, so
//! `input_device` / `output_device` store one, and empty means "whatever the
//! system default is" - which is also exactly what the shell did before the
//! settings existed.
//!
//! ## Why the matching is one pure function
//!
//! `pick_by_name` is the only place a wanted name is compared with a device
//! name. The console and the UI show the verdict this module computes; they do
//! not match anything themselves (T-031 D-5, D-17), so there is never a second
//! opinion about which device a setting means.
//!
//! The rule: an exact match (case-insensitive, trimmed) wins; else a substring
//! that identifies exactly ONE device; else no match. Several candidates is "no
//! match" and the candidates are reported, because for a microphone guessing
//! is the wrong way to fail.
//!
//! ## What happens when the name is not there
//!
//! The system default is used, one warning is logged per change, and the
//! verdict says `fallback: true`. That is the pre-setting behaviour, so a
//! missing headset degrades to what the user had before instead of to a
//! silent assistant.
//!
//! ## The one place the OS default is asked for
//!
//! Everything that needs a device (capture, playback, cues, the tests) goes
//! through this module, so a chosen device cannot be bypassed by a call site
//! that forgot. A source scan in the tests keeps it that way.

use std::sync::Mutex;
use std::time::{Duration, Instant};

use cpal::traits::{DeviceTrait, HostTrait};

/// Which way the audio flows.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Direction {
    Input,
    Output,
}

impl Direction {
    /// What a person calls it, for messages.
    pub fn noun(self) -> &'static str {
        match self {
            Direction::Input => "microphone",
            Direction::Output => "output device",
        }
    }
}

/// What the machine offers right now, per direction, plus the OS defaults.
///
/// Names only: a `cpal::Device` is not something to cache or share, and a name
/// is all the matcher and the UI need.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct DeviceList {
    pub inputs: Vec<String>,
    pub outputs: Vec<String>,
    /// `Some("")` is possible: a default exists but its name cannot be read.
    pub default_input: Option<String>,
    pub default_output: Option<String>,
}

impl DeviceList {
    pub fn names(&self, direction: Direction) -> &[String] {
        match direction {
            Direction::Input => &self.inputs,
            Direction::Output => &self.outputs,
        }
    }

    pub fn default_name(&self, direction: Direction) -> Option<&str> {
        match direction {
            Direction::Input => self.default_input.as_deref(),
            Direction::Output => self.default_output.as_deref(),
        }
    }
}

/// Every device the host can currently see, by direction, with its name.
///
/// Never panics and never fails: an error from the host (no audio service, no
/// permission) is an empty list, which every caller already treats as "no
/// device".
fn scan(host: &cpal::Host, direction: Direction) -> Vec<(String, cpal::Device)> {
    let devices = match direction {
        Direction::Input => host.input_devices(),
        Direction::Output => host.output_devices(),
    };
    match devices {
        Ok(found) => found
            .filter_map(|d| d.name().ok().map(|name| (name, d)))
            .collect(),
        Err(e) => {
            log::debug!("devices: cannot list {} devices: {e}", direction.noun());
            Vec::new()
        }
    }
}

fn default_device(host: &cpal::Host, direction: Direction) -> Option<cpal::Device> {
    match direction {
        Direction::Input => host.default_input_device(),
        Direction::Output => host.default_output_device(),
    }
}

/// Ask the OS what is plugged in. Fresh every call - the cached view for hot
/// paths is `cached`.
pub fn enumerate() -> DeviceList {
    let host = cpal::default_host();
    let name_of = |d: cpal::Device| d.name().unwrap_or_default();
    DeviceList {
        inputs: scan(&host, Direction::Input).into_iter().map(|(n, _)| n).collect(),
        outputs: scan(&host, Direction::Output).into_iter().map(|(n, _)| n).collect(),
        default_input: default_device(&host, Direction::Input).map(name_of),
        default_output: default_device(&host, Direction::Output).map(name_of),
    }
}

/// How a wanted name matched the names on offer. Indexes are positions in the
/// list that was searched.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Pick {
    /// Nothing was asked for: use the system default.
    Default,
    Exact(usize),
    Substring(usize),
    /// No single device matched. `candidates` is empty when nothing matched at
    /// all and lists the contenders when the name was ambiguous.
    None { candidates: Vec<String> },
}

/// Match `wanted` against `names`. The one matcher (BR-6).
pub fn pick_by_name(wanted: &str, names: &[String]) -> Pick {
    let wanted = wanted.trim();
    if wanted.is_empty() {
        return Pick::Default;
    }
    let wanted = wanted.to_lowercase();
    if let Some(i) = names.iter().position(|n| n.trim().to_lowercase() == wanted) {
        return Pick::Exact(i);
    }
    let hits: Vec<usize> = names
        .iter()
        .enumerate()
        .filter(|(_, n)| n.to_lowercase().contains(&wanted))
        .map(|(i, _)| i)
        .collect();
    match hits.as_slice() {
        [one] => Pick::Substring(*one),
        _ => Pick::None {
            candidates: hits.iter().map(|i| names[*i].clone()).collect(),
        },
    }
}

/// How the wanted name related to the device that ended up in use.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum MatchKind {
    Exact,
    Substring,
    /// The name matched nothing (or several): the default is in use instead.
    None,
    /// No name was configured.
    Default,
}

impl MatchKind {
    pub fn as_str(self) -> &'static str {
        match self {
            MatchKind::Exact => "exact",
            MatchKind::Substring => "substring",
            MatchKind::None => "none",
            MatchKind::Default => "default",
        }
    }
}

/// What a `Pick` means once the system default is known.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Choice {
    /// Position in the searched list, or `None` to use the OS default device.
    pub index: Option<usize>,
    /// The device that will be used. `None` only when there is no device.
    pub name: Option<String>,
    pub kind: MatchKind,
    /// A name was configured but it is the default that is in use.
    pub fallback: bool,
    pub candidates: Vec<String>,
}

/// Turn a pick into a decision: a matched name is used, anything else is the
/// system default. Pure, so the fallback rule needs no hardware to test.
pub fn choose(pick: Pick, names: &[String], default: Option<&str>) -> Choice {
    let default = default.map(str::to_string);
    match pick {
        Pick::Default => Choice {
            index: None,
            name: default,
            kind: MatchKind::Default,
            fallback: false,
            candidates: Vec::new(),
        },
        Pick::Exact(i) | Pick::Substring(i) => Choice {
            index: Some(i),
            name: Some(names[i].clone()),
            kind: if matches!(pick, Pick::Exact(_)) { MatchKind::Exact } else { MatchKind::Substring },
            fallback: false,
            candidates: Vec::new(),
        },
        Pick::None { candidates } => Choice {
            index: None,
            name: default,
            kind: MatchKind::None,
            fallback: true,
            candidates,
        },
    }
}

/// The answer to "which device does this setting mean right now".
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Verdict {
    /// What was asked for, trimmed. Empty means the system default.
    pub configured: String,
    /// The device actually in use, or `None` when there is none.
    pub resolved: Option<String>,
    pub match_kind: MatchKind,
    pub fallback: bool,
    pub candidates: Vec<String>,
}

/// The whole decision, from a wanted name and what is on offer. Both the
/// cached description (`current`) and the open path (`resolve`) go through
/// this, so what the UI is told and what gets opened cannot disagree.
fn decide(wanted: &str, names: &[String], default: Option<&str>) -> Choice {
    choose(pick_by_name(wanted, names), names, default)
}

fn verdict_of(wanted: &str, choice: Choice) -> Verdict {
    Verdict {
        configured: wanted.trim().to_string(),
        resolved: choice.name,
        match_kind: choice.kind,
        fallback: choice.fallback,
        candidates: choice.candidates,
    }
}

impl Verdict {
    /// The device in use, or empty when there is none.
    pub fn name(&self) -> String {
        self.resolved.clone().unwrap_or_default()
    }
}

/// Resolve `wanted` against one direction of `list`. It only ever reads that
/// direction's names and default, so a name that exists only as an output can
/// never be returned for an input.
pub fn resolve_name(direction: Direction, wanted: &str, list: &DeviceList) -> Verdict {
    let names = list.names(direction);
    verdict_of(wanted, decide(wanted, names, list.default_name(direction)))
}

/// The two preferences and a generation per preference.
///
/// The generation is what lets an OPEN device notice a change: a `Mic` records
/// the generation it was opened under and reopens when it no longer matches.
/// It moves only when the value really changes, so the settings poke that
/// re-applies an unchanged preference does not make a microphone reopen.
///
/// Name and generation are read together under one lock, so a reader cannot
/// pair a new name with an old generation.
pub struct Prefs {
    input: Mutex<Slot>,
    output: Mutex<Slot>,
}

struct Slot {
    name: String,
    generation: u64,
}

impl Prefs {
    pub const fn new() -> Self {
        Self {
            input: Mutex::new(Slot { name: String::new(), generation: 0 }),
            output: Mutex::new(Slot { name: String::new(), generation: 0 }),
        }
    }

    fn slot(&self, direction: Direction) -> std::sync::MutexGuard<'_, Slot> {
        let slot = match direction {
            Direction::Input => &self.input,
            Direction::Output => &self.output,
        };
        slot.lock().unwrap_or_else(|e| e.into_inner())
    }

    fn set(&self, direction: Direction, name: &str) -> bool {
        let name = name.trim();
        let mut slot = self.slot(direction);
        if slot.name == name {
            return false;
        }
        slot.name = name.to_string();
        slot.generation += 1;
        true
    }

    /// Returns true, and bumps the generation, only if the value changed.
    pub fn set_input(&self, name: &str) -> bool {
        self.set(Direction::Input, name)
    }

    pub fn set_output(&self, name: &str) -> bool {
        self.set(Direction::Output, name)
    }

    pub fn input_preference(&self) -> String {
        self.slot(Direction::Input).name.clone()
    }

    pub fn output_preference(&self) -> String {
        self.slot(Direction::Output).name.clone()
    }

    pub fn input_generation(&self) -> u64 {
        self.slot(Direction::Input).generation
    }

    pub fn output_generation(&self) -> u64 {
        self.slot(Direction::Output).generation
    }

    /// The preference and its generation, read together.
    pub fn snapshot(&self, direction: Direction) -> (String, u64) {
        let slot = self.slot(direction);
        (slot.name.clone(), slot.generation)
    }
}

/// The shell's own preferences. Tests build their own `Prefs` instead, so the
/// default parallel `cargo test` cannot interfere through this one.
pub static PREFS: Prefs = Prefs::new();

/// Has the preference moved on since a device was opened under
/// `opened_generation`?
pub fn needs_reopen(opened_generation: u64, current_generation: u64) -> bool {
    opened_generation != current_generation
}

/// How long a device list is trusted.
pub const CACHE_TTL: Duration = Duration::from_secs(1);

/// A short-lived copy of the device list.
///
/// `audio::available()` and `device_name()` are asked from `/health` and from
/// `/listen/state`, which the voice panel polls twice a second on a bridge that
/// handles one request at a time. Listing the devices on every one of those is
/// work nobody needs: the answer does not change between two polls. A second is
/// short enough that a plugged-in headset still shows up promptly.
///
/// The clock is an argument, not a call, so a test can move time without
/// sleeping. The key is the pair of preference generations: changing a
/// preference drops the copy, so a new setting is never described from an old
/// listing.
pub struct ListCache {
    slot: Mutex<Option<Cached>>,
}

struct Cached {
    taken: Instant,
    key: (u64, u64),
    list: DeviceList,
}

impl ListCache {
    pub const fn new() -> Self {
        Self { slot: Mutex::new(None) }
    }

    fn lock(&self) -> std::sync::MutexGuard<'_, Option<Cached>> {
        self.slot.lock().unwrap_or_else(|e| e.into_inner())
    }

    /// The cached list while it is fresh and the key unchanged, else a new one.
    ///
    /// The lock is not held while `scan` runs: two callers may both list, which
    /// is harmless, and one slow host call never blocks the other.
    pub fn get(&self, now: Instant, key: (u64, u64), scan: impl FnOnce() -> DeviceList) -> DeviceList {
        if let Some(c) = self.lock().as_ref() {
            if c.key == key && now.saturating_duration_since(c.taken) < CACHE_TTL {
                return c.list.clone();
            }
        }
        self.fresh(now, key, scan)
    }

    /// Always list, and keep the result. What the Refresh button wants.
    pub fn fresh(&self, now: Instant, key: (u64, u64), scan: impl FnOnce() -> DeviceList) -> DeviceList {
        let list = scan();
        *self.lock() = Some(Cached { taken: now, key, list: list.clone() });
        list
    }
}

static CACHE: ListCache = ListCache::new();

fn generations() -> (u64, u64) {
    (PREFS.input_generation(), PREFS.output_generation())
}

/// The device list for hot paths: at most one real enumeration per second.
pub fn cached() -> DeviceList {
    CACHE.get(Instant::now(), generations(), enumerate)
}

/// A real enumeration, which also refreshes the copy `cached` serves. For the
/// Refresh button, which must see a device that was plugged in a moment ago.
pub fn refresh() -> DeviceList {
    CACHE.fresh(Instant::now(), generations(), enumerate)
}

/// Remembers which unresolved preference has already been warned about.
///
/// A missing device is worth one line in the log, not one per poll: `current`
/// runs twice a second while the voice panel is open. `note(Some(key))` is true
/// the first time a key is seen, and again after a different key or after
/// `note(None)` (the preference resolved, so a later loss is news again).
pub struct WarnOnce {
    last: Mutex<Option<String>>,
}

impl WarnOnce {
    pub const fn new() -> Self {
        Self { last: Mutex::new(None) }
    }

    pub fn note(&self, key: Option<&str>) -> bool {
        let mut last = self.last.lock().unwrap_or_else(|e| e.into_inner());
        match key {
            None => {
                *last = None;
                false
            }
            Some(k) if last.as_deref() == Some(k) => false,
            Some(k) => {
                *last = Some(k.to_string());
                true
            }
        }
    }
}

static INPUT_WARNED: WarnOnce = WarnOnce::new();
static OUTPUT_WARNED: WarnOnce = WarnOnce::new();

fn warn_on_fallback(direction: Direction, verdict: &Verdict) {
    let warned = match direction {
        Direction::Input => &INPUT_WARNED,
        Direction::Output => &OUTPUT_WARNED,
    };
    let key = verdict.fallback.then_some(verdict.configured.as_str());
    if !warned.note(key) {
        return;
    }
    let why = if verdict.candidates.is_empty() {
        "is not connected".to_string()
    } else {
        format!("matches several devices ({})", verdict.candidates.join(", "))
    };
    log::warn!(
        "devices: {} {:?} {why}; using the system default ({:?})",
        direction.noun(),
        verdict.configured,
        verdict.name()
    );
}

/// What a caller is told when there is no device to open. The microphone text
/// keeps the word "microphone": `hands_free` stops on it instead of spinning.
pub fn no_device_error(direction: Direction, configured: &str) -> String {
    let default = match direction {
        Direction::Input => "default input device",
        Direction::Output => "default output device",
    };
    let configured = configured.trim();
    if configured.is_empty() {
        format!("no {}: nothing is set as the {default}", direction.noun())
    } else {
        format!(
            "no {}: {configured:?} is not connected and nothing is set as the {default}",
            direction.noun()
        )
    }
}

/// A device that is open, and what was decided to get it.
pub struct Resolved {
    pub device: cpal::Device,
    pub name: String,
    /// The preference generation this was resolved under: the device is stale
    /// the moment `needs_reopen(generation, current)` is true.
    pub generation: u64,
}

/// The input device to open: the chosen one, else the system default.
pub fn resolve_input() -> Result<Resolved, String> {
    resolve(Direction::Input)
}

/// The output device to open: the chosen one, else the system default.
pub fn resolve_output() -> Result<Resolved, String> {
    resolve(Direction::Output)
}

fn resolve(direction: Direction) -> Result<Resolved, String> {
    // Preference and generation together, BEFORE listing: a change that lands
    // while the host is being asked leaves the device older than the
    // generation, so it is reopened, never silently kept.
    let (wanted, generation) = PREFS.snapshot(direction);
    let host = cpal::default_host();
    let mut found = scan(&host, direction);
    let default = default_device(&host, direction);
    let default_name = default.as_ref().map(|d| d.name().unwrap_or_default());
    let names: Vec<String> = found.iter().map(|(n, _)| n.clone()).collect();

    let choice = decide(&wanted, &names, default_name.as_deref());
    let index = choice.index;
    let verdict = verdict_of(&wanted, choice);
    warn_on_fallback(direction, &verdict);

    let device = match index {
        Some(i) => Some(found.swap_remove(i).1),
        None => default,
    };
    match device {
        Some(device) => Ok(Resolved { device, name: verdict.name(), generation }),
        None => Err(no_device_error(direction, &wanted)),
    }
}

/// The verdict for the preference now in force, described from the cached
/// list. What `audio::available()` and `device_name()` answer from: cheap
/// enough for a poll, and the same decision `resolve` makes when it opens.
pub fn current(direction: Direction) -> Verdict {
    let (wanted, _) = PREFS.snapshot(direction);
    let verdict = resolve_name(direction, &wanted, &cached());
    warn_on_fallback(direction, &verdict);
    verdict
}

#[cfg(test)]
mod tests {
    use super::*;

    fn names(list: &[&str]) -> Vec<String> {
        list.iter().map(|s| s.to_string()).collect()
    }

    // -- the matcher (AC-52) ---------------------------------------------

    #[test]
    fn an_empty_or_blank_name_means_the_default() {
        let n = names(&["Headset", "Speakers"]);
        assert_eq!(pick_by_name("", &n), Pick::Default);
        assert_eq!(pick_by_name("   \t", &n), Pick::Default);
        assert_eq!(pick_by_name("", &[]), Pick::Default);
    }

    #[test]
    fn an_exact_match_beats_an_earlier_substring() {
        // "Mic" is a substring of the first name and exactly the second.
        let n = names(&["USB Mic Array", "Mic"]);
        assert_eq!(pick_by_name("Mic", &n), Pick::Exact(1));
    }

    #[test]
    fn case_and_surrounding_spaces_do_not_matter() {
        let n = names(&["Realtek Microphone Array"]);
        assert_eq!(pick_by_name("  REALTEK microphone ARRAY  ", &n), Pick::Exact(0));
        // A stored name with stray spaces still matches its trimmed twin.
        let padded = names(&["  Headset  "]);
        assert_eq!(pick_by_name("headset", &padded), Pick::Exact(0));
    }

    #[test]
    fn a_unique_substring_is_accepted() {
        let n = names(&["Speakers (Realtek)", "Headset (USB Audio)"]);
        assert_eq!(pick_by_name("usb", &n), Pick::Substring(1));
    }

    #[test]
    fn an_ambiguous_substring_is_no_match_and_lists_the_candidates() {
        let n = names(&["Headset (USB 1)", "Speakers", "Headset (USB 2)"]);
        assert_eq!(
            pick_by_name("headset", &n),
            Pick::None { candidates: names(&["Headset (USB 1)", "Headset (USB 2)"]) }
        );
    }

    #[test]
    fn nothing_matching_is_no_match_with_no_candidates() {
        let n = names(&["Speakers"]);
        assert_eq!(pick_by_name("webcam", &n), Pick::None { candidates: vec![] });
        assert_eq!(pick_by_name("webcam", &[]), Pick::None { candidates: vec![] });
    }

    #[test]
    fn non_ascii_names_match() {
        let n = names(&["Mikrofon (Réalité)", "Höhrer"]);
        assert_eq!(pick_by_name("mikrofon (RÉALITÉ)", &n), Pick::Exact(0));
        assert_eq!(pick_by_name("höh", &n), Pick::Substring(1));
    }

    #[test]
    fn identical_names_give_the_first() {
        let n = names(&["Headset", "Headset"]);
        assert_eq!(pick_by_name("Headset", &n), Pick::Exact(0));
    }

    // -- the verdict (AC-53) ---------------------------------------------

    fn list() -> DeviceList {
        DeviceList {
            inputs: names(&["Array Mic", "USB Headset Mic"]),
            outputs: names(&["Speakers", "USB Headset"]),
            default_input: Some("Array Mic".into()),
            default_output: Some("Speakers".into()),
        }
    }

    #[test]
    fn a_resolved_name_is_always_in_the_requested_direction() {
        let l = list();
        // "Speakers" exists only as an output: for an input it is no match,
        // and what is used is the INPUT default.
        let v = resolve_name(Direction::Input, "Speakers", &l);
        assert_eq!(v.match_kind, MatchKind::None);
        assert!(v.fallback);
        assert_eq!(v.resolved.as_deref(), Some("Array Mic"));
        // And the reverse.
        let v = resolve_name(Direction::Output, "Array Mic", &l);
        assert!(v.fallback);
        assert_eq!(v.resolved.as_deref(), Some("Speakers"));
        // Whatever is asked, a resolved name is in that direction's list.
        for wanted in ["", "Speakers", "Array Mic", "USB", "headset", "nothing"] {
            for direction in [Direction::Input, Direction::Output] {
                let v = resolve_name(direction, wanted, &l);
                let resolved = v.resolved.expect("this machine has both defaults");
                assert!(l.names(direction).contains(&resolved), "{direction:?} {wanted:?} -> {resolved}");
            }
        }
    }

    #[test]
    fn a_verdict_reports_what_was_configured_and_how_it_matched() {
        let l = list();
        let v = resolve_name(Direction::Input, "  usb headset mic ", &l);
        assert_eq!(v.configured, "usb headset mic");
        assert_eq!(v.match_kind, MatchKind::Exact);
        assert!(!v.fallback);
        assert_eq!(v.resolved.as_deref(), Some("USB Headset Mic"));

        let v = resolve_name(Direction::Input, "", &l);
        assert_eq!((v.match_kind, v.fallback), (MatchKind::Default, false));
        assert_eq!(v.resolved.as_deref(), Some("Array Mic"));

        let v = resolve_name(Direction::Output, "usb", &l);
        assert_eq!((v.match_kind, v.fallback), (MatchKind::Substring, false));
        assert_eq!(v.resolved.as_deref(), Some("USB Headset"));
    }

    #[test]
    fn with_no_device_at_all_nothing_is_resolved() {
        let v = resolve_name(Direction::Input, "", &DeviceList::default());
        assert_eq!(v.resolved, None);
        let v = resolve_name(Direction::Output, "Speakers", &DeviceList::default());
        assert_eq!(v.resolved, None);
        assert!(v.fallback);
    }

    // -- preferences and generations (AC-56, pure half) ------------------

    #[test]
    fn the_generation_moves_only_when_the_value_changes() {
        let p = Prefs::new();
        assert_eq!((p.input_generation(), p.output_generation()), (0, 0));
        assert!(!p.set_input(""), "the default is already empty");
        assert_eq!(p.input_generation(), 0);

        assert!(p.set_input("Headset"));
        assert_eq!(p.input_generation(), 1);
        assert!(!p.set_input("Headset"), "re-applying the same value");
        assert!(!p.set_input("  Headset  "), "the same value with spaces");
        assert_eq!(p.input_generation(), 1, "so nothing reopens");

        assert!(p.set_input("Array Mic"));
        assert_eq!(p.input_generation(), 2);
        assert_eq!(p.input_preference(), "Array Mic");
        // Input and output are independent.
        assert_eq!(p.output_generation(), 0);
        assert!(p.set_output("Speakers"));
        assert_eq!((p.input_generation(), p.output_generation()), (2, 1));
        assert_eq!(p.output_preference(), "Speakers");
        assert_eq!(p.snapshot(Direction::Output), ("Speakers".to_string(), 1));
    }

    #[test]
    fn a_device_reopens_when_the_generation_moved() {
        assert!(!needs_reopen(0, 0));
        assert!(!needs_reopen(7, 7));
        assert!(needs_reopen(0, 1));
        assert!(needs_reopen(3, 2), "any difference, not only growth");
    }

    // -- fallback and its single warning (AC-55) -------------------------

    #[test]
    fn an_unresolved_name_picks_the_default_and_says_fallback() {
        let l = list();
        let on_offer = l.names(Direction::Input);
        let c = decide("Bluetooth Headset", on_offer, l.default_name(Direction::Input));
        assert_eq!(c.index, None, "no device of that name: the OS default device is opened");
        assert_eq!(c.name.as_deref(), Some("Array Mic"));
        assert_eq!(c.kind, MatchKind::None);
        assert!(c.fallback);

        // Ambiguity falls back too, and says who the contenders were.
        let l = DeviceList {
            inputs: names(&["Headset (USB 1)", "Headset (USB 2)", "Array Mic"]),
            default_input: Some("Array Mic".into()),
            ..DeviceList::default()
        };
        let v = resolve_name(Direction::Input, "headset", &l);
        assert!(v.fallback);
        assert_eq!(v.resolved.as_deref(), Some("Array Mic"));
        assert_eq!(v.candidates, names(&["Headset (USB 1)", "Headset (USB 2)"]));

        // A matched name is NOT a fallback and opens that device by position.
        let c = decide("array", l.names(Direction::Input), Some("Array Mic"));
        assert_eq!((c.index, c.fallback), (Some(2), false));
    }

    #[test]
    fn the_warning_fires_once_for_a_repeated_unresolved_preference() {
        let w = WarnOnce::new();
        assert!(w.note(Some("Headset")), "the first sighting warns");
        for _ in 0..5 {
            assert!(!w.note(Some("Headset")), "a poll twice a second must not repeat it");
        }
    }

    #[test]
    fn the_warning_fires_again_after_the_preference_changes_or_resolves() {
        let w = WarnOnce::new();
        assert!(w.note(Some("Headset")));
        assert!(w.note(Some("Webcam")), "a different preference is new news");
        assert!(!w.note(Some("Webcam")));
        assert!(!w.note(None), "a resolved preference never warns");
        assert!(w.note(Some("Webcam")), "and losing the device again is news again");
    }

    // -- the cache, on an injected clock (CR-37) --------------------------

    fn counting_scan(calls: &std::cell::Cell<u32>) -> impl FnOnce() -> DeviceList + '_ {
        move || {
            calls.set(calls.get() + 1);
            list()
        }
    }

    #[test]
    fn a_second_call_within_a_second_does_not_enumerate_again() {
        let cache = ListCache::new();
        let t0 = Instant::now();
        let calls = std::cell::Cell::new(0);
        assert_eq!(cache.get(t0, (0, 0), counting_scan(&calls)), list());
        assert_eq!(calls.get(), 1);
        cache.get(t0 + Duration::from_millis(10), (0, 0), counting_scan(&calls));
        cache.get(t0 + Duration::from_millis(999), (0, 0), counting_scan(&calls));
        assert_eq!(calls.get(), 1, "two polls inside the TTL are served from the copy");
    }

    #[test]
    fn a_call_after_a_second_or_after_a_preference_change_enumerates_again() {
        let cache = ListCache::new();
        let t0 = Instant::now();
        let calls = std::cell::Cell::new(0);
        cache.get(t0, (0, 0), counting_scan(&calls));
        cache.get(t0 + CACHE_TTL, (0, 0), counting_scan(&calls));
        assert_eq!(calls.get(), 2, "at the TTL the copy has expired");

        // Within the TTL of the copy just taken, but the input preference moved.
        cache.get(t0 + CACHE_TTL + Duration::from_millis(5), (1, 0), counting_scan(&calls));
        assert_eq!(calls.get(), 3, "an input change drops the copy");
        cache.get(t0 + CACHE_TTL + Duration::from_millis(6), (1, 1), counting_scan(&calls));
        assert_eq!(calls.get(), 4, "and so does an output change");
        cache.get(t0 + CACHE_TTL + Duration::from_millis(7), (1, 1), counting_scan(&calls));
        assert_eq!(calls.get(), 4, "but the same key is served again");
    }

    #[test]
    fn a_refresh_bypasses_the_copy_and_replaces_it() {
        let cache = ListCache::new();
        let t0 = Instant::now();
        let calls = std::cell::Cell::new(0);
        cache.get(t0, (0, 0), counting_scan(&calls));
        cache.fresh(t0 + Duration::from_millis(1), (0, 0), counting_scan(&calls));
        assert_eq!(calls.get(), 2, "the Refresh button always asks the OS");
        cache.get(t0 + Duration::from_millis(2), (0, 0), counting_scan(&calls));
        assert_eq!(calls.get(), 2, "and what it found is what polls see next");
    }

    // -- the messages (AC-57) ---------------------------------------------

    #[test]
    fn the_no_device_texts_name_what_is_missing() {
        let mic = no_device_error(Direction::Input, "");
        assert!(mic.contains("microphone") && mic.contains("default input device"), "{mic}");
        let mic = no_device_error(Direction::Input, "  Headset ");
        assert!(mic.contains("microphone") && mic.contains("\"Headset\""), "{mic}");
        let out = no_device_error(Direction::Output, "");
        assert!(out.contains("no output device"), "{out}");
    }

    #[test]
    fn the_input_default_text_is_the_one_the_hint_already_used() {
        // `listen::hint` and the old `Mic::open` said exactly this; unchanged
        // wording means nothing that matched on it has to move.
        assert_eq!(
            no_device_error(Direction::Input, ""),
            "no microphone: nothing is set as the default input device"
        );
    }

    // -- the host (AC-49, RS half) ---------------------------------------

    #[test]
    fn enumerating_returns_without_a_panic_and_keeps_the_directions_apart() {
        let l = enumerate();
        println!("devices: inputs {:?}, outputs {:?}", l.inputs, l.outputs);
        println!("devices: default in {:?}, default out {:?}", l.default_input, l.default_output);
        if l.inputs.is_empty() && l.outputs.is_empty() {
            println!("skipped: no audio device on this machine; empty lists are the expected answer");
        }
        // A default belongs to its own direction's list when that list exists.
        if let (Some(d), false) = (&l.default_input, l.inputs.is_empty()) {
            assert!(l.inputs.contains(d), "default input {d:?} is not in the input list");
        }
        if let (Some(d), false) = (&l.default_output, l.outputs.is_empty()) {
            assert!(l.outputs.contains(d), "default output {d:?} is not in the output list");
        }
    }

    // -- playback and cues (AC-54) -----------------------------------------

    #[test]
    fn an_output_is_resolved_from_the_output_side_only() {
        // A machine whose only default is an INPUT: asking for an output must
        // not borrow it, and the failure text must be the output one.
        let l = DeviceList {
            inputs: names(&["Array Mic"]),
            outputs: names(&["Speakers", "USB Headset"]),
            default_input: Some("Array Mic".into()),
            default_output: None,
        };
        let v = resolve_name(Direction::Output, "", &l);
        assert_eq!(v.resolved, None, "the input default is not an output device");
        assert!(no_device_error(Direction::Output, &v.configured).contains("no output device"));

        // A chosen output is used even with no output default, and a name that
        // only exists as an input is not one.
        let v = resolve_name(Direction::Output, "usb headset", &l);
        assert_eq!((v.match_kind, v.fallback), (MatchKind::Exact, false));
        assert_eq!(v.resolved.as_deref(), Some("USB Headset"));
        let v = resolve_name(Direction::Output, "Array Mic", &l);
        assert!(v.fallback && v.resolved.is_none());

        // And with both present, the unresolved output falls to the OUTPUT default.
        let l = DeviceList { default_output: Some("Speakers".into()), ..l };
        let v = resolve_name(Direction::Output, "gone", &l);
        assert_eq!((v.resolved.as_deref(), v.fallback), (Some("Speakers"), true));
    }

    /// Every `.rs` file under `dir`.
    fn rust_sources(dir: &std::path::Path, out: &mut Vec<std::path::PathBuf>) {
        for entry in std::fs::read_dir(dir).expect("the source directory is readable").flatten() {
            let path = entry.path();
            if path.is_dir() {
                rust_sources(&path, out);
            } else if path.extension().map(|e| e == "rs").unwrap_or(false) {
                out.push(path);
            }
        }
    }

    #[test]
    fn nothing_outside_this_module_asks_the_os_for_its_default_device() {
        // The needles are built from two pieces so that this file does not
        // match itself (it is also skipped by path, and `examples/` is not
        // under `src/`).
        let needles = [
            format!("default_{}_device(", "input"),
            format!("default_{}_device(", "output"),
        ];
        let src = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("src");
        let mine = src.join("devices.rs");
        let mut files = Vec::new();
        rust_sources(&src, &mut files);
        assert!(files.len() > 10, "the scan found {} files under {}", files.len(), src.display());

        let mut offenders = Vec::new();
        for file in files.iter().filter(|f| **f != mine) {
            let text = std::fs::read_to_string(file).unwrap_or_default();
            for (n, line) in text.lines().enumerate() {
                if needles.iter().any(|needle| line.contains(needle.as_str())) {
                    offenders.push(format!("{}:{}", file.display(), n + 1));
                }
            }
        }
        assert!(
            offenders.is_empty(),
            "these call the OS default device directly instead of `devices::resolve_*`: {offenders:?}"
        );

        // A control: the scan must be able to see the real call sites, or an
        // empty result above would prove nothing.
        let own = std::fs::read_to_string(&mine).expect("devices.rs is readable");
        for needle in &needles {
            assert!(own.contains(needle.as_str()), "the scan's own control found no {needle}");
        }
    }
}

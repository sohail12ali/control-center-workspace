//! What the tray is showing, and why.
//!
//! A pure state machine, deliberately separated from the Tauri calls that
//! paint it. The reason is testability: "does a permission card pause
//! listening" and "does an interrupted turn go back to idle" are questions
//! about transitions, and answering them through a real tray would need a
//! desktop session, a live chat and a microphone. Here they are table tests.
//!
//! `apply` returns whether the VISUAL changed. The caller then re-reads
//! `icon()` and `tooltip()` — rather than the machine returning a list of
//! effects to perform — because there is exactly one thing to repaint and a
//! command queue for it would be more machinery than the problem has.

use crate::icons::{icon_bytes, wants_template, State};

/// Everything that can move the tray. Named after what HAPPENED, not what
/// the tray should do about it, so the policy stays in one place (`apply`).
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Event {
    /// Always-on listening was turned on (true) or off (false). The bool is
    /// whether a wake word is required, which is what decides between "the
    /// mic is open and gated" and "the mic is open and everything goes".
    Armed(bool),
    /// The mic opened (push-to-talk held, or listen toggled on).
    ListenStart,
    /// Audio captured; transcribing it.
    Transcribing,
    /// A turn was sent and the model is working.
    TurnStart,
    /// The assistant started reading a reply aloud.
    SpeakStart,
    /// It finished reading, or was told to stop.
    SpeakStop,
    /// The turn ended — normally, in error, or interrupted.
    TurnEnd,
    /// A gated tool is waiting on a human.
    ApprovalNeeded,
    /// That card was answered, either way.
    ApprovalResolved,
    /// Replies muted / unmuted.
    Mute(bool),
    /// Listening cancelled without a transcript (escape, empty take).
    Cancel,
}

/// The tray's own view of the assistant. `muted` and `needs_approval` are
/// orthogonal to `state`: a permission card can appear while speaking, and
/// muting does not stop a turn.
#[derive(Clone, Debug)]
pub struct Assistant {
    state: State,
    muted: bool,
    needs_approval: bool,
    backend: String,
    /// Hands-free is on with a wake word required.
    armed: bool,
    /// Listening was interrupted by a permission card and should not
    /// silently resume — see `ApprovalNeeded`.
    listen_paused: bool,
}

impl Default for Assistant {
    fn default() -> Self {
        Self {
            state: State::Idle,
            muted: false,
            needs_approval: false,
            backend: String::new(),
            armed: false,
            listen_paused: false,
        }
    }
}

impl Assistant {
    pub fn state(&self) -> State {
        self.state
    }

    pub fn muted(&self) -> bool {
        self.muted
    }

    pub fn needs_approval(&self) -> bool {
        self.needs_approval
    }

    /// What the tray is actually SHOWING, which is not always `state()`:
    /// armed and muted are standing facts folded in at paint time. Exposed so
    /// a log line can name the icon the user is looking at rather than the
    /// internal state behind it.
    pub fn shown(&self) -> State {
        self.visual_state()
    }

    pub fn armed(&self) -> bool {
        self.armed
    }

    pub fn listen_paused(&self) -> bool {
        self.listen_paused
    }

    pub fn set_backend(&mut self, backend: &str) -> bool {
        if self.backend == backend {
            return false;
        }
        self.backend = backend.to_string();
        true
    }

    /// The icon bytes for the current state, already resolved for this OS.
    pub fn icon(&self) -> &'static [u8] {
        icon_bytes(self.visual_state(), self.needs_approval, wants_template())
    }

    /// Muted replaces the icon only while nothing more urgent is happening:
    /// if the assistant is listening or working, THAT is what the user needs
    /// to see. A mic that is open must never be shown as a mute glyph.
    ///
    /// Armed is the same argument one step further. While hands-free holds the
    /// microphone open under a wake word, an idle-looking tray would be a
    /// lie — so armed replaces idle, and replaces muted too, because muting is
    /// about replies while an open microphone is about the room.
    ///
    /// Armed also outranks `Listening`, which looks backwards and is not.
    /// Hands-free opens a take, discards it, and opens another — so a tray
    /// that followed the takes would flicker red several times a minute while
    /// telling the user nothing they can act on. What they can act on is the
    /// standing fact: the mic is open and gated by a wake word. `Listening`
    /// is then reserved for the case where it means something sharper —
    /// push-to-talk, or hands-free with the wake word switched off, where
    /// every word you say is on its way out.
    fn visual_state(&self) -> State {
        match self.state {
            State::Listening if self.armed => State::Armed,
            State::Idle if self.armed => State::Armed,
            State::Idle if self.muted => State::Muted,
            other => other,
        }
    }

    /// Hover text. Always names the backend when one is known, because that
    /// is where a screenshot or a transcript would be going — the cloud
    /// reminder the design asks to keep visible rather than buried.
    pub fn tooltip(&self) -> String {
        let backend = if self.backend.is_empty() {
            String::new()
        } else {
            format!(" ({})", self.backend)
        };
        if self.needs_approval {
            return "Delivery Console - permission needed, open the window".into();
        }
        match self.visual_state() {
            State::Idle => format!("Delivery Console - idle{backend}"),
            State::Armed => "Delivery Console - hands-free on, say the wake word".into(),
            State::Listening => "Delivery Console - listening".into(),
            State::Thinking => format!("Delivery Console - working{backend}"),
            State::Speaking => "Delivery Console - speaking (click to stop)".into(),
            State::Muted => format!("Delivery Console - replies muted{backend}"),
        }
    }

    /// Fold one event in. Returns true when the icon or tooltip should be
    /// repainted, so the caller never has to diff anything itself.
    pub fn apply(&mut self, event: Event) -> bool {
        let before = (self.visual_state(), self.needs_approval, self.tooltip());

        match event {
            Event::Armed(on) => {
                self.armed = on;
                if !on && self.state == State::Listening {
                    // Hands-free was turned off mid-take. The loop releases
                    // the take; the icon must not stay red waiting for it.
                    self.state = State::Idle;
                }
            }
            Event::ListenStart => {
                // A card on screen wins: opening the mic while a human is
                // being asked to approve something would record them
                // answering a question they had not read yet.
                if !self.needs_approval {
                    self.state = State::Listening;
                    self.listen_paused = false;
                }
            }
            Event::Transcribing | Event::TurnStart => self.state = State::Thinking,
            Event::SpeakStart => {
                // Muted means nothing is read aloud, so there is no speaking
                // state to enter — guarding here rather than at every caller
                // keeps "muted is silent" a property of the machine.
                if !self.muted {
                    self.state = State::Speaking;
                }
            }
            Event::SpeakStop => {
                if self.state == State::Speaking {
                    self.state = State::Idle;
                }
            }
            Event::TurnEnd => {
                // Not unconditional: a reply that is being read aloud
                // outlives the turn that produced it.
                if self.state != State::Speaking {
                    self.state = State::Idle;
                }
            }
            Event::ApprovalNeeded => {
                self.needs_approval = true;
                if self.state == State::Listening {
                    self.state = State::Idle;
                    self.listen_paused = true;
                }
            }
            Event::ApprovalResolved => self.needs_approval = false,
            Event::Mute(on) => {
                self.muted = on;
                if on && self.state == State::Speaking {
                    self.state = State::Idle;
                }
            }
            Event::Cancel => {
                if self.state == State::Listening || self.state == State::Speaking {
                    self.state = State::Idle;
                }
                self.listen_paused = false;
            }
        }

        (self.visual_state(), self.needs_approval, self.tooltip()) != before
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn a() -> Assistant {
        Assistant::default()
    }

    #[test]
    fn a_fresh_tray_is_idle_and_unmuted() {
        let t = a();
        assert_eq!(t.state(), State::Idle);
        assert!(!t.muted() && !t.needs_approval());
    }

    #[test]
    fn a_full_voice_turn_returns_to_idle() {
        let mut t = a();
        for (event, want) in [
            (Event::ListenStart, State::Listening),
            (Event::Transcribing, State::Thinking),
            (Event::SpeakStart, State::Speaking),
            (Event::SpeakStop, State::Idle),
        ] {
            t.apply(event);
            assert_eq!(t.state(), want);
        }
    }

    #[test]
    fn a_permission_card_pauses_listening() {
        // The load-bearing one: the mic must not stay open while a human is
        // being asked to approve something.
        let mut t = a();
        t.apply(Event::ListenStart);
        assert_eq!(t.state(), State::Listening);
        t.apply(Event::ApprovalNeeded);
        assert_eq!(t.state(), State::Idle);
        assert!(t.listen_paused(), "the pause must be recorded, not implied");
        assert!(t.needs_approval());
    }

    #[test]
    fn listening_cannot_start_while_a_card_is_open() {
        let mut t = a();
        t.apply(Event::ApprovalNeeded);
        t.apply(Event::ListenStart);
        assert_eq!(t.state(), State::Idle);
    }

    #[test]
    fn listening_can_start_again_once_the_card_is_answered() {
        let mut t = a();
        t.apply(Event::ApprovalNeeded);
        t.apply(Event::ApprovalResolved);
        t.apply(Event::ListenStart);
        assert_eq!(t.state(), State::Listening);
        assert!(!t.listen_paused());
    }

    #[test]
    fn muted_never_enters_the_speaking_state() {
        let mut t = a();
        t.apply(Event::Mute(true));
        t.apply(Event::SpeakStart);
        assert_eq!(t.state(), State::Idle);
    }

    #[test]
    fn muting_mid_sentence_stops_showing_speaking() {
        let mut t = a();
        t.apply(Event::SpeakStart);
        assert_eq!(t.state(), State::Speaking);
        t.apply(Event::Mute(true));
        assert_eq!(t.state(), State::Idle);
    }

    #[test]
    fn the_mute_glyph_never_hides_an_open_mic() {
        let mut t = a();
        t.apply(Event::Mute(true));
        t.apply(Event::ListenStart);
        // Muted affects replies, not the microphone. Showing the mute glyph
        // here would tell the user nothing is happening while they are being
        // recorded.
        assert_eq!(t.icon(), icon_bytes(State::Listening, false, wants_template()));
    }

    #[test]
    fn muted_shows_the_mute_glyph_when_otherwise_idle() {
        let mut t = a();
        t.apply(Event::Mute(true));
        assert_eq!(t.icon(), icon_bytes(State::Muted, false, wants_template()));
    }

    #[test]
    fn arming_shows_the_armed_icon_rather_than_idle() {
        // The whole point: a microphone held open by hands-free must never
        // present as an idle tray.
        let mut t = a();
        assert!(t.apply(Event::Armed(true)), "arming is visible");
        assert_eq!(t.state(), State::Idle, "armed is a standing fact, not a state");
        assert_eq!(t.icon(), icon_bytes(State::Armed, false, wants_template()));
        assert!(t.tooltip().contains("hands-free"));
    }

    #[test]
    fn shown_is_what_the_user_sees_not_the_internal_state() {
        // These two disagree exactly where it matters, which is why the paint
        // log reports `shown` — a line saying "idle" while a red icon is on
        // screen is worse than no line at all.
        let mut t = a();
        t.apply(Event::Armed(true));
        assert_eq!(t.state(), State::Idle);
        assert_eq!(t.shown(), State::Armed);
        t.apply(Event::Armed(false));
        t.apply(Event::Mute(true));
        assert_eq!(t.shown(), State::Muted);
    }

    #[test]
    fn armed_outranks_muted() {
        // Muting is about replies; an open microphone is about the room.
        let mut t = a();
        t.apply(Event::Mute(true));
        t.apply(Event::Armed(true));
        assert_eq!(t.icon(), icon_bytes(State::Armed, false, wants_template()));
    }

    #[test]
    fn takes_inside_hands_free_do_not_flicker_the_icon() {
        // Hands-free opens a take, discards it, opens another. Following that
        // would flash the tray red several times a minute and tell the user
        // nothing they can act on.
        let mut t = a();
        t.apply(Event::Armed(true));
        assert!(!t.apply(Event::ListenStart), "no repaint for a gated take");
        assert_eq!(t.icon(), icon_bytes(State::Armed, false, wants_template()));
        assert!(!t.apply(Event::Cancel), "and none when it is discarded");
    }

    #[test]
    fn push_to_talk_still_shows_listening() {
        // `Listening` keeps the sharper meaning: every word is on its way out.
        let mut t = a();
        t.apply(Event::ListenStart);
        assert_eq!(t.icon(), icon_bytes(State::Listening, false, wants_template()));
    }

    #[test]
    fn disarming_mid_take_does_not_leave_the_icon_open() {
        let mut t = a();
        t.apply(Event::Armed(true));
        t.apply(Event::ListenStart);
        t.apply(Event::Armed(false));
        assert_eq!(t.state(), State::Idle);
        assert_eq!(t.icon(), icon_bytes(State::Idle, false, wants_template()));
    }

    #[test]
    fn a_turn_ending_does_not_cut_off_a_reply_being_read() {
        let mut t = a();
        t.apply(Event::TurnStart);
        t.apply(Event::SpeakStart);
        t.apply(Event::TurnEnd);
        assert_eq!(t.state(), State::Speaking);
        t.apply(Event::SpeakStop);
        assert_eq!(t.state(), State::Idle);
    }

    #[test]
    fn the_approval_badge_survives_a_state_change() {
        // "Needs approval" happens DURING another state; replacing the icon
        // outright would hide what the assistant is doing.
        let mut t = a();
        t.apply(Event::TurnStart);
        t.apply(Event::ApprovalNeeded);
        assert_eq!(
            t.icon(),
            icon_bytes(State::Thinking, true, wants_template())
        );
    }

    #[test]
    fn cancel_closes_the_mic_and_clears_the_pause() {
        let mut t = a();
        t.apply(Event::ListenStart);
        t.apply(Event::Cancel);
        assert_eq!(t.state(), State::Idle);
        assert!(!t.listen_paused());
    }

    #[test]
    fn apply_reports_whether_the_visual_changed() {
        let mut t = a();
        assert!(t.apply(Event::ListenStart), "idle -> listening is visible");
        assert!(
            !t.apply(Event::ListenStart),
            "listening -> listening repaints nothing"
        );
    }

    #[test]
    fn the_tooltip_names_the_backend_where_a_transcript_would_go() {
        let mut t = a();
        t.set_backend("claude");
        assert!(t.tooltip().contains("claude"));
        t.apply(Event::TurnStart);
        assert!(t.tooltip().contains("claude"));
    }

    #[test]
    fn an_open_card_says_so_in_the_tooltip() {
        let mut t = a();
        t.apply(Event::ApprovalNeeded);
        assert!(t.tooltip().contains("permission needed"));
    }
}

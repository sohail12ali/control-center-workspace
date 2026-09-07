//! The tray state icons, compiled into the binary.
//!
//! `include_bytes!` rather than reading from disk at runtime: the shell must
//! show the right icon on a machine where the repo has moved, and a missing
//! asset should be a BUILD failure, not a silently wrong icon in the tray of
//! a shipped binary. Twenty small PNGs cost about 10 KB in total.
//!
//! The assets are generated and committed by `desktop/icons/gen_tray_icons.py`
//! — see that script for why each state is distinguishable by shape and not
//! only by colour.

/// What the assistant is doing, as far as the tray is concerned.
///
/// Deliberately smaller than the set of things that can happen: `Transcribing`
/// and `Thinking` share one icon because the user cannot act differently on
/// them, and an icon that changes twice in a second reads as a flicker rather
/// than as information.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum State {
    Idle,
    Listening,
    Thinking,
    Speaking,
    Muted,
}

impl State {
    pub fn as_str(self) -> &'static str {
        match self {
            State::Idle => "idle",
            State::Listening => "listening",
            State::Thinking => "thinking",
            State::Speaking => "speaking",
            State::Muted => "muted",
        }
    }
}

macro_rules! icon_set {
    ($name:literal) => {
        (
            include_bytes!(concat!("../icons/tray/", $name, ".png")),
            include_bytes!(concat!("../icons/tray/", $name, "-approval.png")),
            include_bytes!(concat!("../icons/tray/", $name, "-template.png")),
            include_bytes!(concat!("../icons/tray/", $name, "-approval-template.png")),
        )
    };
}

type Set = (&'static [u8], &'static [u8], &'static [u8], &'static [u8]);

const IDLE: Set = icon_set!("idle");
const LISTENING: Set = icon_set!("listening");
const THINKING: Set = icon_set!("thinking");
const SPEAKING: Set = icon_set!("speaking");
const MUTED: Set = icon_set!("muted");

/// The PNG for a state, optionally badged with the needs-approval dot.
///
/// `template` picks the monochrome rendering macOS tints for the menu bar;
/// Windows and Linux take the colour one. The choice is made at the call
/// site by target_os rather than here, so this stays a pure lookup.
pub fn icon_bytes(state: State, approval: bool, template: bool) -> &'static [u8] {
    let set = match state {
        State::Idle => IDLE,
        State::Listening => LISTENING,
        State::Thinking => THINKING,
        State::Speaking => SPEAKING,
        State::Muted => MUTED,
    };
    match (approval, template) {
        (false, false) => set.0,
        (true, false) => set.1,
        (false, true) => set.2,
        (true, true) => set.3,
    }
}

/// True on the platform whose tray wants a tinted template image.
pub const fn wants_template() -> bool {
    cfg!(target_os = "macos")
}

#[cfg(test)]
mod tests {
    use super::*;

    const ALL: [State; 5] = [
        State::Idle,
        State::Listening,
        State::Thinking,
        State::Speaking,
        State::Muted,
    ];

    #[test]
    fn every_variant_is_a_real_png() {
        for state in ALL {
            for approval in [false, true] {
                for template in [false, true] {
                    let bytes = icon_bytes(state, approval, template);
                    assert_eq!(
                        &bytes[..8],
                        b"\x89PNG\r\n\x1a\n",
                        "{} approval={} template={} is not a PNG",
                        state.as_str(),
                        approval,
                        template
                    );
                }
            }
        }
    }

    #[test]
    fn every_variant_is_32x32() {
        // The IHDR width/height sit at a fixed offset in a PNG. A wrong size
        // shows up as a blurry tray icon, which is easy to miss by eye.
        for state in ALL {
            let bytes = icon_bytes(state, false, false);
            let w = u32::from_be_bytes(bytes[16..20].try_into().unwrap());
            let h = u32::from_be_bytes(bytes[20..24].try_into().unwrap());
            assert_eq!((w, h), (32, 32), "{}", state.as_str());
        }
    }

    #[test]
    fn no_two_states_share_an_icon() {
        // The bug this catches actually happened: the macOS template
        // rendering flattened colour to black, so every state came out as
        // the same featureless disc until the glyphs were made cut-outs.
        for template in [false, true] {
            for (i, a) in ALL.iter().enumerate() {
                for b in ALL.iter().skip(i + 1) {
                    assert_ne!(
                        icon_bytes(*a, false, template),
                        icon_bytes(*b, false, template),
                        "{} and {} share an icon (template={})",
                        a.as_str(),
                        b.as_str(),
                        template
                    );
                }
            }
        }
    }

    #[test]
    fn the_approval_badge_changes_the_icon() {
        for state in ALL {
            for template in [false, true] {
                assert_ne!(
                    icon_bytes(state, false, template),
                    icon_bytes(state, true, template),
                    "{} badge is invisible (template={})",
                    state.as_str(),
                    template
                );
            }
        }
    }
}

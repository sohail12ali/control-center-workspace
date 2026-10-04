//! `desktop/features.toml`, as the thing the tray is BUILT from.
//!
//! ## Why this module exists
//!
//! The registry always called itself authoritative — "the honesty registry the
//! tray and Settings project from", in `desktop/tests/test_features.py`'s own
//! words — and a Python test held it to matching what the code does. But the
//! menu itself was hand-written: `tray.rs` listed eight items, while the file
//! marked sixteen features available. Clipboard copy, clipboard send, both
//! captures and the whole listening submenu were implemented, declared, and
//! unreachable, because nobody had typed them into the builder a second time.
//!
//! Two sources of truth drift. One does not. So the file is parsed and the
//! menu is generated, and the only thing left to write by hand is what an id
//! DOES — which is genuinely code, and which `tray.rs` warns about at startup
//! if a shown row has no arm.
//!
//! ## Why compile-time
//!
//! `include_str!`, not a runtime read. The registry ships with the binary, so
//! there is no path to get wrong, no file to be missing, and no way for a
//! shell to start with a menu that silently fell back to a default. A parse
//! failure is a failed build, which is where a malformed committed config
//! belongs.

use std::sync::OnceLock;

const REGISTRY: &str = include_str!("../../features.toml");

/// Where a row appears, verbatim from the file's `tray` field.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Placement {
    /// A disabled label, not a button.
    Header,
    /// An ordinary row, at the root or inside its `parent`.
    Show,
    /// Owns other rows.
    Submenu,
    /// Not a menu row at all. Often still a real feature —
    /// `pause_listen_on_permission` is a behaviour, not something you click.
    Hide,
}

impl Placement {
    fn parse(raw: &str) -> Self {
        match raw {
            "header" => Placement::Header,
            "submenu" => Placement::Submenu,
            "show" => Placement::Show,
            // Anything unrecognised is hidden rather than guessed at. A typo
            // in the registry should cost a missing row, not an item whose
            // behaviour nobody chose.
            _ => Placement::Hide,
        }
    }
}

#[derive(Clone, Debug)]
pub struct Feature {
    pub id: String,
    pub label: String,
    pub placement: Placement,
    pub parent: String,
    /// Can the host actually perform this today?
    pub available: bool,
    /// Shown to the user when `available` is false. The registry requires one
    /// for every unavailable row, and the Python test enforces that.
    pub reason_unavailable: String,
    /// `none` | `gated` | `dangerous`.
    pub risk: String,
    /// The tray may open the window or start listening; it must not approve.
    /// A row with this set NEVER performs its action from the menu.
    pub never_one_click: bool,
    /// A state carrying a tick, rather than a command.
    pub check: bool,
}

impl Feature {
    /// Does this row appear in the menu at all?
    pub fn in_menu(&self) -> bool {
        self.placement != Placement::Hide
    }
}

fn parse(source: &str) -> Vec<Feature> {
    let doc: toml::Value = match source.parse() {
        Ok(v) => v,
        Err(e) => {
            // Unreachable in a shipped binary — the same string is parsed by
            // the unit test below, so a malformed registry fails the build.
            log::error!("features: registry did not parse: {e}");
            return Vec::new();
        }
    };
    let rows = doc
        .get("features")
        .and_then(|f| f.as_array())
        .cloned()
        .unwrap_or_default();

    let mut out = Vec::with_capacity(rows.len());
    for row in rows {
        let string = |key: &str| {
            row.get(key)
                .and_then(|v| v.as_str())
                .unwrap_or_default()
                .to_string()
        };
        let flag = |key: &str| row.get(key).and_then(|v| v.as_bool()).unwrap_or(false);
        let id = string("id");
        if id.is_empty() {
            continue;
        }
        out.push(Feature {
            label: {
                let label = string("label");
                if label.is_empty() {
                    id.clone()
                } else {
                    label
                }
            },
            placement: Placement::parse(&string("tray")),
            parent: string("parent"),
            available: flag("available"),
            reason_unavailable: string("reason_unavailable"),
            risk: string("risk"),
            never_one_click: flag("never_one_click"),
            check: flag("check"),
            id,
        });
    }
    out
}

/// Every row, in the order the file lists them.
///
/// File order IS menu order. That is deliberate: the registry is grouped by
/// `group` already and reads top to bottom the way the menu should, so a
/// separate ordering field would be a second thing to keep in step.
pub fn all() -> &'static [Feature] {
    static ROWS: OnceLock<Vec<Feature>> = OnceLock::new();
    ROWS.get_or_init(|| parse(REGISTRY))
}

/// One row by id, or `None`.
pub fn get(id: &str) -> Option<&'static Feature> {
    all().iter().find(|f| f.id == id)
}

/// The rows belonging to `parent`, in file order.
pub fn children_of(parent: &str) -> Vec<&'static Feature> {
    all()
        .iter()
        .filter(|f| f.parent == parent && f.in_menu())
        .collect()
}

/// Top-level rows: in the menu, and owned by no submenu.
pub fn roots() -> Vec<&'static Feature> {
    all()
        .iter()
        .filter(|f| f.in_menu() && f.parent.is_empty())
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_shipped_registry_parses() {
        // The build cannot catch a malformed `include_str!`, so this does.
        assert!(!all().is_empty(), "the registry produced no rows");
    }

    #[test]
    fn every_row_has_an_id_and_a_label() {
        for f in all() {
            assert!(!f.id.is_empty());
            assert!(!f.label.is_empty(), "{} has no label", f.id);
        }
    }

    #[test]
    fn every_unavailable_menu_row_can_say_why() {
        // A greyed-out row with no explanation is worse than no row: it tells
        // you something exists and refuses to say why you cannot have it.
        for f in all() {
            if f.in_menu() && !f.available {
                assert!(!f.reason_unavailable.is_empty(),
                        "{} is shown, unavailable, and silent about it", f.id);
            }
        }
    }

    #[test]
    fn the_registry_still_describes_the_menu_this_ticket_expects() {
        // Pinned so a row cannot quietly leave the menu. The count is the
        // point: eight items were built while sixteen features were declared
        // available, and one of those sixteen
        // (`pause_listen_on_permission`) is a behaviour rather than a row —
        // hence fifteen.
        let shown = all().iter().filter(|f| f.in_menu() && f.available).count();
        assert_eq!(shown, 15, "available menu rows");
        assert!(all().iter().any(|f| f.id == "clipboard_copy_last" && f.in_menu()));
        assert!(all().iter().any(|f| f.id == "capture_region" && f.in_menu()));
    }

    #[test]
    fn a_submenu_owns_its_children() {
        let listen = children_of("listen_mode");
        let ids: Vec<&str> = listen.iter().map(|f| f.id.as_str()).collect();
        assert_eq!(ids, vec!["listen_off", "listen_short_take", "listen_hands_free"]);
        // And a child is never also a root, or it would appear twice.
        assert!(roots().iter().all(|f| f.id != "listen_off"));
    }

    #[test]
    fn the_gated_capture_and_clipboard_rows_refuse_one_click() {
        // The registry's own rule: the tray may open the window, it must not
        // approve. These three are the ones that would send pixels or a
        // password somewhere if it did.
        for id in ["clipboard_send", "capture_this_turn", "capture_region"] {
            let row = all().iter().find(|f| f.id == id).expect(id);
            assert!(row.never_one_click, "{id} must never act from the tray");
            assert_eq!(row.risk, "gated");
        }
    }

    #[test]
    fn unknown_placements_hide_rather_than_guess() {
        let rows = parse("[[features]]\nid = \"x\"\ntray = \"sideways\"\n");
        assert_eq!(rows[0].placement, Placement::Hide);
    }

    #[test]
    fn a_row_with_no_id_is_skipped_not_shown_blank() {
        let rows = parse("[[features]]\nlabel = \"nameless\"\ntray = \"show\"\n");
        assert!(rows.is_empty());
    }
}

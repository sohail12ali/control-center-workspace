"""desktop/features.toml — T-002 skeleton flags."""

import os
import re
import tomllib

DESKTOP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(DESKTOP, "features.toml")

SKELETON = {
    "session_backend",
    "show_window",
    "new_chat",
    "mute_replies",
    "interrupt",
    "quit",
}


def _features():
    with open(PATH, "rb") as fh:
        return tomllib.load(fh)["features"]


class TestSkeletonAvailable:
    def test_skeleton_ids_available(self):
        rows = {row["id"]: row for row in _features()}
        assert set(SKELETON) <= set(rows)
        for fid in SKELETON:
            assert rows[fid]["skeleton"] is True
            assert rows[fid]["available"] is True

    def test_availability_matches_what_is_actually_built(self):
        """This file is the honesty registry the tray and Settings project
        from, so a row claiming more than the code does is a lie with a UI
        attached.

        It used to assert that NOTHING outside the T-002 skeleton was
        available, which was true when the skeleton was all there was. Voice,
        clipboard and capture have since landed, so the check is now the exact
        set — which still fails loudly if a row is flipped without the work,
        and equally if work lands without the row being flipped.
        """
        built = {
            # T-002 skeleton
            "session_backend", "show_window", "new_chat", "interrupt",
            "mute_replies", "quit",
            # T-005: clipboard and capture over the native bridge
            "clipboard_menu", "clipboard_copy_last", "clipboard_send",
            "capture_this_turn", "capture_region",
            # T-006: voice
            "listen_mode", "listen_off", "listen_short_take",
            "pause_listen_on_permission",
            # T-008: always-on listening, behind a wake word
            "listen_hands_free",
        }
        available = {row["id"] for row in _features() if row["available"]}
        assert available == built, (
            "features.toml disagrees with what is built. "
            "Claiming more: %s. Understating: %s"
            % (sorted(available - built), sorted(built - available)))

    def test_every_unavailable_row_says_why(self):
        # An unavailable row with no reason shows the user a greyed control
        # and no explanation, which is the thing this registry exists to avoid.
        for row in _features():
            if not row["available"]:
                assert row["reason_unavailable"].strip(), row["id"]

    def test_no_listen_clipboard_capture_in_skeleton(self):
        for row in _features():
            if not row.get("skeleton"):
                continue
            assert row["group"] not in ("listen", "clipboard", "capture", "watch")


TRAY_RS = os.path.join(DESKTOP, "src-tauri", "src", "tray.rs")


def _dispatched():
    """The ids `tray.rs` declares it can carry out.

    Read from the `DISPATCHED` list rather than by parsing the `match` arms:
    the arms group ids with `|` and nest inside other matches, so scraping
    them is a small parser waiting to be wrong. The list is one place, the
    Rust `warn_about_drift` reads the same list, and this asserts the list is
    honest about the registry.
    """
    with open(TRAY_RS, encoding="utf-8") as fh:
        source = fh.read()
    start = source.index("const DISPATCHED")
    body = source[start:source.index("];", start)]
    return set(re.findall(r'"([a-z_]+)"', body))


class TestTheTrayCarriesOutWhatTheRegistryOffers:
    """The drift this whole ticket exists for.

    `features.toml` marked sixteen features available; `tray.rs` hand-wrote
    eight menu items. Nothing anywhere compared the two, so clipboard copy,
    clipboard send, both captures and the entire listening submenu were
    implemented, declared available, and unreachable from the menu.

    The menu's shape is now generated from the registry
    (`desktop/src-tauri/src/features.rs`), so a row cannot go missing. What
    can still drift is the dispatch — a row that appears and does nothing —
    and that is what these two assertions close, from both directions.
    """

    def test_every_available_menu_row_has_a_dispatch_arm(self):
        # A header is a label and a submenu is a container; neither is clicked.
        clickable = {
            row["id"] for row in _features()
            if row["available"] and row["tray"] in ("show",)
        }
        missing = sorted(clickable - _dispatched())
        assert not missing, (
            "features.toml offers these as available, but tray.rs has no arm "
            "for them — they would appear in the menu and do nothing: %s"
            % missing)

    def test_nothing_is_dispatched_that_the_registry_does_not_declare(self):
        """The other direction. An arm with no row is dead code that reads as
        a working feature to anyone grepping for it."""
        ids = {row["id"] for row in _features()}
        stray = sorted(_dispatched() - ids)
        assert not stray, (
            "tray.rs dispatches ids that are not in features.toml: %s" % stray)

    def test_the_gated_rows_are_declared_never_one_click(self):
        """The registry's own rule, pinned where it is easy to break: the tray
        may open the window, it must not approve. These three are the ones
        that would put pixels or a clipboard — which can hold a password —
        somewhere else if a single click were enough."""
        rows = {row["id"]: row for row in _features()}
        for fid in ("clipboard_send", "capture_this_turn", "capture_region"):
            assert rows[fid]["never_one_click"] is True, fid
            assert rows[fid]["risk"] == "gated", fid

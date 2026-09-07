"""desktop/features.toml — T-002 skeleton flags."""

import os
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

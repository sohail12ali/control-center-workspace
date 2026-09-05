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

    def test_non_skeleton_unavailable(self):
        for row in _features():
            if row["id"] in SKELETON:
                continue
            assert row["available"] is False, row["id"]

    def test_no_listen_clipboard_capture_in_skeleton(self):
        for row in _features():
            if not row.get("skeleton"):
                continue
            assert row["group"] not in ("listen", "clipboard", "capture", "watch")

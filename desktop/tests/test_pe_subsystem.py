"""PE subsystem check — the definitive proof of the cause-A fix.

`#![windows_subsystem]` (`main.rs`) is a crate attribute; the only way to
prove it took effect is reading the field it controls straight out of the
built binary's COFF/PE headers. Subsystem `2` = Windows GUI (no console);
`3` = console (the debug-only bug this ticket fixes — see
`T-003-decision-log.md`).

Skips rather than fails when nothing has been built yet — a fresh checkout
has nothing under `target/`.
"""

import glob
import os
import struct

import pytest

DESKTOP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(DESKTOP, "src-tauri", "target")
EXE_NAME = "delivery-console-desktop.exe"

IMAGE_SUBSYSTEM_WINDOWS_GUI = 2
IMAGE_SUBSYSTEM_WINDOWS_CUI = 3


def pe_subsystem(exe_path):
    """The `Subsystem` field of the PE Optional Header.

    Layout: `e_lfanew` (a file offset to the PE signature) sits at DOS-header
    offset 0x3C. From there: 4 bytes of `"PE\\0\\0"` signature, 20 bytes of
    COFF File Header, then 68 bytes into the Optional Header lands on
    `Subsystem` — true for both PE32 and PE32+, since PE32+ drops the 4-byte
    `BaseOfData` field but widens `ImageBase` by exactly 4 bytes, a wash.
    """
    with open(exe_path, "rb") as fh:
        header = fh.read(1024)  # header fields only, never the whole binary
    if header[:2] != b"MZ":
        raise ValueError("%s is not a PE/COFF binary (no MZ signature)" % exe_path)
    e_lfanew = struct.unpack_from("<I", header, 0x3C)[0]
    subsystem_offset = e_lfanew + 4 + 20 + 68
    return struct.unpack_from("<H", header, subsystem_offset)[0]


def built_exes():
    """Top-level profile exes only (`target/debug|release/...exe`) — never
    `target/*/deps/*.exe`, which are test-harness binaries, not the product."""
    pattern = os.path.join(TARGET, "*", EXE_NAME)
    return sorted(glob.glob(pattern))


class TestPeSubsystem:
    def test_every_built_exe_is_the_gui_subsystem(self):
        exes = built_exes()
        if not exes:
            pytest.skip(
                "no built %s under desktop/src-tauri/target — "
                "build first (see desktop/README.md)" % EXE_NAME
            )
        for exe in exes:
            subsystem = pe_subsystem(exe)
            assert subsystem == IMAGE_SUBSYSTEM_WINDOWS_GUI, (
                "%s has PE subsystem %d, expected %d (GUI) — the debug-only "
                "windows_subsystem gate this ticket fixes regressed"
                % (exe, subsystem, IMAGE_SUBSYSTEM_WINDOWS_GUI)
            )

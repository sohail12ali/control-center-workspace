"""Generate the application bundle icons. Stdlib only — run it, commit the PNGs.

    python desktop/icons/gen_app_icons.py

## Why this exists

Tauri validates the bundle icons at COMPILE time and rejects any that are not
RGBA. The placeholders committed with the original shell spike were RGB, which
built fine on Windows and failed the macOS build outright:

    error: proc macro panicked
      = help: message: icon .../icons/32x32.png is not RGBA

That is a good error, badly timed: it only appeared once a macOS runner tried,
which was three tickets after the icons were committed. Generating them here
means the format is a property of the code rather than of whatever tool
happened to export them.

Separate from `gen_tray_icons.py` on purpose: the tray icons carry state and
come in six variants and two renderings, while these are one static mark at
two sizes. Sharing a script would mean one file doing two unrelated jobs.
"""

import math
import os
import struct
import zlib

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "src-tauri", "icons")

#: Sizes referenced by `tauri.conf.json`'s bundle icon list.
SIZES = (32, 128)

#: The mark: a filled disc, the same shape family the tray idle icon uses, so
#: the app and its tray icon read as the same product.
FILL = (0x2F, 0x6F, 0xED)


def _pixels(size):
    """RGBA rows for one icon, anti-aliased at the edge."""
    centre = (size - 1) / 2.0
    radius = size * 0.46
    rows = []
    for y in range(size):
        row = []
        for x in range(size):
            d = math.hypot(x - centre, y - centre)
            if d <= radius - 1:
                row.append((FILL[0], FILL[1], FILL[2], 255))
            elif d <= radius:
                # One pixel of coverage falloff, which is all a disc needs.
                alpha = int(round(255 * (radius - d)))
                row.append((FILL[0], FILL[1], FILL[2], max(0, min(255, alpha))))
            else:
                row.append((0, 0, 0, 0))
        rows.append(row)
    return rows


def _png(rows):
    """Colour type 6 — RGBA. The whole point of this file."""
    size = len(rows)
    raw = b"".join(bytes([0]) + bytes(v for px in row for v in px) for row in rows)

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    return (bytes([0x89]) + b"PNG\r\n" + bytes([0x1A]) + b"\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


def main():
    out = os.path.normpath(OUT_DIR)
    os.makedirs(out, exist_ok=True)
    for size in SIZES:
        path = os.path.join(out, "%dx%d.png" % (size, size))
        blob = _png(_pixels(size))
        with open(path, "wb") as fh:
            fh.write(blob)
        # Read back the header rather than trusting the writer.
        width, height, depth, colour = struct.unpack(">IIBB", blob[16:26])
        assert colour == 6, "colour type %d is not RGBA" % colour
        print("wrote %s  %dx%d depth=%d RGBA  %d bytes"
              % (os.path.basename(path), width, height, depth, len(blob)))


if __name__ == "__main__":
    main()

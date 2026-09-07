"""Generate the tray state icons. Stdlib only — run it, commit the PNGs.

    python desktop/icons/gen_tray_icons.py

## Why generated rather than drawn

The tray needs one icon per assistant state, in two renderings (colour for the
Windows and Linux trays, monochrome "template" for the macOS menu bar), at a
size where a stray pixel is the difference between legible and mush. Six states
times two renderings is twelve near-identical assets, and hand-editing twelve
PNGs in lockstep is how they drift. Here the shapes are code, the palette is
one table, and regenerating is one command.

Committing the output matters as much as generating it: the build must not
depend on Python, and a reviewer should see an icon change as a binary diff on
a reviewable file, not as a script change with invisible consequences.

## Why 32x32, and why shape carries the meaning

Windows asks for a 16px logical icon and picks a 32px asset on a 200% display,
which is the common case now; 32 downsamples to 16 cleanly for these shapes.
Every state is distinguishable by SHAPE alone (disc, ring-with-gap, mic, waves,
slash, plus an overlay dot), not only by colour — because the macOS template
rendering has no colour at all, and because a colour-blind user gets the same
information as anyone else.

No anti-aliasing library either: shapes are sampled on a 4x supersampled grid
and averaged down, which is enough for circles and bars at this size.
"""

import math
import os
import struct
import zlib

SIZE = 32
SS = 4                      # supersampling factor
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "src-tauri", "icons", "tray")

#: (r, g, b) per state. Chosen for contrast against BOTH a light and a dark
#: taskbar, which is why every one is a mid-tone: a pale icon vanishes on
#: light, a dark one vanishes on dark.
PALETTE = {
    "idle": (0x8A, 0x8F, 0x98),        # neutral grey - nothing happening
    "listening": (0xE5, 0x48, 0x4D),   # red - the mic is open, be obvious
    "thinking": (0xF5, 0xA5, 0x24),    # amber - working
    "speaking": (0x30, 0xA4, 0x6C),    # green - talking back
    "muted": (0x8A, 0x8F, 0x98),       # grey, distinguished by the slash
}

OUTLINE = (0x1C, 0x1F, 0x23)           # dark ring so the icon survives a light tray
INK = (0xFF, 0xFF, 0xFF)               # glyphs drawn on top of the fill
APPROVAL = (0xFF, 0x8B, 0x3E)          # the needs-approval overlay dot


# -- tiny raster helpers -----------------------------------------------------

def _blank():
    return [[(0, 0, 0, 0)] * (SIZE * SS) for _ in range(SIZE * SS)]


def _put(buf, x, y, rgb, a=255):
    if 0 <= x < SIZE * SS and 0 <= y < SIZE * SS:
        buf[y][x] = (rgb[0], rgb[1], rgb[2], a)


def _disc(buf, cx, cy, r, rgb):
    for y in range(int(cy - r) - 1, int(cy + r) + 2):
        for x in range(int(cx - r) - 1, int(cx + r) + 2):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                _put(buf, x, y, rgb)


def _ring(buf, cx, cy, r_out, r_in, rgb, gap=None):
    """`gap` is (start_deg, end_deg) measured clockwise from 12 o'clock."""
    for y in range(int(cy - r_out) - 1, int(cy + r_out) + 2):
        for x in range(int(cx - r_out) - 1, int(cx + r_out) + 2):
            d2 = (x - cx) ** 2 + (y - cy) ** 2
            if not (r_in * r_in <= d2 <= r_out * r_out):
                continue
            if gap is not None:
                ang = math.degrees(math.atan2(x - cx, cy - y)) % 360
                lo, hi = gap
                if lo <= ang <= hi:
                    continue
            _put(buf, x, y, rgb)


def _rect(buf, x0, y0, x1, y1, rgb):
    for y in range(int(y0), int(y1) + 1):
        for x in range(int(x0), int(x1) + 1):
            _put(buf, x, y, rgb)


def _capsule(buf, cx, y0, y1, r, rgb):
    """A vertical rounded bar — the mic body."""
    _rect(buf, cx - r, y0, cx + r, y1, rgb)
    _disc(buf, cx, y0, r, rgb)
    _disc(buf, cx, y1, r, rgb)


def _arc(buf, cx, cy, r, width, deg_from, deg_to, rgb):
    """A partial ring, angles clockwise from 12 o'clock — speaker waves."""
    r_out, r_in = r + width / 2.0, r - width / 2.0
    for y in range(int(cy - r_out) - 1, int(cy + r_out) + 2):
        for x in range(int(cx - r_out) - 1, int(cx + r_out) + 2):
            d2 = (x - cx) ** 2 + (y - cy) ** 2
            if not (r_in * r_in <= d2 <= r_out * r_out):
                continue
            ang = math.degrees(math.atan2(x - cx, cy - y)) % 360
            if deg_from <= ang <= deg_to:
                _put(buf, x, y, rgb)


def _line(buf, x0, y0, x1, y1, width, rgb):
    """A thick segment, by distance-to-segment — the muted slash."""
    dx, dy = x1 - x0, y1 - y0
    length2 = dx * dx + dy * dy
    half = width / 2.0
    for y in range(int(min(y0, y1) - width), int(max(y0, y1) + width) + 1):
        for x in range(int(min(x0, x1) - width), int(max(x0, x1) + width) + 1):
            t = 0.0 if length2 == 0 else max(0.0, min(
                1.0, ((x - x0) * dx + (y - y0) * dy) / length2))
            px, py = x0 + t * dx, y0 + t * dy
            if (x - px) ** 2 + (y - py) ** 2 <= half * half:
                _put(buf, x, y, rgb)


def _downsample(buf):
    """Average each SS x SS block — the only anti-aliasing here."""
    out = []
    for y in range(SIZE):
        row = []
        for x in range(SIZE):
            r = g = b = a = 0
            for sy in range(SS):
                for sx in range(SS):
                    pr, pg, pb, pa = buf[y * SS + sy][x * SS + sx]
                    # Premultiply so a transparent pixel does not drag the
                    # colour of its neighbours toward black.
                    r += pr * pa; g += pg * pa; b += pb * pa; a += pa
            n = SS * SS
            if a == 0:
                row.append((0, 0, 0, 0))
            else:
                row.append((r // a, g // a, b // a, a // n))
        out.append(row)
    return out


def _to_template(buf):
    """macOS menu-bar rendering: the system tints the icon, so ONLY the alpha
    channel carries information — a white glyph on a coloured disc would come
    out as a featureless blob, which is exactly the bug this exists to avoid.

    So ink becomes a HOLE and everything else becomes opaque: the mic, the
    speaker waves, the slash and the approval surround all read as cut-outs.
    Converting before downsampling keeps the edges anti-aliased.
    """
    holed = [[(0, 0, 0, 0) if (px[3] == 0 or px[:3] == INK) else (0, 0, 0, 255)
              for px in row] for row in buf]
    return _downsample(holed)


def _png(pixels):
    raw = b"".join(b"\x00" + bytes(v for px in row for v in px)
                   for row in pixels)

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


# -- the states --------------------------------------------------------------

def _base(fill):
    """Every state shares this: a dark outline, the state colour, and a thin
    white inner ring that keeps the glyph readable on any taskbar."""
    buf = _blank()
    cx = cy = (SIZE * SS) / 2.0
    r = 14.0 * SS
    _disc(buf, cx, cy, r, OUTLINE)
    _disc(buf, cx, cy, r - 1.2 * SS, fill)
    return buf, cx, cy, r


def draw(state, approval=False, template=False):
    fill = PALETTE[state]
    buf, cx, cy, r = _base(fill)

    if state == "listening":
        # Mic: capsule body, stem, base bar.
        _capsule(buf, cx, cy - 5.0 * SS, cy - 0.5 * SS, 2.6 * SS, INK)
        _rect(buf, cx - 0.9 * SS, cy - 0.5 * SS, cx + 0.9 * SS, cy + 4.0 * SS, INK)
        _rect(buf, cx - 4.0 * SS, cy + 4.0 * SS, cx + 4.0 * SS, cy + 5.6 * SS, INK)

    elif state == "thinking":
        # A ring with a gap at 12 o'clock reads as "in progress" even in a
        # still frame. The CENTRE is ink, i.e. a hole in the template
        # rendering — without it the disc behind the ring stays opaque and
        # this state comes out identical to idle on the macOS menu bar.
        _ring(buf, cx, cy, r - 1.2 * SS, r - 5.2 * SS, PALETTE["thinking"],
              gap=(345, 360))
        _ring(buf, cx, cy, r - 1.2 * SS, r - 5.2 * SS, PALETTE["thinking"],
              gap=(0, 15))
        _disc(buf, cx, cy, r - 5.2 * SS, INK)

    elif state == "speaking":
        # Speaker: a small cone plus two waves.
        _rect(buf, cx - 5.5 * SS, cy - 2.2 * SS, cx - 2.5 * SS, cy + 2.2 * SS, INK)
        _line(buf, cx - 2.5 * SS, cy - 5.2 * SS, cx - 2.5 * SS, cy + 5.2 * SS,
              2.0 * SS, INK)
        _arc(buf, cx - 2.0 * SS, cy, 5.0 * SS, 1.6 * SS, 60, 120, INK)
        _arc(buf, cx - 2.0 * SS, cy, 8.0 * SS, 1.6 * SS, 65, 115, INK)

    elif state == "muted":
        _capsule(buf, cx, cy - 5.0 * SS, cy - 0.5 * SS, 2.6 * SS, INK)
        _rect(buf, cx - 0.9 * SS, cy - 0.5 * SS, cx + 0.9 * SS, cy + 4.0 * SS, INK)
        _rect(buf, cx - 4.0 * SS, cy + 4.0 * SS, cx + 4.0 * SS, cy + 5.6 * SS, INK)
        # The slash gets a dark backing line so it stays visible over white ink.
        _line(buf, cx - 8.0 * SS, cy - 8.0 * SS, cx + 8.0 * SS, cy + 8.0 * SS,
              4.2 * SS, OUTLINE)
        _line(buf, cx - 8.0 * SS, cy - 8.0 * SS, cx + 8.0 * SS, cy + 8.0 * SS,
              2.2 * SS, INK)

    if approval:
        # Bottom-right dot. Deliberately an OVERLAY on whatever state is
        # current, because "needs approval" happens *during* another state and
        # replacing the icon would hide what the assistant is doing.
        dx, dy, dr = cx + 8.5 * SS, cy + 8.5 * SS, 5.2 * SS
        # The surround is INK, not OUTLINE, on purpose: ink becomes a hole in
        # the template rendering, so the badge stays a distinct shape on the
        # macOS menu bar instead of merging into the disc behind it.
        _disc(buf, dx, dy, dr, INK)
        _disc(buf, dx, dy, dr - 1.6 * SS, APPROVAL)

    return _to_template(buf) if template else _downsample(buf)


def main():
    out = os.path.normpath(OUT_DIR)
    os.makedirs(out, exist_ok=True)
    written = []
    for state in ("idle", "listening", "thinking", "speaking", "muted"):
        for approval in (False, True):
            for template in (False, True):
                name = state
                if approval:
                    name += "-approval"
                if template:
                    name += "-template"
                path = os.path.join(out, name + ".png")
                with open(path, "wb") as fh:
                    fh.write(_png(draw(state, approval, template)))
                written.append(os.path.basename(path))
    print("wrote %d icons to %s" % (len(written), out))
    for name in written:
        print("  " + name)


if __name__ == "__main__":
    main()

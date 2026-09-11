"""Generate the application bundle icons from the source artwork. Stdlib only.

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
several sizes. Sharing a script would mean one file doing two unrelated jobs.

## The mark

`source/app-icon-512.png` — a blue four-point sparkle with a smaller purple
one, chosen by the owner of this workspace. Earlier revisions of this file DREW
the mark in code; that made sense while the mark was geometry nobody had picked
yet, and stopped making sense the moment there was real artwork. The drawing
code is gone rather than kept commented out: the source PNG is the mark now,
and a second, divergent definition of it would be a lie waiting to be read.

PROVENANCE: downloaded from https://img.icons8.com/color/512/bard--v2.png
(Icons8). Icons8's free tier requires attribution; if this ships without a paid
licence, that attribution is owed somewhere visible. Replacing the mark means
replacing that one file — nothing else here knows what it looks like.

## Why it is not blurry

Three causes of soft icons, all of them handled here:

  * ONE FRAME. The .ico used to ship a single 32px frame, so Windows upscaled
    it for 48px list views and 256px extra-large ones. Every size Windows asks
    for is now resampled from the 512px source at that exact size.
  * NAIVE RESAMPLING. Picking nearest pixels out of a 512px source throws away
    31 of every 32 and turns a smooth curve into a staircase. `_resample`
    averages every source pixel that falls under a destination pixel,
    weighting the partial ones at the edges by how much of them is covered.
  * STRAIGHT-ALPHA AVERAGING. Averaging colour without weighting by alpha
    drags edge pixels toward whatever the transparent pixels happen to carry —
    usually black, giving a dark halo. Everything here is averaged
    PREMULTIPLIED and un-premultiplied at the end.

## What it writes

`32x32.png` and `128x128.png` (the sizes `tauri.conf.json` lists) plus
`icon.ico` packing 16/20/24/32/40/48/64/256 as PNG-in-ICO, which every Windows
since Vista reads. That list is not padding: 20 and 40 are what a 125% display
asks for, 24 is the Alt-Tab and jump-list size, 64 the medium-icon view. Also
`console/static/icon-{16,32,64}.png`, so the web console's favicon is the same
asset rather than a second drawing that drifts.
"""

import os
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, "source", "app-icon-512.png")
OUT_DIR = os.path.normpath(os.path.join(HERE, "..", "src-tauri", "icons"))
WEB_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "console", "static"))

#: Sizes referenced by `tauri.conf.json`'s bundle icon list.
PNG_SIZES = (32, 128)

#: Frames packed into `icon.ico` — every size Windows asks for, resampled from
#: the source at that size rather than scaled from a neighbour.
#:
#: LARGEST FIRST, and that order is load-bearing. Windows itself picks the
#: best-fit frame and does not care, but `tauri-codegen` builds the app's
#: default window icon with `icon_dir.entries()[0]` — the FIRST frame, whatever
#: it is. Smallest-first put a 16x16 image in the taskbar and the tray, where
#: Windows then blew it up to 48 and 32: the icon looked soft precisely
#: BECAUSE the .ico had gained small frames. Sorted here rather than at the
#: call site so there is one place to state it.
ICO_SIZES = (256, 64, 48, 40, 32, 24, 20, 16)

#: The favicon, at the three sizes a browser tab actually picks from.
WEB_SIZES = (16, 32, 64)

#: Transparent border left around the mark, as a fraction of the icon's side.
#: The artwork arrives with its own padding, which is trimmed first, so this is
#: the ONLY margin — otherwise the mark renders small and timid in a taskbar
#: full of icons that fill their box.
MARGIN = 0.04


# -- PNG in ---------------------------------------------------------------

def _read_png(path):
    """Decode a non-interlaced 8-bit RGBA PNG to rows of (r, g, b, a).

    Deliberately narrow: it asserts the format it wants rather than growing a
    decoder for palettes, 16-bit samples and Adam7. The source file is
    committed next to this script, so "what format is it" has one answer, and
    an assert is a better failure than a subtly wrong icon.
    """
    with open(path, "rb") as fh:
        blob = fh.read()
    assert blob[:8] == bytes([0x89]) + b"PNG\r\n" + bytes([0x1A]) + b"\n", "not a PNG"

    width = height = None
    data = b""
    i = 8
    while i < len(blob):
        length = struct.unpack(">I", blob[i:i + 4])[0]
        tag = blob[i + 4:i + 8]
        payload = blob[i + 8:i + 8 + length]
        if tag == b"IHDR":
            width, height, depth, colour, _comp, _filt, interlace = \
                struct.unpack(">IIBBBBB", payload)
            assert depth == 8, "need 8-bit samples, got %d" % depth
            assert colour == 6, "need RGBA (colour type 6), got %d" % colour
            assert interlace == 0, "interlaced PNGs are not supported"
        elif tag == b"IDAT":
            data += payload
        elif tag == b"IEND":
            break
        i += 12 + length

    raw = zlib.decompress(data)
    stride = width * 4
    rows, prev = [], bytearray(stride)
    pos = 0
    for _ in range(height):
        filter_type = raw[pos]
        line = bytearray(raw[pos + 1:pos + 1 + stride])
        pos += 1 + stride
        # The PNG filters, per the spec: `a` is the pixel to the left, `b` the
        # one above, `c` above-left; all zero off the edges of the image.
        for x in range(stride):
            a = line[x - 4] if x >= 4 else 0
            b = prev[x]
            c = prev[x - 4] if x >= 4 else 0
            if filter_type == 0:
                pass
            elif filter_type == 1:
                line[x] = (line[x] + a) & 0xFF
            elif filter_type == 2:
                line[x] = (line[x] + b) & 0xFF
            elif filter_type == 3:
                line[x] = (line[x] + (a + b) // 2) & 0xFF
            elif filter_type == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[x] = (line[x] + pr) & 0xFF
            else:
                raise AssertionError("unknown PNG filter %d" % filter_type)
        rows.append([tuple(line[x:x + 4]) for x in range(0, stride, 4)])
        prev = line
    return rows


# -- geometry -------------------------------------------------------------

def _alpha_bbox(rows):
    """The box holding every pixel that is not fully transparent."""
    x0, y0 = len(rows[0]), len(rows)
    x1 = y1 = -1
    for y, row in enumerate(rows):
        for x, px in enumerate(row):
            if px[3]:
                if x < x0: x0 = x
                if x > x1: x1 = x
                if y < y0: y0 = y
                if y > y1: y1 = y
    assert x1 >= 0, "the source is entirely transparent"
    return x0, y0, x1 + 1, y1 + 1


def _square(rows, box):
    """Crop to `box`, then pad back out to a SQUARE around the same centre.

    Square because an icon is square, and letting the resampler squash a
    non-square crop into one would distort the mark. Padding rather than
    cropping further, because trimming the point off a sparkle is worse than a
    few transparent pixels.
    """
    x0, y0, x1, y1 = box
    side = max(x1 - x0, y1 - y0)
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    sx, sy = int(round(cx - side / 2.0)), int(round(cy - side / 2.0))

    out = []
    for y in range(sy, sy + side):
        row = []
        for x in range(sx, sx + side):
            inside = 0 <= y < len(rows) and 0 <= x < len(rows[0])
            row.append(rows[y][x] if inside else (0, 0, 0, 0))
        out.append(row)
    return out


def _resample(rows, size):
    """Area-average `rows` down to size x size, in premultiplied alpha.

    Every destination pixel covers a rectangle of source pixels, and each
    source pixel contributes in proportion to how much of it falls inside.
    That is what makes a 512 -> 16 reduction look like the artwork instead of
    like 256 pixels picked out of 262144.
    """
    src = len(rows)
    scale = src / float(size)
    out = []
    for dy in range(size):
        sy0, sy1 = dy * scale, (dy + 1) * scale
        row = []
        for dx in range(size):
            sx0, sx1 = dx * scale, (dx + 1) * scale
            r = g = b = a = area = 0.0
            for y in range(int(sy0), min(int(sy1 - 1e-9) + 1, src)):
                wy = min(sy1, y + 1) - max(sy0, y)
                if wy <= 0:
                    continue
                for x in range(int(sx0), min(int(sx1 - 1e-9) + 1, src)):
                    wx = min(sx1, x + 1) - max(sx0, x)
                    if wx <= 0:
                        continue
                    w = wx * wy
                    pr, pg, pb, pa = rows[y][x]
                    f = pa / 255.0
                    # Premultiplied: a transparent pixel adds NO colour.
                    r += pr * f * w
                    g += pg * f * w
                    b += pb * f * w
                    a += pa * w
                    area += w
            if area <= 0 or a <= 0:
                row.append((0, 0, 0, 0))
                continue
            alpha = a / area
            f = alpha / 255.0
            row.append((
                max(0, min(255, int(round(r / area / f)))),
                max(0, min(255, int(round(g / area / f)))),
                max(0, min(255, int(round(b / area / f)))),
                max(0, min(255, int(round(alpha)))),
            ))
        out.append(row)
    return out


def _pad(rows, size):
    """Centre the mark in a size x size canvas with MARGIN around it."""
    inner = max(1, size - 2 * int(round(size * MARGIN)))
    if inner >= size:
        return _resample(rows, size)
    art = _resample(rows, inner)
    off = (size - inner) // 2
    out = [[(0, 0, 0, 0)] * size for _ in range(size)]
    for y in range(inner):
        for x in range(inner):
            out[off + y][off + x] = art[y][x]
    return out


# -- PNG out --------------------------------------------------------------

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


def _ico(frames):
    """Pack (size, png_bytes) pairs into an .ico directory.

    PNG frames, not BMP: a 256px BMP frame would be a quarter-megabyte of
    bottom-up rows plus an AND mask, and Windows has read PNG frames since
    Vista. 256 is written as 0 in the directory, which is how the format says
    "256" in one byte.
    """
    header = struct.pack("<HHH", 0, 1, len(frames))
    offset = len(header) + 16 * len(frames)
    entries, blobs = b"", b""
    for size, blob in frames:
        entries += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0,
                               1, 32, len(blob), offset)
        blobs += blob
        offset += len(blob)
    return header + entries + blobs


def _write(path, blob, note):
    with open(path, "wb") as fh:
        fh.write(blob)
    print("wrote %-16s %s  %d bytes" % (os.path.basename(path), note, len(blob)))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    src = _read_png(SOURCE)
    box = _alpha_bbox(src)
    print("source %dx%d, ink in %s, squared and re-padded at %d%%"
          % (len(src[0]), len(src), box, round(MARGIN * 100)))
    art = _square(src, box)

    cache = {}

    def png(size):
        if size not in cache:
            blob = _png(_pad(art, size))
            # Read back the header rather than trusting the writer.
            width, height, depth, colour = struct.unpack(">IIBB", blob[16:26])
            assert colour == 6, "colour type %d is not RGBA" % colour
            assert width == height == size and depth == 8
            cache[size] = blob
        return cache[size]

    for size in PNG_SIZES:
        _write(os.path.join(OUT_DIR, "%dx%d.png" % (size, size)), png(size),
               "%dx%d RGBA" % (size, size))

    _write(os.path.join(OUT_DIR, "icon.ico"),
           _ico([(s, png(s)) for s in ICO_SIZES]),
           "frames " + "/".join(str(s) for s in ICO_SIZES))

    for size in WEB_SIZES:
        _write(os.path.join(WEB_DIR, "icon-%d.png" % size), png(size),
               "%dx%d RGBA (console favicon)" % (size, size))


if __name__ == "__main__":
    main()

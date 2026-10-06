#!/usr/bin/env python3
"""Regenerate the headless-replay fixtures in desktop/tests/fixtures/ (T-032).

SYNTHETIC SPEECH, NOT A HUMAN VOICE. Every spoken fixture is Piper
(desktop/tts/piper.exe, voice en_US-amy-medium) text-to-speech, joined with
digitally generated silence and seeded low-level noise. Nothing is recorded
from a microphone, and nothing here says anything about how a real person
pauses. What the fixtures are good for is exact, repeatable timing: a pause
that is 0.9 s long is 0.9 s long every run.

Run from anywhere:  python desktop/tests/gen_replay_fixtures.py
Check reproducibility:  python desktop/tests/gen_replay_fixtures.py --check

Only the standard library is used. Output is 16 kHz mono 16-bit PCM, the format
`audio::Take::wav` and the recogniser use. Piper is run with noise_scale and
noise_w at 0 so the same text gives the same samples.
"""
import hashlib
import random
import struct
import subprocess
import sys
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
FIXTURES = HERE / "fixtures"
PIPER = REPO / "desktop" / "tts" / ("piper.exe" if sys.platform == "win32" else "piper")
VOICE = REPO / "desktop" / "tts" / "en_US-amy-medium.onnx"
HZ = 16_000
PIPER_HZ = 22_050  # en_US-amy-medium, from its .onnx.json
PAD_MS = 500  # quiet before the first word, so the endpointer calibrates on a room
TRIM_THRESHOLD = 400  # Piper clips carry their own silent edges; cut them off


def ms(n):
    return HZ * n // 1000


def room(n, seed, amplitude=6):
    """n samples of very faint noise, seeded: a quiet room, not digital zero."""
    rng = random.Random(seed)
    return [rng.randint(-amplitude, amplitude) for _ in range(n)]


def speak(text):
    """Piper's 22.05 kHz raw output for `text`, resampled to 16 kHz, edges trimmed."""
    out = subprocess.run(
        [str(PIPER), "--model", str(VOICE), "--output_raw",
         "--noise_scale", "0", "--noise_w", "0"],
        input=(text + "\n").encode(), capture_output=True, cwd=PIPER.parent, check=True,
    ).stdout
    src = list(struct.unpack("<%dh" % (len(out) // 2), out))
    ratio = HZ / PIPER_HZ
    n = round(len(src) * ratio)
    pcm = []
    for i in range(n):  # linear interpolation, as audio.rs does
        pos = i / ratio
        left = int(pos)
        frac = pos - left
        a = src[left] if left < len(src) else 0
        b = src[left + 1] if left + 1 < len(src) else a
        pcm.append(int(a + (b - a) * frac))
    loud = [i for i, s in enumerate(pcm) if abs(s) > TRIM_THRESHOLD]
    return pcm[loud[0]: loud[-1] + 1] if loud else pcm


def click(seed):
    """A 3 ms transient: loud, but far shorter than any syllable."""
    rng = random.Random(seed)
    n = ms(3)
    return [int(rng.uniform(-1, 1) * 26_000 * (1 - i / n)) for i in range(n)]


def assemble(parts, seed):
    """parts: ('say', text) | ('gap', ms) | ('click',) | ('pcm', samples).
    Gaps are faint seeded noise. PAD_MS of room before and after."""
    pcm = room(ms(PAD_MS), seed)
    for i, part in enumerate(parts):
        kind = part[0]
        if kind == "say":
            pcm += speak(part[1])
        elif kind == "gap":
            pcm += room(ms(part[1]), seed + 1 + i)
        elif kind == "click":
            pcm += click(seed + 100 + i)
        elif kind == "pcm":
            pcm += part[1]
    return pcm + room(ms(PAD_MS), seed + 99)


def noise(n, seed, amplitude):
    rng = random.Random(seed)
    return [rng.randint(-amplitude, amplitude) for _ in range(n)]


FIXTURE_SPECS = {
    # (a) one sentence, one 0.9 s pause in the middle of it
    "replay-a-mid-pause.wav": lambda: assemble(
        [("say", "Show me the open tickets"), ("gap", 900), ("say", "and which ones are blocked")], 1),
    # (b) two sentences, a 3 s gap between them
    "replay-b-gap-3s.wav": lambda: assemble(
        [("say", "Show me the open tickets."), ("gap", 3000), ("say", "Which ones are blocked?")], 2),
    # (c) one sentence with five 0.9 s pauses
    "replay-c-five-pauses.wav": lambda: assemble(
        [("say", "Show me"), ("gap", 900), ("say", "the open tickets"), ("gap", 900),
         ("say", "that are"), ("gap", 900), ("say", "blocked or waiting"), ("gap", 900),
         ("say", "on someone"), ("gap", 900), ("say", "right now")], 3),
    # (d) silence only: digital zero
    "replay-d-silence.wav": lambda: [0] * ms(3000),
    # (e) low noise only: about -40 dBFS, steady, no speech
    "replay-e-low-noise.wav": lambda: noise(ms(3000), 5, 300),
    # (f) a sentence, then three short clicks inside the merge window after it
    "replay-f-clicks-in-window.wav": lambda: assemble(
        [("say", "Show me the open tickets"), ("gap", 250), ("click",), ("gap", 250),
         ("click",), ("gap", 250), ("click",)], 6),
    # (g) non-speech that real base.en turns into text. Found by search (see
    # README-replay.md): 10 s of digital silence -> "you" (a FR-15 list entry);
    # 8 s of steady noise -> a bracketed sound tag such as "(clippers whirring)".
    "replay-g-silence-hallucination.wav": lambda: [0] * ms(10_000),
    "replay-g2-noise-sound-tag.wav": lambda: noise(ms(8000), 7, 300),
}


def wav_bytes(pcm):
    import io
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(HZ)
        w.writeframes(struct.pack("<%dh" % len(pcm), *[max(-32768, min(32767, s)) for s in pcm]))
    return buf.getvalue()


def build():
    return {name: wav_bytes(make()) for name, make in FIXTURE_SPECS.items()}


def main():
    for tool in (PIPER, VOICE):
        if not tool.is_file():
            sys.exit(f"missing {tool}: run desktop/get-piper.ps1 first")
    built = build()
    if "--check" in sys.argv:
        again = build()
        same = all(built[n] == again[n] for n in built)
        for n in built:
            print(("same     " if built[n] == again[n] else "DIFFERENT"),
                  n, hashlib.sha256(built[n]).hexdigest()[:16])
        sys.exit(0 if same else 1)
    FIXTURES.mkdir(exist_ok=True)
    for name, data in built.items():
        (FIXTURES / name).write_bytes(data)
        print(f"wrote {name}: {len(data)} bytes, {(len(data) - 44) / 2 / HZ:.2f} s, "
              f"sha256 {hashlib.sha256(data).hexdigest()[:16]}")


if __name__ == "__main__":
    main()

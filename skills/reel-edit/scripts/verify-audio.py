#!/usr/bin/env python3
"""Subtract the source voice out of a render to isolate music and sound effects.

Usage:
    python3 verify-audio.py source.mp4 render.mp4 [cueFrame:label ...]

Reports the voice gain (should be ~1.0), the isolated bed level, and the peak of
each named cue relative to the bed. Requires ffmpeg on PATH and numpy.
"""
import subprocess, sys, tempfile, os, wave
import numpy as np

FPS = 30


def read(path):
    wav = os.path.join(tempfile.mkdtemp(), "a.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path,
                    "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", wav], check=True)
    w = wave.open(wav)
    return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float) / 32768


def db(x):
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    src, ren = read(sys.argv[1]), read(sys.argv[2])

    # the encoder prepends a delay; find it by correlating the first 3 seconds
    best = None
    for d in range(0, 4100):
        a, b = src[:48000 * 3], ren[d:d + 48000 * 3]
        if len(b) < len(a):
            break
        c = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9)
        if best is None or c > best[1]:
            best = (d, c)
    delay = best[0]

    n = min(len(src), len(ren) - delay)
    a, b = src[:n], ren[delay:delay + n]
    k = np.dot(a, b) / np.dot(a, a)
    res = b - k * a

    print(f"encoder delay {delay} samples")
    print(f"voice gain    {k:.4f}   (1.0 means the voice passed through untouched)")
    print(f"voice         {db(a):6.1f} dB")
    print(f"added audio   {db(res):6.1f} dB   separation {db(a) - db(res):.1f} dB")

    hop = 48000 // FPS
    env = np.array([np.max(np.abs(res[i:i + hop])) for i in range(0, len(res) - hop, hop)])
    edb = 20 * np.log10(env + 1e-9)
    base = float(np.median(edb))
    print(f"bed peak median {base:.1f} dB")

    for arg in sys.argv[3:]:
        frame, _, label = arg.partition(":")
        f = int(frame)
        w = edb[max(0, f - 4):f + 14]
        if len(w) == 0:
            continue
        print(f"  f{f:<6d} {label or '':16s} peak {w.max():6.1f} dB  "
              f"+{w.max() - base:5.1f} over bed  at f{f - 4 + int(np.argmax(w))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

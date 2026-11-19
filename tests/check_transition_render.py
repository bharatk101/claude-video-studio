#!/usr/bin/env python3
"""Checks the CI transition renders (see ci.yml): a red clip with a 440 Hz tone joined at frame 60 to a blue clip
with an 880 Hz tone, with a 10-frame fade.

    python3 check_transition_render.py out/t-hold.mp4 out/t-overlap.mp4

hold:    120 frames; red to f60, the fade runs f60-f69 over the held red frame, blue from f70; the tone switches
         at exactly 2.00 s (the sound is never overlapped).
overlap: 110 frames; the fade runs f50-f59, blue from f60; both tones play while the sound crossfades.
"""
import subprocess, sys

import numpy as np


def frames(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", "scale=27:48", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    f = np.frombuffer(raw, np.uint8).reshape(-1, 48, 27, 3)[:, 10:38, 5:22]   # centre, clear of hook and captions
    return f.reshape(len(f), -1, 3).mean(1)


def tones(path, t0, t1):
    x = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "48000", "-f", "s16le", "-"],
                                     capture_output=True, check=True).stdout, np.int16).astype(float)
    s = x[int(t0 * 48000):int(t1 * 48000)]
    sp, f = np.abs(np.fft.rfft(s)), np.fft.rfftfreq(len(s), 1 / 48000)
    return sp[(f > 420) & (f < 460)].max(), sp[(f > 860) & (f < 900)].max()


def red(c): return c[0] > 200 and c[2] < 60
def blue(c): return c[2] > 200 and c[0] < 60
def mixed(c): return 60 < c[0] < 200 and 60 < c[2] < 200


hold, overlap = sys.argv[1], sys.argv[2]
h, o = frames(hold), frames(overlap)
assert len(h) == 120, f"hold: {len(h)} frames, expected 120"
assert len(o) == 110, f"overlap: {len(o)} frames, expected 110"
assert all(red(h[i]) for i in range(0, 61)) and mixed(h[65]) and all(blue(h[i]) for i in range(70, 120)), h[55:72].astype(int)
assert all(red(o[i]) for i in range(0, 51)) and mixed(o[55]) and all(blue(o[i]) for i in range(60, 110)), o[45:62].astype(int)
a, b = tones(hold, 1.70, 1.95)
assert a > 20 * max(b, 1), f"hold before the join: 440 {a:.0f} vs 880 {b:.0f}"
a, b = tones(hold, 2.05, 2.30)
assert b > 20 * max(a, 1), f"hold after the join: 440 {a:.0f} vs 880 {b:.0f}"
a, b = tones(overlap, 1.70, 1.95)
assert a > 0.2 * b and b > 0.2 * a, f"overlap should crossfade: 440 {a:.0f} vs 880 {b:.0f}"
print("transition renders ok: hold 120 frames, fade f60-f69, sound switches at 2.00 s; overlap 110 frames, fade f50-f59, crossfade")

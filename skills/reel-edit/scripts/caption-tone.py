#!/usr/bin/env python3
"""Measure the ground behind a caption band, per frame.

Render the segment WITHOUT captions as a quarter-scale sequence, e.g.

    npx remotion render src/index.ts <Comp> "$TMPDIR/tone" --sequence \
      --frames=A-B --scale=0.25 --props='{"noCaptions":true}'

then:

    python3 caption-tone.py "$TMPDIR/tone" <compDurationFrames> public/<video>/caption-tone.json [y0 y1 [x0 x1]]

It writes a JSON array, one mean luminance (0-255) per composition frame for
the band y0-y1 (default y1055-1150, the two-thirds caption band; for other
captions pass the measured caption line box, plus x0 x1 to skip the frame's
edges) on the 1080x1920 frame, null where no frame was rendered. Above 140 is
a light ground: use the outlined caption there (components/Caption.tsx, or
the brand sheet's light-ground treatment; `isLight` in
components/TwoThirdsPanel.tsx). Average it per caption chunk.
"""
import json
import os
import re
import sys

import numpy as np
from PIL import Image

src, dur, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
y0, y1 = (int(sys.argv[4]), int(sys.argv[5])) if len(sys.argv) > 5 else (1055, 1150)
x0, x1 = (int(sys.argv[6]), int(sys.argv[7])) if len(sys.argv) > 7 else (0, 1080)
lum = [None] * dur
for fn in os.listdir(src):
    m = re.search(r"(\d+)\.(jpe?g|png)$", fn)
    if not m:
        continue
    f = int(m.group(1))
    a = np.array(Image.open(os.path.join(src, fn)).convert("L")).astype(float)
    k = a.shape[0] / 1920
    lum[f] = round(float(a[int(y0 * k): int(y1 * k), int(x0 * k): int(x1 * k)].mean()), 1)
vals = [v for v in lum if v is not None]
os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
json.dump(lum, open(out, "w"))
print(f"{len(vals)} frames, luminance {min(vals)}-{max(vals)} -> {out}")

#!/usr/bin/env python3
"""Read each line's box width off a TextHook "measure" still.

Render one frame with <TextHook variant="measure" .../> (each line drawn as
its own white box on black), then:

    python3 measure-hook.py still.png <top> <lines> [lineHeight=105]

It prints the widths to paste into TextHook's `widths` prop.
"""
import sys
import numpy as np
from PIL import Image

img, top, n = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
lh = int(sys.argv[4]) if len(sys.argv) > 4 else 105
a = np.array(Image.open(img).convert("L")).astype(int)
widths = []
for i in range(n):
    band = a[top + i * lh + 4: top + (i + 1) * lh - 4]
    cols = np.where((band > 200).sum(0) > band.shape[0] * 0.5)[0]
    widths.append(int(cols.max() - cols.min() + 1))
print("widths:", widths)

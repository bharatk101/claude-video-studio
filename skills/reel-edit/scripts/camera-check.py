#!/usr/bin/env python3
"""Replay a screen-recording camera path and report the worst per-frame motion.

Run it before you render. It catches two things: a clamp that snaps the
framing, and a pan that is simply too fast to read.

    python3 camera-check.py --src 3024x1898 --keys "0:1450:1388:800 40:1430:1388:1120 140:1220:2385:1040"
    python3 camera-check.py --src 3024x1898 --keys-json src/MyVideo/camera.json    # [{"f","w","cx","cy"}, ...]
    options: --frame 1080x1920 (the pane, default full frame)  --bleed 400  --ease cubic|sin

Keys are (frame, windowWidth, centreX, centreY) in SOURCE pixels, the same keys
the composition's camAt() uses. Exit code 1 when the pan is over the limit.

A lateral pan over fine UI text reads as smooth at under about 25 output px per
frame. Anything over 50 will be called out as a jump.
"""
FRAME_W, FRAME_H = 1080, 1920
SRC_W, SRC_H = 3024, 1898
MAX_BLEED = 400

# (frame, windowWidth, centreX, centreY) in SOURCE pixels
KEYS = [
    (0, 1450, 1388, 800),
    (40, 1430, 1388, 1120),
    (140, 1220, 2385, 1040),
]


EASE = "cubic"


def ease_in_out_sin(t):
    import math
    return -(math.cos(math.pi * t) - 1) / 2


def ease_in_out_cubic(t):
    return 4 * t * t * t if t < 0.5 else 1 - ((-2 * t + 2) ** 3) / 2


def cam_at(keys, f):
    if f <= keys[0][0]:
        return keys[0][1:]
    if f >= keys[-1][0]:
        return keys[-1][1:]
    for i in range(len(keys) - 1):
        if keys[i][0] <= f <= keys[i + 1][0]:
            a, b = keys[i], keys[i + 1]
            break
    k = (f - a[0]) / (b[0] - a[0])
    t = ease_in_out_sin(k) if EASE == "sin" else ease_in_out_cubic(k)
    return [a[j] + (b[j] - a[j]) * t for j in (1, 2, 3)]


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def parse_args():
    import argparse, json
    global FRAME_W, FRAME_H, SRC_W, SRC_H, MAX_BLEED, KEYS, EASE
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", help="source size WxH (default 3024x1898)")
    ap.add_argument("--frame", help="pane size WxH (default 1080x1920)")
    ap.add_argument("--bleed", type=float, help="MAX_BLEED in source px (default 400)")
    ap.add_argument("--keys", help='"f:w:cx:cy f:w:cx:cy ..."')
    ap.add_argument("--keys-json", help='JSON file: [{"f":0,"w":1450,"cx":1388,"cy":800}, ...]')
    ap.add_argument("--ease", choices=["cubic", "sin"], default="cubic")
    ap.add_argument("--limit", type=float, default=25, help="max lateral pan, output px/frame")
    a = ap.parse_args()
    if a.src: SRC_W, SRC_H = map(int, a.src.lower().split("x"))
    if a.frame: FRAME_W, FRAME_H = map(int, a.frame.lower().split("x"))
    if a.bleed is not None: MAX_BLEED = a.bleed
    if a.keys: KEYS = [tuple(float(v) for v in k.split(":")) for k in a.keys.split()]
    if a.keys_json: KEYS = [(k["f"], k["w"], k["cx"], k["cy"]) for k in json.load(open(a.keys_json))]
    EASE = a.ease
    return a.limit


def main():
    limit = parse_args()
    last = int(KEYS[-1][0])
    prev = None
    worst_corner = worst_corner_f = 0
    worst_pan = worst_pan_f = 0
    for f in range(last + 1):
        w, cx, cy = cam_at(KEYS, f)
        wh = w * FRAME_H / FRAME_W
        cxc = clamp(cx, w / 2, SRC_W - w / 2)
        cyc = clamp(cy, wh / 2 - MAX_BLEED, SRC_H - wh / 2 + MAX_BLEED)
        k = FRAME_W / w
        corners = [(FRAME_W / 2 - cxc * k, FRAME_H / 2 - cyc * k),
                   (FRAME_W / 2 + (SRC_W - cxc) * k, FRAME_H / 2 + (SRC_H - cyc) * k)]
        if prev:
            d = max(((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** 0.5
                    for p, q in zip(corners, prev[0]))
            if d > worst_corner:
                worst_corner, worst_corner_f = d, f
            pan = abs(cxc - prev[1]) * k
            if pan > worst_pan:
                worst_pan, worst_pan_f = pan, f
        prev = (corners, cxc)

    print(f"worst corner motion  {worst_corner:6.1f} output px/frame  at f{worst_corner_f}")
    print(f"worst lateral pan    {worst_pan:6.1f} output px/frame  at f{worst_pan_f}")
    if worst_pan > limit:
        print("  pan is fast; lengthen the move, reduce the zoom change, or try --ease sin")
    crossing = [f for f in range(last + 1)
                if abs(cam_at(KEYS, f)[0] * FRAME_H / FRAME_W - SRC_H) < 30]
    if crossing:
        print(f"  note: the window height passes through the source height near f{crossing[0]}; "
              "confirm the clamp allows bleed, or a hard clamp will snap here")


    return 1 if worst_pan > limit else 0


if __name__ == "__main__":
    raise SystemExit(main())

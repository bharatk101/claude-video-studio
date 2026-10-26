#!/usr/bin/env python3
"""Measure the speaker's framing per shot: head top, eye line, mouth, chin and centre, as min-max ranges.

    python3 measure-framing.py public/recordings/take.mp4                    uses take.cuts.json if it exists
    python3 measure-framing.py take.mp4 --cuts take.cuts.json --samples 10 --out-dir "$TMPDIR/take"

Writes <take>.framing.json:
  {"shots": [{"from", "to", "detected": "9/10", "face": [x, y, w, h], "headTop": [min, max],
              "eyeLine": [min, max], "mouth": [min, max], "chin": [min, max], "centreX": [min, max],
              "methods": {...}}],
   "suggest": {"captionBaseline", "hookTop", "notes": [...]}, "warnings": [...]}
and <out-dir>/framing-<shot>.png: a mid-shot frame with every measured line drawn on it, the suggested caption
baseline (green) and hook box (blue), and the Instagram 4:5 band. LOOK AT THESE before using the numbers.

Measured, offline, no model download: OpenCV's bundled detectors (pip install "opencv-python-headless<5" numpy).
Face and eyes are detected; the head top is found by scanning up from the face until the background starts;
mouth and chin come from the face box. A handheld mic's windscreen is NOT detected: read it off the grid sheet
from detect-cuts.py, because the caption usually sits on its fuzzy top (references/captions.md).
"""
import argparse, json, os, subprocess, sys

try:
    import cv2
    import numpy as np
except ImportError:
    sys.exit('needs OpenCV and numpy: pip3 install "opencv-python-headless<5" numpy  (or: bash run.sh setup)')

W, H = 1080, 1920
IG_TOP, IG_BOTTOM = 285, 1635
HOOK_LINE_H = 105


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
                          "stream=width,height,r_frame_rate,nb_read_frames", "-of", "json", path],
                         capture_output=True, text=True, check=True).stdout
    s = json.loads(out)["streams"][0]
    n, d = (int(x) for x in s["r_frame_rate"].split("/"))
    return s["width"], s["height"], n / d, int(s["nb_read_frames"])


def frame_at(path, f, fps, w, h):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{f / fps:.4f}", "-i", path, "-frames:v", "1",
                          "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    if len(raw) < w * h * 3:
        return None
    return np.frombuffer(raw[: w * h * 3], np.uint8).reshape(h, w, 3)


CASC = {}


def cascade(name):
    if name not in CASC:
        CASC[name] = cv2.CascadeClassifier(os.path.join(cv2.data.haarcascades, name))
        if CASC[name].empty():
            sys.exit(f"OpenCV has no {name}: install opencv-python-headless<5 (OpenCV 5 dropped the bundled detectors)")
    return CASC[name]


def detect_face(img):
    """Largest face as (x, y, w, h) in frame px, and which detector found it."""
    sc = 540 / img.shape[1]
    small = cv2.resize(img, None, fx=sc, fy=sc)
    gray = cv2.equalizeHist(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY))
    mins = int(small.shape[1] * 0.10)
    for name in ("haarcascade_frontalface_default.xml", "haarcascade_frontalface_alt2.xml"):
        f = cascade(name).detectMultiScale(gray, 1.08, 5, minSize=(mins, mins))
        if len(f):
            x, y, w, h = max(f, key=lambda r: r[2] * r[3])
            return tuple(int(v / sc) for v in (x, y, w, h)), "frontal"
    for flip in (False, True):
        g = cv2.flip(gray, 1) if flip else gray
        f = cascade("haarcascade_profileface.xml").detectMultiScale(g, 1.08, 4, minSize=(mins, mins))
        if len(f):
            x, y, w, h = max(f, key=lambda r: r[2] * r[3])
            if flip:
                x = g.shape[1] - x - w
            return tuple(int(v / sc) for v in (x, y, w, h)), "profile"
    return None, None


def eye_line(img, face):
    x, y, w, h = face
    roi = cv2.cvtColor(img[y: y + int(h * 0.6), x: x + w], cv2.COLOR_BGR2GRAY)
    eyes = cascade("haarcascade_eye.xml").detectMultiScale(roi, 1.1, 6, minSize=(max(8, w // 9), max(8, w // 9)))
    eyes = [e for e in eyes if 0.15 * h < e[1] + e[3] / 2 < 0.6 * h]
    if len(eyes) >= 1:
        return int(y + np.median([e[1] + e[3] / 2 for e in eyes])), "eyes"
    return int(y + 0.40 * h), "estimate"


def head_top(img, face):
    """Scan up from the face: the head (hair, cap) ends where the rows above look like the background."""
    x, y, w, h = face
    x0, x1 = max(0, x + int(0.15 * w)), min(img.shape[1], x + int(0.85 * w))
    far = max(0, y - int(1.6 * h))
    if y - far < 12:
        return max(0, y - int(0.45 * h)), "estimate (face near the top)"
    band = img[far:y, x0:x1].astype(int)
    # background colour: the median of the rows farthest above the face
    ref = np.median(band[: max(4, len(band) // 8)].reshape(-1, 3), axis=0)
    diff = np.abs(band - ref).sum(axis=2) > 60
    frac = diff.mean(axis=1)
    rows = np.where(frac > 0.35)[0]
    if not len(rows):
        return max(0, y - int(0.45 * h)), "estimate (no edge found)"
    # topmost run of "head" rows that continues down to the face (ignore specks in the background)
    top = rows[-1]
    for r in rows[::-1]:
        if top - r <= 3:
            top = r
        else:
            break
    return far + int(top), "measured"


def rng(vals):
    return [int(min(vals)), int(max(vals))] if vals else None


def measure_shot(path, a, b, fps, w, h, samples):
    span = max(1, b - a)
    pick = sorted({int(a + 3 + (span - 6) * (i + 0.5) / samples) for i in range(samples)}) if span > 8 else [a + span // 2]
    rec, methods, mid = [], {}, None
    for f in pick:
        img = frame_at(path, f, fps, w, h)
        if img is None:
            continue
        if mid is None and f >= a + span // 2:
            mid = (f, img)
        face, how = detect_face(img)
        if not face:
            continue
        ey, eh = eye_line(img, face)
        ht, hh = head_top(img, face)
        x, y, fw, fh = face
        rec.append({"f": f, "face": face, "eye": ey, "top": ht, "mouth": int(y + 0.80 * fh),
                    "chin": int(y + fh * 1.05), "cx": int(x + fw / 2)})
        for k, v in (("face", how), ("eyeLine", eh), ("headTop", hh)):
            methods.setdefault(k, {}).setdefault(v, 0)
            methods[k][v] += 1
    if mid is None and pick:
        mid = (pick[len(pick) // 2], frame_at(path, pick[len(pick) // 2], fps, w, h))
    out = {"from": a, "to": b, "detected": f"{len(rec)}/{len(pick)}"}
    if rec:
        med = np.median([r["face"] for r in rec], axis=0).astype(int).tolist()
        out.update({"face": med, "headTop": rng([r["top"] for r in rec]), "eyeLine": rng([r["eye"] for r in rec]),
                    "mouth": rng([r["mouth"] for r in rec]), "chin": rng([r["chin"] for r in rec]),
                    "centreX": rng([r["cx"] for r in rec]), "methods": methods})
    return out, mid


def suggest(shots, w, h):
    sx, sy = W / w, H / h
    found = [s for s in shots if s.get("chin")]
    notes = []
    if not found:
        return {"captionBaseline": None, "hookTop": None, "notes": ["no face found: measure by hand from the grid sheet"]}
    chin = max(s["chin"][1] for s in found) * sy
    top = min(s["headTop"][0] for s in found) * sy
    cap = int(min(IG_BOTTOM - 40, chin + 70))
    notes.append(f"caption baseline y{cap}: ~70 px under the lowest chin (y{int(chin)}), never on it. With a "
                 "handheld mic, use 40-50 px below the windscreen's top instead (read it off the grid).")
    hook_top = int(top - 30 - 2 * HOOK_LINE_H)
    if hook_top >= IG_TOP:
        notes.append(f"a two-line hook fits above the head: top y{hook_top} (clears the head top y{int(top)} by 30 px)")
    else:
        hook_top = IG_TOP
        notes.append(f"no room for a two-line hook above the head (head top y{int(top)}): start it at y{IG_TOP} "
                     "and let it overlap the hair, use one line, or use a split layout")
    moves = [s for s in found if s["headTop"][1] - s["headTop"][0] > 30]
    if moves:
        notes.append("the head moves more than 30 px in shot(s) starting " + ", ".join(f"f{s['from']}" for s in moves)
                     + ": set positions from the extremes, or let a crop follow the head")
    return {"captionBaseline": cap, "hookTop": hook_top, "notes": notes}


def annotate(img, shot, sug, w, h, out):
    vis = img.copy()
    sx = w / W
    def hline(y, col, label, thick=3):
        if y is None:
            return
        y = int(y)
        cv2.line(vis, (0, y), (w, y), col, thick)
        cv2.putText(vis, label, (12, max(28, y - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.9 * sx * 1.4, col, 2, cv2.LINE_AA)
    for yy in (IG_TOP, IG_BOTTOM):
        y = int(yy * h / H)
        for x in range(0, w, 40):
            cv2.line(vis, (x, y), (x + 20, y), (255, 255, 255), 2)
    if shot.get("face"):
        x, y, fw, fh = shot["face"]
        cv2.rectangle(vis, (x, y), (x + fw, y + fh), (200, 200, 200), 2)
        hline(shot["headTop"][0], (255, 255, 0), f"head top {shot['headTop'][0]}-{shot['headTop'][1]}")
        hline(shot["eyeLine"][0], (0, 255, 255), f"eyes {shot['eyeLine'][0]}-{shot['eyeLine'][1]}")
        hline(shot["mouth"][0], (0, 165, 255), f"mouth {shot['mouth'][0]}")
        hline(shot["chin"][1], (0, 0, 255), f"chin {shot['chin'][1]}")
    if sug.get("captionBaseline"):
        hline(sug["captionBaseline"] * h / H, (0, 220, 0), f"caption baseline {sug['captionBaseline']}", 4)
    if sug.get("hookTop"):
        t = int(sug["hookTop"] * h / H)
        cv2.rectangle(vis, (int(w * 0.12), t), (int(w * 0.88), t + int(2 * HOOK_LINE_H * h / H)), (255, 120, 0), 3)
        cv2.putText(vis, "hook", (int(w * 0.12) + 10, t + 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 120, 0), 2, cv2.LINE_AA)
    cv2.imwrite(out, vis)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("take")
    ap.add_argument("--cuts", help="cuts JSON from detect-cuts.py (default: <take>.cuts.json if present)")
    ap.add_argument("--samples", type=int, default=8, help="frames sampled per shot")
    ap.add_argument("--out", help="output JSON (default: <take>.framing.json)")
    ap.add_argument("--out-dir", help="annotated frames (default: $TMPDIR/<take>-measure)")
    a = ap.parse_args()
    if not os.path.exists(a.take):
        sys.exit(f"no such file: {a.take}")
    w, h, fps, frames = probe(a.take)
    stem = os.path.splitext(a.take)[0]
    cuts_path = a.cuts or stem + ".cuts.json"
    cuts = json.load(open(cuts_path))["cuts"] if os.path.exists(cuts_path) else []
    bounds = [0] + [c for c in cuts if 0 < c < frames] + [frames]
    od = a.out_dir or os.path.join(os.environ.get("TMPDIR", "/tmp"), os.path.basename(stem) + "-measure")
    os.makedirs(od, exist_ok=True)

    shots, mids = [], []
    for s, e in zip(bounds[:-1], bounds[1:]):
        shot, mid = measure_shot(a.take, s, e, fps, w, h, a.samples)
        shots.append(shot)
        mids.append(mid)
    warnings = []
    if (w, h) != (W, H):
        warnings.append(f"the take is {w}x{h}: numbers are in its own pixels; suggestions are scaled to 1080x1920")
    for s in shots:
        if not s.get("face"):
            warnings.append(f"shot f{s['from']}-{s['to']}: no face found ({s['detected']}); b-roll or a screen? measure by hand")
    sug = suggest(shots, w, h)
    result = {"take": os.path.basename(a.take), "size": [w, h], "fps": fps, "frames": frames,
              "cuts": cuts_path if cuts else None, "shots": shots, "suggest": sug, "warnings": warnings}
    out = a.out or stem + ".framing.json"
    json.dump(result, open(out, "w"), indent=1)

    print(f"{result['take']}: {len(shots)} shot(s), {w}x{h}")
    for s in shots:
        if s.get("face"):
            print(f"  f{s['from']:<5}-{s['to']:<5} face {s['detected']:>5}  head top {s['headTop']}  eyes {s['eyeLine']}"
                  f"  mouth {s['mouth']}  chin {s['chin']}  centre x {s['centreX']}")
        else:
            print(f"  f{s['from']:<5}-{s['to']:<5} no face ({s['detected']})")
    for n in sug["notes"]:
        print("  > " + n)
    for wn in warnings:
        print("  ! " + wn)
    made = []
    for s, mid in zip(shots, mids):
        if mid and mid[1] is not None:
            p = os.path.join(od, f"framing-{s['from']}.png")
            annotate(mid[1], s, sug, w, h, p)
            made.append(p)
    print(f"-> {out}\nlook at:\n  " + "\n  ".join(made))
    return 0


if __name__ == "__main__":
    sys.exit(main())

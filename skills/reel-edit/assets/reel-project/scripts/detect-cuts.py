#!/usr/bin/env python3
"""Measure a take in one command: its cuts (in frames), its frame count, and contact sheets to read.

    python3 detect-cuts.py public/recordings/take.mp4                  -> public/recordings/take.cuts.json + sheets
    python3 detect-cuts.py take.mp4 --threshold 0.05 --fps 30 --sheet-every 2 --out-dir "$TMPDIR/take"

Writes:
  <take>.cuts.json   {"fps", "frames", "duration", "cuts": [frame...], "detail": [{"frame", "t", "score", "soft"}],
                      "warnings": [...]}
                     import it in the composition: `import take from "../../public/recordings/take.cuts.json"`
  <out-dir>/sheet.jpg        one frame every N seconds, timecoded: look for footage the creator already edited
                             (b-roll, title cards, their own captions) and schedule around it
  <out-dir>/cuts.jpg         the first frame after every cut, labelled with its frame number
  <out-dir>/grid-<f>.png     measuring grids (108x96 px cells, 540x480 major) on a frame from each shot, to read off
                             hair or cap top, eye line, mouth, chin and the mic windscreen

The threshold defaults to 0.05, not ffmpeg's usual 0.3 or 0.15: soft cuts are missed above that, and a missed
cut silently becomes a caption-drift bug later. Cuts scoring under 0.15 are marked "soft": check them on cuts.jpg.
"""
import argparse, json, os, re, subprocess, sys


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def probe(path):
    r = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
             "stream=codec_name,width,height,r_frame_rate,nb_read_frames:format=duration,format_name", "-of", "json", path])
    if r.returncode:
        sys.exit(f"ffprobe failed on {path}: {r.stderr.strip()}")
    d = json.loads(r.stdout)
    s, f = d["streams"][0], d["format"]
    num, den = (int(x) for x in s["r_frame_rate"].split("/"))
    return {"codec": s["codec_name"], "w": s["width"], "h": s["height"], "fps": num / den if den else 0,
            "frames": int(s.get("nb_read_frames") or 0), "duration": float(f["duration"]), "container": f["format_name"]}


def scenes(path, threshold):
    r = run(["ffmpeg", "-v", "error", "-i", path, "-vf", f"select='gt(scene,{threshold})',metadata=print:file=-",
             "-an", "-f", "null", "-"])
    out, t = [], None
    for line in r.stdout.splitlines():
        m = re.search(r"pts_time:([\d.]+)", line)
        if m:
            t = float(m.group(1))
        m = re.search(r"lavfi\.scene_score=([\d.]+)", line)
        if m and t is not None:
            out.append((t, float(m.group(1))))
            t = None
    return out


def sheet(path, out, every, dur):
    cols = 6
    n = max(1, int(dur // every))
    rows = (n + cols - 1) // cols
    vf = (f"fps=1/{every},scale=240:-2,drawtext=text='%{{pts\\:hms}}':x=6:y=6:fontsize=18:fontcolor=white:"
          f"box=1:boxcolor=black@0.6,tile={cols}x{rows}:padding=4:color=0x202020")
    r = run(["ffmpeg", "-v", "error", "-y", "-i", path, "-vf", vf, "-frames:v", "1", out])
    if r.returncode:   # drawtext needs a font; retry without labels
        run(["ffmpeg", "-v", "error", "-y", "-i", path, "-vf", f"fps=1/{every},scale=240:-2,tile={cols}x{rows}:padding=4",
             "-frames:v", "1", out])


def cuts_sheet(path, out, frames, fps):
    if not frames:
        return False
    sel = "+".join(f"eq(n\\,{f})" for f in frames[:60])
    cols = min(6, len(frames))
    rows = (min(len(frames), 60) + cols - 1) // cols
    # label before select, so %{n} is the take's own frame number (after select it would count 0, 1, 2...)
    label = "drawtext=text='f%{n}':x=24:y=24:fontsize=84:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=10,"
    pick = f"select='{sel}',scale=240:-2,"
    tile = f"tile={cols}x{rows}:padding=4:color=0x202020"
    r = run(["ffmpeg", "-v", "error", "-y", "-i", path, "-vf", label + pick + tile, "-vsync", "0", "-frames:v", "1", out])
    if r.returncode:
        run(["ffmpeg", "-v", "error", "-y", "-i", path, "-vf", pick + tile, "-vsync", "0", "-frames:v", "1", out])
    return True


def grid(path, out, frame):
    run(["ffmpeg", "-v", "error", "-y", "-i", path, "-vf",
         f"select=eq(n\\,{frame}),drawgrid=w=108:h=96:t=2:c=red@0.5,drawgrid=w=540:h=480:t=4:c=yellow@0.9",
         "-vsync", "0", "-frames:v", "1", out])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("take")
    ap.add_argument("--threshold", type=float, default=0.05)
    ap.add_argument("--fps", type=float, default=30)
    ap.add_argument("--min-gap", type=int, default=4, help="merge detections closer than this many frames")
    ap.add_argument("--sheet-every", type=float, default=2.0, help="seconds between contact-sheet frames")
    ap.add_argument("--out", help="cuts JSON path (default: <take>.cuts.json)")
    ap.add_argument("--out-dir", help="where the sheets go (default: $TMPDIR/<take>-measure)")
    ap.add_argument("--no-sheets", action="store_true")
    a = ap.parse_args()

    if not os.path.exists(a.take):
        sys.exit(f"no such file: {a.take}")
    info = probe(a.take)
    warnings = []
    if info["codec"] in ("hevc", "h265") or a.take.lower().endswith(".mov"):
        warnings.append(f"{info['codec']} / {os.path.splitext(a.take)[1]}: transcode to H.264 mp4 before editing "
                        "(OffthreadVideo shows duplicate-frame flashes on .mov/HEVC); see the skill's Ingest step")
    if abs(info["fps"] - a.fps) > 0.01:
        warnings.append(f"the take is {info['fps']:.3f} fps, the reel is {a.fps:g}: transcode with -r {a.fps:g} first")
    if (info["w"], info["h"]) != (1080, 1920):
        warnings.append(f"the take is {info['w']}x{info['h']}, not 1080x1920: scale or crop it in the composition")

    raw = scenes(a.take, a.threshold)
    merged = []
    for t, s in raw:
        f = round(t * a.fps)
        if merged and f - merged[-1]["frame"] < a.min_gap:
            if s > merged[-1]["score"]:
                merged[-1] = {"frame": f, "t": round(t, 3), "score": round(s, 3)}
            continue
        merged.append({"frame": f, "t": round(t, 3), "score": round(s, 3)})
    for c in merged:
        c["soft"] = c["score"] < 0.15

    stem = os.path.splitext(a.take)[0]
    out = a.out or stem + ".cuts.json"
    result = {"take": os.path.basename(a.take), "fps": a.fps, "frames": info["frames"],
              "duration": round(info["duration"], 3), "size": [info["w"], info["h"]], "codec": info["codec"],
              "threshold": a.threshold, "cuts": [c["frame"] for c in merged], "detail": merged, "warnings": warnings}
    with open(out, "w") as fh:
        json.dump(result, fh, indent=1)

    print(f"{result['take']}: {info['frames']} frames, {info['duration']:.2f} s, {info['w']}x{info['h']} {info['codec']} "
          f"@ {info['fps']:.3f} fps")
    for w in warnings:
        print(f"  ! {w}")
    print(f"{len(merged)} cut(s) at threshold {a.threshold}:")
    for c in merged:
        print(f"  f{c['frame']:<6} {c['t']:8.3f}s  score {c['score']:.3f}{'  (soft: check it)' if c['soft'] else ''}")
    print(f"-> {out}")

    if not a.no_sheets:
        od = a.out_dir or os.path.join(os.environ.get("TMPDIR", "/tmp"), os.path.basename(stem) + "-measure")
        os.makedirs(od, exist_ok=True)
        sheet(a.take, os.path.join(od, "sheet.jpg"), a.sheet_every, info["duration"])
        made = [os.path.join(od, "sheet.jpg")]
        if cuts_sheet(a.take, os.path.join(od, "cuts.jpg"), [c["frame"] for c in merged], a.fps):
            made.append(os.path.join(od, "cuts.jpg"))
        starts = [0] + [c["frame"] for c in merged]
        ends = [c["frame"] for c in merged] + [info["frames"]]
        for s, e in list(zip(starts, ends))[:8]:          # one grid per shot, mid-shot
            f = (s + e) // 2
            grid(a.take, os.path.join(od, f"grid-{f}.png"), f)
            made.append(os.path.join(od, f"grid-{f}.png"))
        print("sheets:\n  " + "\n  ".join(made))
    return 0


if __name__ == "__main__":
    sys.exit(main())

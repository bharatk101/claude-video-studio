#!/usr/bin/env python3
"""Several clips -> one take. Normalise every clip to the reel format, optionally jump-cut each one, match their
loudness, and join them into a single video that the rest of the reel workflow treats as one take.

    python3 assemble.py clip1.mp4 clip2.MOV clip3.mp4 --out public/recordings/reel.mp4
    python3 assemble.py public/recordings/raw --order time --out public/recordings/reel.mp4    # a whole folder
    python3 assemble.py public/recordings/raw/*.MOV --order time --jumpcuts --fillers --punch 1.1 --out ...
    options: --order given|name|time   --fit auto|crop|blur   --trim-ends   --lufs -16   --min-pause 0.35

Each clip:
  - is turned upright (phone rotation), converted to 1080x1920 at 30 fps (any size, fps, .mov, HEVC):
      vertical: scaled to fill and centre-cropped; landscape: cropped around the speaker's face when one is found
      (OpenCV), otherwise fitted over a blurred copy of itself (--fit crop / blur to force one)
  - keeps only its speech with --jumpcuts (the same cutting as jump-cuts.py: word-safe with <clip>.words.json,
    --fillers drops um/uh), or only loses its dead air at the start and end with --trim-ends
  - is gain-matched to --lufs (default -16) so clips recorded at different levels sound the same; a clip with no
    audio gets silence
Joins are frame-exact with ~12 ms audio fades, and audio stays in sync across every join.

Writes, next to --out:
  <out>.mp4            the assembled take (H.264 + AAC, 1080x1920, 30 fps)
  <out>.cuts.json      every join as a cut (kind "clip" or "jump"), in detect-cuts.py's format, so captions break
                       at them and measure-framing.py measures each shot
  <out>.words.json     the clips' transcripts re-timed onto the assembled timeline, when EVERY clip has one;
                       otherwise transcribe the assembled take once (bash run.sh transcribe <out>)
  <out>.assembly.json  what came from where: per clip its fit, gain, and kept spans (source seconds -> out frames)
"""
import argparse, concurrent.futures as cf, datetime, importlib.util, json, os, re, shutil, subprocess, sys, tempfile

import numpy as np

W, H, FPS, SR = 1080, 1920, 30, 48000
HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        raise RuntimeError(f"{cmd[0]} failed: {(r.stderr or r.stdout).strip()[-800:]}")
    return r


# ---------- probing ----------
def probe(path):
    d = json.loads(run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=codec_type,codec_name,width,height,avg_frame_rate,r_frame_rate,pix_fmt,color_transfer"
                        ":stream_tags=rotate:stream_side_data=rotation:format=duration:format_tags=creation_time",
                        "-of", "json", path]).stdout)
    v = next((s for s in d.get("streams", []) if s["codec_type"] == "video"), None)
    if not v:
        raise RuntimeError(f"{path} has no video stream")
    rot = 0
    for sd in v.get("side_data_list") or []:
        if "rotation" in sd:
            rot = int(float(sd["rotation"]))
    rot = rot or int(float((v.get("tags") or {}).get("rotate", 0)))
    w, h = v["width"], v["height"]
    if abs(rot) % 180 == 90:                              # ffmpeg turns it upright when decoding
        w, h = h, w
    num, den = (int(x) for x in (v.get("avg_frame_rate") or v["r_frame_rate"]).split("/"))
    fps = num / den if den else 0
    created = (d.get("format", {}).get("tags") or {}).get("creation_time")
    return {"w": w, "h": h, "rotation": rot, "fps": round(fps, 3), "codec": v["codec_name"],
            "pix_fmt": v.get("pix_fmt", ""), "hdr": v.get("color_transfer") in ("arib-std-b67", "smpte2084"),
            "audio": any(s["codec_type"] == "audio" for s in d["streams"]),
            "duration": float(d["format"]["duration"]), "created": created}


def loudness(path):
    """Integrated loudness (LUFS) of the first audio stream, or None for silence / no audio."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-map", "0:a:0", "-af", "ebur128=framelog=quiet",
                        "-f", "null", "-"], capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    if not m:
        return None
    v = float(m[-1])
    return None if v <= -69 else v


VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi", ".mts"}


def expand_inputs(items, out=None):
    """Files stay as given; a folder becomes the videos directly inside it (by name, hidden files and the
    output itself skipped). Returns absolute paths, de-duplicated, in order."""
    clips = []
    for it in items:
        p = os.path.abspath(os.path.expanduser(it))
        if os.path.isdir(p):
            found = sorted((os.path.join(p, f) for f in os.listdir(p)
                            if not f.startswith(".") and os.path.splitext(f)[1].lower() in VIDEO_EXTS
                            and os.path.isfile(os.path.join(p, f))), key=lambda q: os.path.basename(q).lower())
            found = [f for f in found if f != out]
            if not found:
                sys.exit(f"no videos in folder: {p}  (looked for {', '.join(sorted(VIDEO_EXTS))})")
            clips += found
        elif os.path.exists(p):
            clips.append(p)
        else:
            sys.exit(f"no such file: {p}")
    seen, uniq = set(), []
    for c in clips:
        if c not in seen:
            seen.add(c); uniq.append(c)
    return uniq


def order_clips(paths, how):
    if how == "name":
        return sorted(paths, key=lambda p: os.path.basename(p).lower())
    if how == "time":
        def key(p):
            c = probe(p)["created"]
            if c:
                try:
                    return datetime.datetime.fromisoformat(c.replace("Z", "+00:00")).timestamp()
                except ValueError:
                    pass
            return os.path.getmtime(p)
        return sorted(paths, key=key)
    return list(paths)


# ---------- framing ----------
def face_x(path, info):
    """Horizontal centre of the speaker's face in a landscape clip (source px), or None."""
    try:
        mf = _load("measure_framing", "measure-framing.py")
    except SystemExit:                                    # OpenCV isn't installed
        return None
    xs = []
    for frac in (0.3, 0.5, 0.7):
        img = mf.frame_at(path, int(info["duration"] * frac * 30), 30, info["w"], info["h"])
        if img is None:
            continue
        face, _ = mf.detect_face(img)
        if face:
            xs.append(face[0] + face[2] / 2)
    return float(np.median(xs)) if xs else None


def fit_filter(info, fit, fx):
    """ffmpeg filter (input already upright) that makes exactly W x H."""
    w, h = info["w"], info["h"]
    if fit == "blur":
        return (f"split=2[bg][fg];[bg]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                f"boxblur=30:2,eq=brightness=-0.06[bgb];[fg]scale={W}:-2[fgs];[bgb][fgs]overlay=(W-w)/2:(H-h)/2")
    if fit == "face" and fx is not None:
        sw = int(round(w * H / h / 2) * 2)
        x = int(min(max(fx * H / h - W / 2, 0), sw - W))
        return f"scale={sw}:{H},crop={W}:{H}:{x}:0"
    return f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"      # cover, centred


def choose_fit(info, want, fx):
    """Vertical clips always fill the frame; --fit only decides landscape ones."""
    if info["w"] < info["h"]:
        return "cover"
    if want == "blur":
        return "blur"
    if want == "crop":
        return "face" if fx is not None else "cover"
    return "face" if fx is not None else "blur"


# ---------- one segment ----------
def encode_segment(job):
    s, n, src, info, vf, gain, punch, out = (job[k] for k in ("s", "n", "src", "info", "vf", "gain", "punch", "out"))
    length = n / FPS
    chain = f"[0:v]fps={FPS},{vf}"
    if punch != 1.0:   # punch in toward the eye line, back to exactly W x H
        chain += f"[fit];[fit]scale={int(round(W * punch / 2) * 2)}:-2,crop={W}:{H}:(iw-{W})/2:(ih-{H})*0.4"
    chain += f",setsar=1,format=yuv420p,tpad=stop_mode=clone:stop={FPS}[v]"
    ain = "[0:a]" if info["audio"] else "[1:a]"
    achain = (f"{ain}aresample={SR},aformat=sample_fmts=fltp:channel_layouts=stereo,volume={gain:.2f}dB,"
              f"afade=t=in:d=0.012,afade=t=out:st={max(0.0, length - 0.012):.4f}:d=0.012,"
              f"apad,atrim=end_sample={n * (SR // FPS)}[a]")
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{s:.4f}", "-t", f"{length + 0.25:.4f}", "-i", src]
    if not info["audio"]:
        cmd += ["-f", "lavfi", "-t", f"{length + 0.25:.4f}", "-i", f"anullsrc=r={SR}:cl=stereo"]
    cmd += ["-filter_complex", chain + ";" + achain, "-map", "[v]", "-map", "[a]", "-frames:v", str(n),
            "-c:v", "libx264", "-preset", "medium", "-crf", "15", "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-video_track_timescale", "15360", "-c:a", "pcm_s16le", out]
    run(cmd)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("clips", nargs="+", help="video files, and/or folders (every video directly inside, by name)")
    ap.add_argument("--out", help="assembled take (default: assembled.mp4 next to the first clip)")
    ap.add_argument("--order", choices=["given", "name", "time"], default="given",
                    help="given (as listed), name (A-Z), time (recording time, then file time)")
    ap.add_argument("--fit", choices=["auto", "crop", "blur"], default="auto",
                    help="landscape clips: auto (crop on the face if found, else blur-fill), crop, or blur")
    ap.add_argument("--jumpcuts", action="store_true", help="cut the pauses inside every clip")
    ap.add_argument("--fillers", action="store_true", help="with --jumpcuts: also cut um / uh (needs transcripts)")
    ap.add_argument("--trim-ends", action="store_true", help="only cut dead air at each clip's start and end")
    ap.add_argument("--min-pause", type=float, default=0.35)
    ap.add_argument("--punch", type=float, default=1.0, help="alternate zoom per segment, e.g. 1.1, to hide joins")
    ap.add_argument("--lufs", type=float, default=-16.0, help="loudness every clip is matched to")
    ap.add_argument("--jobs", type=int, default=min(4, os.cpu_count() or 2))
    a = ap.parse_args()

    first = os.path.abspath(os.path.expanduser(a.clips[0]))
    out = os.path.abspath(os.path.expanduser(a.out)) if a.out else \
        os.path.join(first if os.path.isdir(first) else os.path.dirname(first), "assembled.mp4")
    clips = expand_inputs(a.clips, out)
    if out in clips:
        sys.exit("--out can't be one of the input clips")
    stem = os.path.splitext(out)[0]
    jc = _load("jump_cuts", "jump-cuts.py")
    clips = order_clips(clips, a.order)

    plan, warnings, seg_jobs, t_out = [], [], [], 0
    tmp = tempfile.mkdtemp(prefix="assemble-")
    for ci, path in enumerate(clips):
        info = probe(path)
        name = os.path.basename(path)
        wpath = os.path.splitext(path)[0] + ".words.json"
        words = json.load(open(wpath)) if os.path.exists(wpath) else None
        if info["hdr"]:
            warnings.append(f"{name} is HDR: colours may look flat after conversion; export it as SDR "
                            "(iPhone: Settings > Camera > Formats > HDR Video off) for the best match")
        fx = face_x(path, info) if (info["w"] >= info["h"] and a.fit != "blur") else None
        fit = choose_fit(info, a.fit, fx)
        lufs = loudness(path) if info["audio"] else None
        gain = max(-20.0, min(20.0, a.lufs - lufs)) if lufs is not None else 0.0

        if (a.jumpcuts or a.trim_ends) and info["audio"]:
            try:
                kf, _, _, _ = jc.plan_keep(path, words, FPS, info["duration"], a.min_pause, fillers=a.fillers)
            except ValueError:
                kf = [[0, int(info["duration"] * FPS)]]
                warnings.append(f"{name}: no speech found, kept whole")
            if a.trim_ends and not a.jumpcuts and kf:
                kf = [[kf[0][0], kf[-1][1]]]
        else:
            kf = [[0, int(np.floor(info["duration"] * FPS))]]
            if (a.jumpcuts or a.trim_ends) and not info["audio"]:
                warnings.append(f"{name}: no audio, kept whole")

        segs = []
        for f0, f1 in kf:
            n = f1 - f0
            if n < 2:
                continue
            k = len(seg_jobs)
            punch = a.punch if (a.punch != 1.0 and k % 2) else 1.0
            seg = {"from": round(f0 / FPS, 3), "to": round(f1 / FPS, 3), "outFrom": t_out, "frames": n, "scale": punch}
            segs.append(seg)
            seg_jobs.append({"s": f0 / FPS, "n": n, "src": path, "info": info, "vf": fit_filter(info, fit, fx),
                             "gain": gain, "punch": punch, "out": os.path.join(tmp, f"seg{k:04d}.mov"),
                             "clip": ci, "words": words, "outFrom": t_out})
            t_out += n
        plan.append({"src": name, "path": path, "size": [info["w"], info["h"]], "rotation": info["rotation"],
                     "fps": info["fps"], "codec": info["codec"], "duration": round(info["duration"], 3),
                     "audio": info["audio"], "lufs": lufs, "gainDb": round(gain, 2), "fit": fit,
                     "faceX": round(fx) if fx is not None else None,
                     "transcript": words is not None or not info["audio"],   # a silent clip needs none
                     "kept": round(sum(s["frames"] for s in segs) / FPS, 2), "segments": segs})

    if not seg_jobs:
        sys.exit("nothing to assemble")
    print(f"assembling {len(clips)} clip(s), {len(seg_jobs)} segment(s) -> {t_out} frames ({t_out / FPS:.2f}s)")
    with cf.ThreadPoolExecutor(max_workers=max(1, a.jobs)) as ex:
        list(ex.map(encode_segment, seg_jobs))

    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w") as f:
        for j in seg_jobs:
            f.write(f"file '{j['out'].replace(os.sep, '/')}'\n")   # forward slashes: safe on Windows too
    os.makedirs(os.path.dirname(out), exist_ok=True)
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c:v", "copy",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out])
    shutil.rmtree(tmp, ignore_errors=True)

    # cuts: every join (clip boundaries and jump cuts), in detect-cuts.py's format
    detail, prev_clip = [], None
    for j in seg_jobs:
        if j["outFrom"] > 0:
            detail.append({"frame": j["outFrom"], "t": round(j["outFrom"] / FPS, 3), "score": 1.0, "soft": False,
                           "kind": "clip" if j["clip"] != prev_clip else "jump", "source": plan[j["clip"]]["src"]})
        prev_clip = j["clip"]
    cuts = {"take": os.path.basename(out), "fps": FPS, "frames": t_out, "duration": round(t_out / FPS, 3),
            "size": [W, H], "codec": "h264", "threshold": None, "cuts": [d["frame"] for d in detail],
            "detail": detail, "warnings": [], "assembledFrom": [c["src"] for c in plan]}
    json.dump(cuts, open(stem + ".cuts.json", "w"), indent=1)

    # transcript on the assembled timeline, only when every clip had one
    wrote_words = all(c["transcript"] for c in plan)
    if wrote_words:
        merged = []
        for j in seg_jobs:
            s, e, o = j["s"], j["s"] + j["n"] / FPS, j["outFrom"]
            for w in j["words"] or []:
                if a.fillers and re.sub(r"[^a-z]", "", w["text"].lower()) in jc.FILLERS:
                    continue
                t0 = w["startMs"] / 1000
                if s <= t0 < e:
                    merged.append({**w, "startMs": int(round((o / FPS + t0 - s) * 1000)),
                                   "endMs": int(round((o / FPS + min(w["endMs"] / 1000, e) - s) * 1000))})
        json.dump(merged, open(stem + ".words.json", "w"), indent=0)

    for c in plan:
        c.pop("path", None)
    json.dump({"out": os.path.basename(out), "fps": FPS, "frames": t_out, "duration": round(t_out / FPS, 3),
               "targetLufs": a.lufs, "settings": {"order": a.order, "fit": a.fit, "jumpcuts": a.jumpcuts,
                                                  "fillers": a.fillers, "trimEnds": a.trim_ends, "punch": a.punch},
               "clips": plan, "warnings": warnings}, open(stem + ".assembly.json", "w"), indent=1)

    for c in plan:
        lf = f"{c['lufs']:.1f} LUFS -> {c['gainDb']:+.1f} dB" if c["lufs"] is not None else "no audio"
        print(f"  {c['src']:<28} {c['size'][0]}x{c['size'][1]} {c['fps']:g}fps  fit {c['fit']:<5}  {lf:<26}"
              f" {c['duration']:6.2f}s -> {c['kept']:6.2f}s  {len(c['segments'])} segment(s)")
    for w in warnings:
        print("  ! " + w)
    print(f"-> {out}\n-> {stem}.cuts.json  ({len(detail)} joins)")
    print(f"-> {stem}.words.json" if wrote_words else
          f"   no combined transcript (not every clip had one): bash run.sh transcribe {os.path.relpath(out)}")
    print(f"-> {stem}.assembly.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())

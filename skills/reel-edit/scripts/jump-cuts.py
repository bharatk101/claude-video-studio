#!/usr/bin/env python3
"""Jump cuts: find the pauses (and optionally filler words) in a take and keep only the speech.

    python3 jump-cuts.py public/recordings/take.mp4                        uses take.words.json if it exists
    python3 jump-cuts.py take.mp4 --min-pause 0.35 --fillers --punch 1.12
    python3 jump-cuts.py take.mp4 --render out/take-jumpcut.mp4             also write a quick ffmpeg preview

Writes:
  <take>.jumpcuts.json   {"fps", "sourceFrames", "keep": [{"from", "to", "outFrom", "scale"}], "outFrames",
                          "removed": [{"from", "to", "why"}], "saved": seconds}
                         keep[].from/to are SOURCE frames; outFrom is where that span starts in the edit.
                         Feed it to components/JumpCut.tsx.
  <take>.cut.words.json  the transcript re-timed onto the edited timeline (words in removed spans dropped), so
                         captions and word-anchored graphics use it directly.

How a pause is found: a 10 ms RMS envelope of the voice, silent below (20th percentile + 8 dB), the same test
references/captions.md uses. With a transcript, a pause must also fall between two words, so a cut never lands
inside a word (whisper's timings alone drift). Each kept span gets --pre / --post padding so onsets and word
tails survive; spans closer than --min-pause are merged.
"""
import argparse, json, os, re, subprocess, sys

import numpy as np

SR = 16000
FILLERS = {"um", "uh", "uhm", "umm", "erm", "er", "ah", "hmm", "mm"}


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,r_frame_rate,nb_frames:format=duration",
                          "-of", "json", path], capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    v = next((s for s in d["streams"] if s["codec_type"] == "video"), None)
    if not any(s["codec_type"] == "audio" for s in d["streams"]):
        sys.exit(f"{path} has no audio track: nothing to cut on")
    fps = 30.0
    if v:
        n, dd = (int(x) for x in v["r_frame_rate"].split("/"))
        fps = n / dd
    return fps, float(d["format"]["duration"])


def envelope(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.int16).astype(float) / 32768
    hop = SR // 100                                        # 10 ms
    n = len(x) // hop
    rms = np.sqrt((x[: n * hop].reshape(n, hop) ** 2).mean(axis=1) + 1e-12)
    return 20 * np.log10(rms)


def voiced(env, extra_db=8.0):
    thr = np.percentile(env, 20) + extra_db
    v = env > thr
    # close tiny gaps (< 60 ms) inside words, drop blips (< 40 ms)
    v = _fill(v, 6, True)
    v = _fill(v, 4, False)
    return v, thr


def _fill(v, n, value):
    v = v.copy()
    i = 0
    while i < len(v):
        if v[i] != value:
            j = i
            while j < len(v) and v[j] != value:
                j += 1
            if j - i < n and i > 0 and j < len(v):
                v[i:j] = value
            i = j
        else:
            i += 1
    return v


def spans(mask):
    out, i = [], 0
    while i < len(mask):
        if mask[i]:
            j = i
            while j < len(mask) and mask[j]:
                j += 1
            out.append([i / 100, j / 100])
            i = j
        else:
            i += 1
    return out


def plan_keep(take, words, fps, dur, min_pause=0.35, pre=0.08, post=0.12, fillers=False):
    """The kept spans of a take, in frames at `fps`: (keep [[f0, f1], ...], removed [{from, to, why}], silence dB,
    source frames). Shared by this script and assemble.py, so both cut exactly the same way."""
    env = envelope(take)
    mask, thr = voiced(env)
    speech = spans(mask)
    if not speech:
        raise ValueError("no speech found (is the take silent?)")
    removed = []

    # a transcript makes the cuts word-safe: extend speech spans to cover every word they touch
    if words:
        for w in words:
            ws, we = w["startMs"] / 1000, w["endMs"] / 1000
            filler = fillers and re.sub(r"[^a-z]", "", w["text"].lower()) in FILLERS
            if filler:
                continue
            hit = [s for s in speech if s[0] < we and s[1] > ws]
            if hit:
                hit[0][0] = min(hit[0][0], ws)
                hit[-1][1] = max(hit[-1][1], we)
        speech.sort()

    # pad, then merge spans whose gap is shorter than a real pause
    padded = [[max(0, s - pre), min(dur, e + post)] for s, e in speech]
    keep = []
    for s, e in padded:
        if keep and s - keep[-1][1] < min_pause - pre - post:
            keep[-1][1] = max(keep[-1][1], e)
        else:
            keep.append([s, e])
    # to frames
    kf = []
    for s, e in keep:
        f0, f1 = int(np.floor(s * fps)), int(np.ceil(e * fps))
        if kf and f0 <= kf[-1][1]:
            kf[-1][1] = max(kf[-1][1], f1)
        elif f1 - f0 >= 3:
            kf.append([f0, f1])
    src_frames = int(round(dur * fps))
    # fillers are cut from the FINAL frame spans, after padding, so no padding can grow back over them
    filler_spans = []
    if words and fillers:
        for w in words:
            if re.sub(r"[^a-z]", "", w["text"].lower()) in FILLERS:
                f0 = max(0, int(np.floor((w["startMs"] / 1000 - 0.03) * fps)))
                f1 = int(np.ceil((w["endMs"] / 1000 + 0.03) * fps))
                filler_spans.append((f0, f1, w["text"]))
        for f0, f1, txt in filler_spans:
            new = []
            for s0, s1 in kf:
                if s1 <= f0 or s0 >= f1:
                    new.append([s0, s1])
                else:
                    if f0 - s0 >= 3: new.append([s0, f0])
                    if s1 - f1 >= 3: new.append([f1, s1])
            kf = new
            removed.append({"from": f0, "to": f1, "why": f"filler '{txt}'"})
    prev = 0
    for f0, f1 in kf:
        if f0 > prev:
            removed.append({"from": prev, "to": f0, "why": "pause"})
        prev = f1
    if prev < src_frames:
        removed.append({"from": prev, "to": src_frames, "why": "pause"})
    # a gap that exists only because a filler was cut is that filler, not a separate pause
    fill = [r for r in removed if r["why"] != "pause"]
    removed = fill + [r for r in removed if r["why"] == "pause"
                      and not any(r["from"] < f["to"] + 3 and r["to"] > f["from"] - 3 for f in fill)]
    removed.sort(key=lambda r: r["from"])
    return kf, removed, thr, src_frames


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("take")
    ap.add_argument("--words", help="transcript (default: <take>.words.json if it exists)")
    ap.add_argument("--min-pause", type=float, default=0.35, help="pauses at least this long are cut (s)")
    ap.add_argument("--pre", type=float, default=0.08, help="kept before each speech onset (s)")
    ap.add_argument("--post", type=float, default=0.12, help="kept after each speech end (s)")
    ap.add_argument("--fillers", action="store_true", help="also cut um / uh / erm (needs a transcript)")
    ap.add_argument("--punch", type=float, default=1.0,
                    help="alternate scale per kept span, e.g. 1.12 for a punch-in on every other cut (hides the jump)")
    ap.add_argument("--fps", type=float, help="edit frame rate (default: the take's)")
    ap.add_argument("--render", help="also write a jump-cut preview mp4 with ffmpeg")
    a = ap.parse_args()

    if not os.path.exists(a.take):
        sys.exit(f"no such file: {a.take}")
    fps0, dur = probe(a.take)
    fps = a.fps or round(fps0, 3)
    stem = os.path.splitext(a.take)[0]
    wpath = a.words or stem + ".words.json"
    words = json.load(open(wpath)) if os.path.exists(wpath) else None

    try:
        kf, removed, thr, src_frames = plan_keep(a.take, words, fps, dur, a.min_pause, a.pre, a.post, a.fillers)
    except ValueError as e:
        sys.exit(str(e))

    out, t = [], 0
    for i, (f0, f1) in enumerate(kf):
        out.append({"from": f0, "to": f1, "outFrom": t, "scale": a.punch if (a.punch != 1.0 and i % 2) else 1.0})
        t += f1 - f0
    result = {"take": os.path.basename(a.take), "fps": fps, "sourceFrames": src_frames, "outFrames": t,
              "keep": out, "removed": removed, "saved": round((src_frames - t) / fps, 2),
              "settings": {"minPause": a.min_pause, "pre": a.pre, "post": a.post, "fillers": a.fillers,
                           "punch": a.punch, "silenceDb": round(float(thr), 1), "transcript": bool(words)}}
    jpath = stem + ".jumpcuts.json"
    json.dump(result, open(jpath, "w"), indent=1)

    if words:   # re-time the transcript onto the edited timeline
        remap = []
        for w in words:
            if a.fillers and re.sub(r"[^a-z]", "", w["text"].lower()) in FILLERS:
                continue
            f = w["startMs"] / 1000 * fps
            seg = next((k for k in out if k["from"] <= f < k["to"]), None)
            if not seg:
                continue
            shift = (seg["outFrom"] - seg["from"]) / fps * 1000
            end_cap = (seg["to"] - seg["from"] + seg["outFrom"]) / fps * 1000
            remap.append({**w, "startMs": int(round(w["startMs"] + shift)),
                          "endMs": int(round(min(w["endMs"] + shift, end_cap)))})
        json.dump(remap, open(stem + ".cut.words.json", "w"), indent=0)

    print(f"{result['take']}: {src_frames} -> {t} frames ({src_frames / fps:.2f}s -> {t / fps:.2f}s, "
          f"{result['saved']}s cut), {len(out)} kept span(s), silence below {thr:.1f} dB"
          f"{', word-safe' if words else ' (no transcript: cuts follow the audio only)'}")
    for r in removed:
        if r["to"] - r["from"] >= 3:
            print(f"  cut f{r['from']:<6}-f{r['to']:<6} {(r['to'] - r['from']) / fps:5.2f}s  {r['why']}")
    print(f"-> {jpath}" + (f"\n-> {stem}.cut.words.json" if words else ""))

    if a.render:
        vw, vh = (int(v) for v in subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0",
             a.take], capture_output=True, text=True, check=True).stdout.strip().split(","))
        parts, fc = [], []
        for i, k in enumerate(out):
            s, e = k["from"] / fps, k["to"] / fps
            sc = k["scale"]
            vf = f"[0:v]trim=start_frame={k['from']}:end_frame={k['to']},setpts=PTS-STARTPTS"   # exact frames
            if sc != 1.0:   # punch in, then crop back to exactly the source size so the spans concat
                vf += f",scale=2*trunc(iw*{sc}/2):-2,crop={vw}:{vh}"
            vf += ",setsar=1"
            fc.append(vf + f"[v{i}]")
            fc.append(f"[0:a]atrim=start={s:.4f}:end={e:.4f},asetpts=PTS-STARTPTS,"
                      f"afade=t=in:d=0.012,afade=t=out:st={max(0, e - s - 0.012):.4f}:d=0.012[a{i}]")
            parts.append(f"[v{i}][a{i}]")
        fc.append("".join(parts) + f"concat=n={len(out)}:v=1:a=1[v][a]")
        os.makedirs(os.path.dirname(os.path.abspath(a.render)), exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.take, "-filter_complex", ";".join(fc), "-map", "[v]",
                        "-map", "[a]", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(fps),
                        "-c:a", "aac", "-b:a", "192k", a.render], check=True)
        print(f"-> {a.render} (preview; the Remotion JumpCut component is the real edit)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

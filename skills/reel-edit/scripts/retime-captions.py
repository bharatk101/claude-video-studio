#!/usr/bin/env python3
"""Re-time a word-level transcript by voting DTW timestamps across dense windows.

A single full-file whisper pass drifts late inside long speech (up to about a
second) and pads the last word of each sentence out to the next sentence. This
re-times every word without changing any of the text.

Usage (whisper.cpp, the most accurate: DTW token timestamps):
    python3 retime-captions.py media.mp4 words.json out.json \
        --whisper bin/whisper.cpp/build/bin/whisper-cli \
        --model   bin/whisper.cpp/models/ggml-small.bin \
        [--step 2.5] [--window 6] [--dtw small]

Usage (no compiler needed: pip3 install faster-whisper):
    python3 retime-captions.py media.mp4 words.json out.json --backend faster-whisper [--model small]

The output keeps the input's exact word list and only replaces startMs/endMs, so
any fix dictionary keyed BY INDEX keeps working. Never key one by startMs.
"""
import argparse, difflib, json, os, re, statistics, subprocess, sys, tempfile

norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())


def run_window(whisper, model, wav, out_prefix, dtw):
    subprocess.run([whisper, "-m", model, "-f", wav, "-ml", "1", "-sow",
                    "-dtw", dtw, "-oj", "-of", out_prefix, "--no-prints"],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    with open(out_prefix + ".json") as fh:
        return json.load(fh)["transcription"]


def samples16k(path):
    """Mono 16 kHz float32 samples via ffmpeg. faster-whisper gets these instead of a path, because its own file
    decoding (PyAV) breaks across PyAV versions ('unexpected keyword argument metadata_errors')."""
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


_FW = {}


def run_window_fw(model, wav):
    """Same output shape as whisper.cpp's -ml 1 JSON, from faster-whisper word timestamps."""
    if model not in _FW:
        from faster_whisper import WhisperModel
        _FW[model] = WhisperModel(model, device="auto", compute_type="int8")
    segs, _ = _FW[model].transcribe(samples16k(wav), word_timestamps=True, vad_filter=False)
    return [{"text": w.word, "offsets": {"from": int(w.start * 1000), "to": int(w.end * 1000)}}
            for s in segs for w in (s.words or [])]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("media"); ap.add_argument("words"); ap.add_argument("out")
    ap.add_argument("--backend", default="whisper.cpp", choices=["whisper.cpp", "faster-whisper"])
    ap.add_argument("--whisper", help="whisper-cli path (whisper.cpp backend)")
    ap.add_argument("--model", help="ggml model path (whisper.cpp) or model name, e.g. small (faster-whisper)")
    ap.add_argument("--step", type=float, default=2.5)
    ap.add_argument("--window", type=float, default=6.0)
    ap.add_argument("--dtw", default="small")
    a = ap.parse_args()
    if a.backend == "whisper.cpp" and not (a.whisper and a.model):
        ap.error("--whisper and --model are required for the whisper.cpp backend (or use --backend faster-whisper)")
    a.model = a.model or "small"

    ref = json.load(open(a.words))
    ra = [norm(w["text"]) for w in ref]

    tmp = tempfile.mkdtemp()
    full = os.path.join(tmp, "full.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.media,
                    "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", full], check=True)

    dur = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nk=1:nw=1", full],
        capture_output=True, text=True).stdout.strip())

    starts, s = [], 0.0
    while s < dur:
        starts.append(round(s, 3)); s += a.step

    votes = {i: [] for i in range(len(ref))}
    for n, ss in enumerate(starts):
        wav = os.path.join(tmp, f"w{n}.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(ss), "-i", full,
                        "-t", str(a.window), "-ar", "16000", "-ac", "1",
                        "-c:a", "pcm_s16le", wav], check=True)
        try:
            seg = (run_window_fw(a.model, wav) if a.backend == "faster-whisper"
                   else run_window(a.whisper, a.model, wav, os.path.join(tmp, f"w{n}"), a.dtw))
        except subprocess.CalledProcessError:
            continue
        off = ss * 1000
        ws = [(norm(x["text"]), x["offsets"]["from"] + off, x["offsets"]["to"] + off)
              for x in seg if x["text"].strip() and norm(x["text"])]
        if not ws:
            continue
        # a window is trustworthy past its lead-in and before it starts to drift
        lo = 0 if n == 0 else off + 1100
        hi = 1e9 if ss + a.window >= dur else off + 3600
        sm = difflib.SequenceMatcher(None, ra, [w[0] for w in ws], autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag != "equal":
                continue
            for k in range(i2 - i1):
                st, en = ws[j1 + k][1], ws[j1 + k][2]
                if lo <= st < hi:
                    votes[i1 + k].append((st, en))
        print(f"  window {n + 1}/{len(starts)} @ {ss:.2f}s", file=sys.stderr)

    out = [dict(w) for w in ref]
    have = [False] * len(ref)
    for i, v in votes.items():
        if not v:
            continue
        out[i]["startMs"] = int(statistics.median(x[0] for x in v))
        out[i]["endMs"] = int(statistics.median(x[1] for x in v))
        have[i] = True

    # words with no vote (usually the ones a fix dictionary rewrites) must be
    # interpolated between their matched neighbours, never left on their old value
    i = 0
    while i < len(out):
        if have[i]:
            i += 1; continue
        j = i
        while j < len(out) and not have[j]:
            j += 1
        lo_ms = out[i - 1]["endMs"] if i > 0 else 0
        hi_ms = out[j]["startMs"] if j < len(out) else lo_ms + 400 * (j - i)
        span = max(hi_ms - lo_ms, 60 * (j - i))
        for k in range(j - i):
            out[i + k]["startMs"] = int(round(lo_ms + span * k / (j - i)))
            out[i + k]["endMs"] = int(round(lo_ms + span * (k + 1) / (j - i)))
        i = j

    for i in range(1, len(out)):
        if out[i]["startMs"] < out[i - 1]["startMs"]:
            out[i]["startMs"] = out[i - 1]["startMs"]
        if out[i]["endMs"] < out[i]["startMs"] + 40:
            out[i]["endMs"] = out[i]["startMs"] + 40

    json.dump(out, open(a.out, "w"), indent=0)
    voted = sum(have)
    print(f"voted {voted}/{len(ref)} words; {len(ref) - voted} interpolated")
    moved = [(ref[i]['text'], out[i]['startMs'] - ref[i]['startMs'])
             for i in range(len(ref)) if abs(out[i]['startMs'] - ref[i]['startMs']) > 250]
    print(f"{len(moved)} words moved more than 250ms")
    for t, d in moved[:20]:
        print(f"   {t!r:20s} {d:+6d} ms ({round(d / 1000 * 30):+3d} frames)")
    print(f"written {a.out}")


if __name__ == "__main__":
    main()

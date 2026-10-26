#!/usr/bin/env python3
"""Word-level transcript of a take: [{"text", "startMs", "endMs"}, ...].

  python3 scripts/transcribe.py public/recordings/take.mp4 public/recordings/take.words.json
  options: --backend auto|whisper.cpp|faster-whisper   --model base.en|small|medium...   --language en   --force

Backends:
  whisper.cpp     used when built (scripts/setup-whisper.sh puts it in bin/whisper.cpp) or WHISPER_CLI is set.
                  Needs ggml-<model>.bin in bin/whisper.cpp/models (or WHISPER_MODEL=/path/to/model.bin).
  faster-whisper  `pip3 install faster-whisper`; downloads the model on first use. No compiler needed.

It refuses to overwrite an existing transcript unless --force: whisper jitters between runs, and every beat you
anchored to a word would drift. Re-time instead (the skill's scripts/retime-captions.py) if captions are off.
"""
import argparse, json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def wav16k(media, out):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", media, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", out], check=True)


def samples16k(path):
    """Mono 16 kHz float32 samples via ffmpeg. faster-whisper gets these instead of a path, because its own file
    decoding (PyAV) breaks across PyAV versions ('unexpected keyword argument metadata_errors')."""
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def find_whisper_cpp(model):
    cli = os.environ.get("WHISPER_CLI")
    if not cli:
        for c in ("bin/whisper.cpp/build/bin/whisper-cli", "bin/whisper.cpp/build/bin/Release/whisper-cli.exe", "bin/whisper.cpp/main"):
            p = os.path.join(ROOT, c)
            if os.path.exists(p):
                cli = p
                break
        cli = cli or shutil.which("whisper-cli")
    mdl = os.environ.get("WHISPER_MODEL") or os.path.join(ROOT, "bin/whisper.cpp/models", f"ggml-{model}.bin")
    return (cli, mdl) if cli and os.path.exists(mdl) else (None, None)


def run_whisper_cpp(cli, mdl, wav, language):
    with tempfile.TemporaryDirectory() as td:
        prefix = os.path.join(td, "t")
        r = subprocess.run([cli, "-m", mdl, "-f", wav, "-l", language, "-ml", "1", "-sow", "-oj", "-of", prefix, "--no-prints"],
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit(f"whisper.cpp failed:\n{r.stderr[-1500:]}")
        data = json.load(open(prefix + ".json"))["transcription"]
    return [{"text": x["text"].strip(), "startMs": int(x["offsets"]["from"]), "endMs": int(x["offsets"]["to"])}
            for x in data if x["text"].strip()]


def run_faster_whisper(wav, model, language):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("No transcriber available. Either `pip3 install faster-whisper`, or build whisper.cpp with "
                 "scripts/setup-whisper.sh.")
    m = WhisperModel(model, device="auto", compute_type="int8")
    segments, _ = m.transcribe(samples16k(wav), language=language, word_timestamps=True, vad_filter=False)
    out = []
    for seg in segments:
        for w in seg.words or []:
            t = w.word.strip()
            if t:
                out.append({"text": t, "startMs": int(round(w.start * 1000)), "endMs": int(round(w.end * 1000))})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("media"); ap.add_argument("out")
    ap.add_argument("--backend", default="auto", choices=["auto", "whisper.cpp", "faster-whisper"])
    ap.add_argument("--model", default="base.en", help="base.en (fast, English) or small (multilingual, better)")
    ap.add_argument("--language", default="en")
    ap.add_argument("--force", action="store_true", help="overwrite an existing transcript")
    a = ap.parse_args()
    if not os.path.exists(a.media):
        sys.exit(f"no such file: {a.media}")
    if os.path.exists(a.out) and not a.force:
        sys.exit(f"{a.out} already exists. Re-transcribing shifts every word; pass --force only if the take changed.")
    with tempfile.TemporaryDirectory() as td:
        wav = os.path.join(td, "a.wav")
        wav16k(a.media, wav)
        cli, mdl = find_whisper_cpp(a.model) if a.backend in ("auto", "whisper.cpp") else (None, None)
        if a.backend == "whisper.cpp" and not cli:
            sys.exit("whisper.cpp not found: run scripts/setup-whisper.sh or set WHISPER_CLI and WHISPER_MODEL")
        if cli:
            words, used = run_whisper_cpp(cli, mdl, wav, a.language), "whisper.cpp"
        else:
            words, used = run_faster_whisper(wav, a.model, a.language), "faster-whisper"
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(words, open(a.out, "w"), indent=0)
    print(f"{len(words)} words ({used}, {a.model}) -> {a.out}")


if __name__ == "__main__":
    main()

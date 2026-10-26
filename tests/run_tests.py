#!/usr/bin/env python3
"""Tests with known answers for the tools that measure things. No test framework needed:

  python3 tests/run_tests.py

Needs ffmpeg, numpy, pillow and OpenCV (pip3 install numpy pillow "opencv-python-headless<5"). Runs in a temp folder.
"""
import json, os, subprocess, sys, tempfile, traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
RE = os.path.join(ROOT, "skills", "reel-edit", "scripts")
TMP = tempfile.mkdtemp(prefix="vs-tests-")
passed, failed = [], []


def sh(*cmd, check=True, **kw):
    kw.setdefault("text", True)                     # text=False for binary output (raw frames, samples)
    r = subprocess.run(list(cmd), capture_output=True, **kw)
    if check and r.returncode:
        raise AssertionError(f"{' '.join(map(str, cmd))} exited {r.returncode}\n{r.stdout}\n{r.stderr}")
    return r


def test(fn):
    try:
        fn()
        passed.append(fn.__name__)
        print(f"  ✓ {fn.__name__}")
    except Exception:
        failed.append(fn.__name__)
        print(f"  ✗ {fn.__name__}\n" + "".join("      " + l for l in traceback.format_exc().splitlines(True)))
    return fn


@test
def detect_cuts_exact_frames():
    take = os.path.join(TMP, "take.mp4")
    sh("ffmpeg", "-v", "error", "-y",
       "-f", "lavfi", "-i", "testsrc2=s=540x960:r=30:d=3", "-f", "lavfi", "-i", "smptebars=s=540x960:r=30:d=2",
       "-f", "lavfi", "-i", "color=c=0x404040:s=540x960:r=30:d=2", "-f", "lavfi", "-i", "color=c=0x5a5a5a:s=540x960:r=30:d=2",
       "-filter_complex", "[0][1][2][3]concat=n=4:v=1:a=0[v]", "-map", "[v]", "-c:v", "libx264", "-pix_fmt", "yuv420p", take)
    sh(PY, os.path.join(RE, "detect-cuts.py"), take, "--no-sheets")
    d = json.load(open(os.path.join(TMP, "take.cuts.json")))
    assert d["cuts"] == [90, 150, 210], d["cuts"]
    assert d["frames"] == 270, d["frames"]
    assert any("not 1080x1920" in w for w in d["warnings"]), d["warnings"]


@test
def camera_check_limits():
    ok = sh(PY, os.path.join(RE, "camera-check.py"), check=False)
    assert ok.returncode == 0 and "24.0" in ok.stdout, ok.stdout          # the documented accepted move
    fast = sh(PY, os.path.join(RE, "camera-check.py"), "--keys", "0:1450:1388:800 20:1220:2385:1040", check=False)
    assert fast.returncode == 1, fast.stdout


@test
def doctor_json():
    r = sh(PY, os.path.join(ROOT, "skills", "reel-edit", "scripts", "doctor.py"), "--json", check=False,
           env={**os.environ, "VIDEO_STUDIO_HOME": os.path.join(TMP, "home")})
    d = json.loads(r.stdout)
    names = {c["name"] for c in d["checks"]}
    for must in ("ffmpeg", "Node.js 18+", "transcriber"):
        assert must in names, names
    ff = next(c for c in d["checks"] if c["name"] == "ffmpeg")
    assert ff["ok"], ff


@test
def manifests_valid_json():
    for p in (".claude-plugin/plugin.json", ".claude-plugin/marketplace.json"):
        d = json.load(open(os.path.join(ROOT, p)))
        assert d["name"] == "video-studio", d
    assert not d["plugins"][0]["name"].startswith("claude-")


@test
def every_skill_has_frontmatter():
    for name in ("reel-edit",):
        head = open(os.path.join(ROOT, "skills", name, "SKILL.md")).read().split("---")[1]
        assert f"name: {name}" in head and "description:" in head, name


@test
def measure_framing_tracks_known_face():
    try:
        import cv2, numpy as np, urllib.request
    except ImportError:
        print("    (skipped: needs opencv-python-headless<5)"); return
    src = os.path.join(TMP, "face.jpg")
    try:
        urllib.request.urlretrieve("https://raw.githubusercontent.com/opencv/opencv/4.x/samples/data/lena.jpg", src)
    except Exception:
        print("    (skipped: no network for the sample photo)"); return
    im = cv2.resize(cv2.imread(src), (700, 700))
    take = os.path.join(TMP, "face.mp4")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", "1080x1920",
                          "-r", "30", "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", take], stdin=subprocess.PIPE)
    for n in range(150):
        x, y = (190, 560 + int(40 * n / 89)) if n < 90 else (60, 820)     # shot 1 bobs 40 px; cut at f90
        fr = np.full((1920, 1080, 3), (72, 64, 58), np.uint8)
        fr[y:y + 700, x:x + 700] = im
        p.stdin.write(fr.tobytes())
    p.stdin.close(); p.wait()
    sh(PY, os.path.join(RE, "detect-cuts.py"), take, "--no-sheets")
    sh(PY, os.path.join(RE, "measure-framing.py"), take, "--out-dir", os.path.join(TMP, "framing"))
    d = json.load(open(os.path.join(TMP, "face.framing.json")))
    s1, s2 = d["shots"]
    assert s1["detected"].split("/")[0] == s1["detected"].split("/")[1], s1["detected"]
    # the face sits 130 px further left in shot 2, and shot 1's head moves ~40 px
    assert abs((s1["centreX"][0] - s2["centreX"][0]) - 130) <= 8, (s1["centreX"], s2["centreX"])
    assert 25 <= s1["headTop"][1] - s1["headTop"][0] <= 45, s1["headTop"]
    assert s2["headTop"][1] - s2["headTop"][0] <= 4, s2["headTop"]
    assert d["suggest"]["captionBaseline"] > max(s["chin"][1] for s in d["shots"])


@test
def jump_cuts_known_pauses():
    import numpy as np, wave
    sr, dur = 48000, 5.6
    t = np.arange(int(sr * dur)) / sr
    rng = np.random.default_rng(1)
    x = rng.normal(0, 0.001, len(t))
    for a, b in [(0, 1.0), (1.8, 2.4), (2.6, 3.6), (4.8, 5.3)]:     # pauses: 0.8 s, 0.2 s (keep), 1.2 s
        m = (t >= a) & (t < b); tt = t[m] - a
        x[m] += 0.25 * (0.6 + 0.4 * np.abs(np.sin(2 * np.pi * 4 * tt))) * np.sin(2 * np.pi * 180 * tt) + rng.normal(0, 0.03, m.sum())
    wav = os.path.join(TMP, "jc.wav")
    w = wave.open(wav, "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes()); w.close()
    take = os.path.join(TMP, "jc.mp4")
    sh("ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=360x640:r=30:d=5.6", "-i", wav,
       "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", take)
    words = [("so", .05, .3), ("it", 1.85, 2.05), ("cuts", 2.1, 2.35), ("um", 2.62, 2.92), ("the", 3.0, 3.2),
             ("pauses.", 3.25, 3.55), ("done.", 4.85, 5.25)]
    json.dump([{"text": a, "startMs": int(s * 1000), "endMs": int(e * 1000)} for a, s, e in words],
              open(os.path.join(TMP, "jc.words.json"), "w"))
    prev = os.path.join(TMP, "jc-prev.mp4")
    sh(PY, os.path.join(RE, "jump-cuts.py"), take, "--fillers", "--punch", "1.12", "--render", prev)
    d = json.load(open(os.path.join(TMP, "jc.jumpcuts.json")))
    pauses = [r for r in d["removed"] if r["why"] == "pause" and r["to"] - r["from"] > 8]
    assert len(pauses) == 2, d["removed"]                        # the 0.8 s and 1.2 s pauses; the 0.2 s breath stays
    assert any(r["why"].startswith("filler") for r in d["removed"]), d["removed"]
    assert abs(pauses[0]["from"] / 30 - 1.12) < 0.1 and abs(pauses[1]["to"] / 30 - 4.72) < 0.1, pauses
    cw = json.load(open(os.path.join(TMP, "jc.cut.words.json")))
    assert "um" not in [w["text"] for w in cw] and len(cw) == 6, cw
    n = sh("ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
           "stream=nb_read_frames", "-of", "csv=p=0", prev).stdout.strip()
    assert int(n) == d["outFrames"], (n, d["outFrames"])


@test
def assemble_mixed_clips():
    import numpy as np, wave
    d = os.path.join(TMP, "asm"); os.makedirs(d, exist_ok=True)
    sr, rng = 48000, np.random.default_rng(3)

    def speech(dur, spans, amp):
        t = np.arange(int(sr * dur)) / sr
        x = rng.normal(0, 0.001, len(t))
        for a, b in spans:
            m = (t >= a) & (t < b); tt = t[m] - a
            x[m] += amp * (0.6 + 0.4 * np.abs(np.sin(2 * np.pi * 4 * tt))) * np.sin(2 * np.pi * 180 * tt) + rng.normal(0, amp * .1, m.sum())
        return t, x

    def wav(name, x):
        w = wave.open(os.path.join(d, name), "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes()); w.close()

    _, xa = speech(4.0, [(0.3, 1.4), (2.2, 3.6)], 0.30); wav("a.wav", xa)                 # vertical, a 0.8 s pause
    tb, xb = speech(3.0, [(0.2, 2.6)], 0.30 * 10 ** (-18 / 20))                           # landscape, 18 dB quieter
    m = (tb >= 1.0) & (tb < 1.03); xb[m] += 0.05 * np.sin(2 * np.pi * 2000 * tb[m]); wav("b.wav", xb)  # beep at 1.00 s
    j = lambda *p: os.path.join(d, *p)
    sh("ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=540x960:r=30:d=4", "-i", j("a.wav"),
       "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", j("A.mp4"))
    sh("ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=960x540:r=25:d=3", "-i", j("b.wav"), "-filter_complex",
       "[0:v]drawbox=x=0:y=0:w=iw:h=ih:color=white:t=fill:enable='between(t,1.0,1.039)'[v]", "-map", "[v]", "-map", "1:a",
       "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", j("B.mp4"))              # flash at 1.00 s
    sh("ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "smptebars=s=360x640:r=60:d=1.5", "-c:v", "libx264",
       "-pix_fmt", "yuv420p", j("C.mov"))                                                       # 60 fps, no audio
    json.dump([{"text": "one", "startMs": 350, "endMs": 1350}, {"text": "two.", "startMs": 2250, "endMs": 3550}], open(j("A.words.json"), "w"))
    json.dump([{"text": "three", "startMs": 250, "endMs": 2500}], open(j("B.words.json"), "w"))
    sh(PY, os.path.join(RE, "assemble.py"), j("A.mp4"), j("B.mp4"), j("C.mov"), "--jumpcuts", "--punch", "1.1",
       "--fit", "blur", "--out", j("out", "reel.mp4"))

    asm = json.load(open(j("out", "reel.assembly.json"))); cuts = json.load(open(j("out", "reel.cuts.json")))
    o = j("out", "reel.mp4")
    st = json.loads(sh("ffprobe", "-v", "error", "-count_frames", "-show_entries",
                       "stream=codec_type,width,height,r_frame_rate,nb_read_frames,duration", "-of", "json", o).stdout)["streams"]
    v = next(s for s in st if s["codec_type"] == "video"); a = next(s for s in st if s["codec_type"] == "audio")
    assert (v["width"], v["height"], v["r_frame_rate"]) == (1080, 1920, "30/1"), v
    assert int(v["nb_read_frames"]) == asm["frames"], (v["nb_read_frames"], asm["frames"])
    assert abs(float(a["duration"]) - float(v["duration"])) < 1 / 30, (a["duration"], v["duration"])
    assert [x["kind"] for x in cuts["detail"]] == ["jump", "clip", "clip"], cuts["detail"]
    assert [c["fit"] for c in asm["clips"]] == ["cover", "blur", "cover"], [c["fit"] for c in asm["clips"]]
    # A/V sync across the joins: the flash frame and the beep in clip B land within a frame of each other
    seg = asm["clips"][1]["segments"][0]; lo, hi = seg["outFrom"], seg["outFrom"] + seg["frames"]
    luma = np.frombuffer(sh("ffmpeg", "-v", "error", "-i", o, "-vf", "scale=27:48", "-f", "rawvideo", "-pix_fmt", "gray",
                            "-", text=False).stdout, np.uint8).reshape(-1, 48, 27).mean(axis=(1, 2))
    flash = lo + int(np.argmax(luma[lo:hi]))
    au = np.frombuffer(sh("ffmpeg", "-v", "error", "-i", o, "-ac", "1", "-ar", "48000", "-f", "f32le", "-", text=False).stdout, np.float32)
    hop, f = 480, np.fft.rfftfreq(480, 1 / 48000)
    band = [np.abs(np.fft.rfft(au[i:i + hop] * np.hanning(hop))) for i in range(0, len(au) - hop, hop)]
    beep = int(np.argmax([b[(f > 1800) & (f < 2200)].sum() / (b.sum() + 1e-9) for b in band])) * hop / 48000
    assert abs(beep - flash / 30) <= 1 / 30 + 0.012, (beep, flash / 30)
    # loudness matched: inputs 18 dB apart, outputs within 1.5 dB
    db = lambda x: 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)
    A = np.concatenate([au[int(s["outFrom"] * 1600):int((s["outFrom"] + s["frames"]) * 1600)] for s in asm["clips"][0]["segments"]])
    assert abs(db(A) - db(au[lo * 1600:hi * 1600])) < 1.5, (db(A), db(au[lo * 1600:hi * 1600]))
    w = json.load(open(j("out", "reel.words.json")))
    assert [x["text"] for x in w] == ["one", "two.", "three"], w
    assert abs(w[2]["startMs"] - (lo / 30 + 0.25 - asm["clips"][1]["segments"][0]["from"]) * 1000) <= 2, w[2]


@test
def assemble_takes_a_folder():
    import importlib.util
    d = os.path.join(TMP, "folder-in"); os.makedirs(os.path.join(d, "sub"), exist_ok=True)
    for f in ("b_take2.MOV", "a_take1.mp4", "c.MKV", "notes.txt", ".hidden.mp4", "sub/x.mp4", "music.wav", "reel.mp4"):
        open(os.path.join(d, f), "w").close()
    spec = importlib.util.spec_from_file_location("assemble", os.path.join(RE, "assemble.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    got = [os.path.basename(p) for p in m.expand_inputs([d], out=os.path.join(d, "reel.mp4"))]
    assert got == ["a_take1.mp4", "b_take2.MOV", "c.MKV"], got           # videos directly inside, by name
    mixed = m.expand_inputs([os.path.join(d, "c.MKV"), d], out=None)    # a file, then its folder: no duplicates
    assert [os.path.basename(p) for p in mixed] == ["c.MKV", "a_take1.mp4", "b_take2.MOV", "reel.mp4"], mixed


@test
def run_sh_parses_and_helps():
    if os.name == "nt":
        return
    rs = os.path.join(ROOT, "skills", "reel-edit", "assets", "reel-project", "run.sh")
    sh("bash", "-n", rs)
    out = sh("bash", rs).stdout
    for cmd in ("setup", "transcribe", "cuts", "render", "check", "doctor"):
        assert f"bash run.sh {cmd}" in out, cmd
    bad = sh("bash", rs, "render", check=False)
    assert bad.returncode == 2 and "usage" in bad.stdout


@test
def windows_launchers():
    proj = os.path.join(ROOT, "skills", "reel-edit", "assets", "reel-project")
    for n in ("setup.cmd", "run.cmd"):
        raw = open(os.path.join(proj, n), "rb").read()
        assert raw.count(b"\n") == raw.count(b"\r\n"), f"{n} needs CRLF line endings"
    assert b"run.cmd\" setup" in open(os.path.join(proj, "setup.cmd"), "rb").read()
    assert b"run.sh %*" in open(os.path.join(proj, "run.cmd"), "rb").read()


@test
def app_mode_doc_linked_from_the_skill():
    assert "app-mode.md" in open(os.path.join(ROOT, "skills", "reel-edit", "SKILL.md")).read()
    assert os.path.exists(os.path.join(ROOT, "skills", "reel-edit", "references", "app-mode.md"))


@test
def skills_are_self_contained():
    """In the Claude app only the loaded skill's folder is available: no skill may reach outside itself except by
    naming another skill, and the copies that make that possible must match their source."""
    import re
    r = sh(PY, os.path.join(ROOT, "tools", "sync.py"), "--check", check=False)
    assert r.returncode == 0, r.stdout
    bad = []
    for dirpath, _, files in os.walk(os.path.join(ROOT, "skills")):
        for f in files:
            if f.endswith((".md", ".py", ".sh", ".mjs")):
                p = os.path.join(dirpath, f)
                txt = open(p, encoding="utf-8", errors="ignore").read()
                for m in re.finditer(r"<skill>|\.\./\.\./(shared|templates)|ROOT, \"(shared|templates)\"", txt):
                    bad.append(f"{os.path.relpath(p, ROOT)}: {m.group(0)}")
    assert not bad, bad
    for gone in ("shared", "templates"):
        assert not os.path.exists(os.path.join(ROOT, gone)), f"{gone}/ at the plugin root isn't available in chat"


print(f"\n{len(passed)} passed, {len(failed)} failed  ({TMP})")
sys.exit(1 if failed else 0)

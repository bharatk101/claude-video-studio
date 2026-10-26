#!/usr/bin/env python3
"""Video Studio doctor: checks everything the skills need and prints the fix for anything missing.
Lives in the reel-edit skill (python3 ${CLAUDE_SKILL_DIR}/scripts/doctor.py) and in every reel project (bash run.sh doctor).

  python3 doctor.py                 everything (Remotion + whisper for reel editing)
  python3 doctor.py --project DIR   also check a reel project (venv, node_modules, transcriber, brand sheet, recordings)
                                    (inside a project: bash run.sh doctor)
  python3 doctor.py --fix           install what can be installed safely (Python packages)
  python3 doctor.py --json          machine-readable result

Exit code 0 when every required check passes; optional ones only warn. Never prints API key values.
"""
import argparse, importlib.util, json, os, platform, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OS = {"Darwin": "mac", "Linux": "linux", "Windows": "windows"}.get(platform.system(), "linux")
TTY = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
C = (lambda c, s: f"\033[{c}m{s}\033[0m") if TTY else (lambda c, s: s)

results = []


def install_hint(pkg):
    """System package install command per OS."""
    table = {
        "ffmpeg": {"mac": "brew install ffmpeg", "linux": "sudo apt install ffmpeg  (or your distro's package)", "windows": "winget install Gyan.FFmpeg"},
        "node": {"mac": "brew install node", "linux": "https://nodejs.org (LTS) or: sudo apt install nodejs npm", "windows": "winget install OpenJS.NodeJS.LTS"},
        "cmake": {"mac": "brew install cmake", "linux": "sudo apt install cmake build-essential", "windows": "winget install Kitware.CMake"},
        "python": {"mac": "brew install python", "linux": "sudo apt install python3 python3-pip", "windows": "winget install Python.Python.3.12"},
    }
    return table[pkg][OS]


def add(group, name, ok, detail="", fix="", required=True):
    results.append({"group": group, "name": name, "ok": bool(ok), "required": required, "detail": detail, "fix": fix})


def version_of(cmd, args=("-version",), pat=r"(\d+\.\d+(?:\.\d+)?)"):
    try:
        out = subprocess.run([cmd, *args], capture_output=True, text=True, timeout=20)
        m = re.search(pat, out.stdout + out.stderr)
        return m.group(1) if m else "?"
    except Exception:
        return None


def has_module(name):
    return importlib.util.find_spec(name) is not None


def pip_cmd(pkgs):
    extra = " --break-system-packages" if OS == "linux" and not os.environ.get("VIRTUAL_ENV") else ""
    return f"{sys.executable} -m pip install {' '.join(pkgs)}{extra}"


# ---------- checks ----------
def check_common():
    v = sys.version_info
    add("common", "Python 3.9+", v >= (3, 9), f"{v.major}.{v.minor}", install_hint("python"))
    for exe in ("ffmpeg", "ffprobe"):
        p = shutil.which(exe)
        add("common", exe, p, version_of(exe) if p else "not found", install_hint("ffmpeg"))
    node = shutil.which("node")
    nv = version_of("node", ("--version",), r"v(\d+)") if node else None
    add("common", "Node.js 18+", node and nv and nv.isdigit() and int(nv) >= 18, f"v{nv}" if nv else "not found", install_hint("node"))
    add("common", "npm", shutil.which("npm"), "", install_hint("node"))
    add("common", "numpy", has_module("numpy"), "", pip_cmd(["numpy"]))


def check_reel(project, fix):
    # inside a reel project, `bash run.sh setup` installs everything; point there instead of at pip
    setup = "bash run.sh setup" if project else None
    if project:
        add("reel", "project Python (.venv)", os.path.exists(os.path.join(project, ".venv")) or bool(os.environ.get("VIRTUAL_ENV")),
            "", setup)
    add("reel", "Pillow", has_module("PIL"), "measurement scripts", setup or pip_cmd(["pillow"]))
    cv_ok = has_module("cv2")
    if cv_ok:
        import cv2
        cv_ok = os.path.exists(os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml"))
    add("reel", "OpenCV 4 (framing)", cv_ok, "measure-framing.py",
        setup or pip_cmd(['"opencv-python-headless<5"']), required=False)
    fw = has_module("faster_whisper")
    wc = None
    if project:
        b = os.path.join(project, "bin", "whisper.cpp", "build", "bin")
        wc = next((p for p in (os.path.join(b, "whisper-cli"), os.path.join(b, "Release", "whisper-cli.exe"),
                               os.path.join(b, "whisper-cli.exe")) if os.path.exists(p)), None)
    wc = wc or os.environ.get("WHISPER_CLI") or shutil.which("whisper-cli")
    add("reel", "transcriber", fw or wc, ("whisper.cpp" if wc else "") + (" + " if wc and fw else "") + ("faster-whisper" if fw else "") or "none",
        setup or (pip_cmd(["faster-whisper"]) + "   (or, in a reel project: bash run.sh setup)"))
    add("reel", "cmake (only to build whisper.cpp)", shutil.which("cmake"), "", install_hint("cmake"), required=False)
    if project:
        nm = os.path.join(project, "node_modules", "remotion", "package.json")
        rv = json.load(open(nm))["version"] if os.path.exists(nm) else None
        add("reel", "project dependencies", rv, f"remotion {rv}" if rv else "not installed", setup)
        fonts = os.path.exists(os.path.join(project, "node_modules", "@fontsource", "inter"))
        add("reel", "bundled Inter font", fonts, "", setup, required=False)
        brand = os.path.join(project, "brand", "BRAND.md")
        filled = os.path.exists(brand) and "<!-- hex -->" not in open(brand).read()
        add("reel", "brand sheet filled in", filled, brand if os.path.exists(brand) else "missing",
            "ask Claude: \"set up my brand sheet\" (from your website or a past video)", required=False)
        rec = os.path.join(project, "public", "recordings")
        n = len([f for f in os.listdir(rec) if not f.startswith(".") and os.path.isfile(os.path.join(rec, f))]) if os.path.isdir(rec) else 0
        add("reel", "recordings", True, f"{n} file(s) in public/recordings", "", required=False)


def run_fixes():
    missing = sorted({r["fix"].split("install ", 1)[1].split()[0] for r in results
                      if not r["ok"] and r["fix"].startswith(sys.executable)})
    if missing:
        print(C("1", f"\ninstalling Python packages: {' '.join(missing)}"))
        subprocess.run(pip_cmd(missing), shell=True)
        return True
    return False


def report(as_json):
    if as_json:
        print(json.dumps({"os": OS, "checks": results}, indent=1))
        return
    print(C("1", f"Video Studio doctor  ({platform.system()} {platform.machine()})"))
    group = None
    for r in results:
        if r["group"] != group:
            group = r["group"]
            print(C("1", f"\n{ {'common': 'Everything', 'reel': 'Reel editing'}[group] }"))
        mark = C("32", "✓") if r["ok"] else (C("31", "✗") if r["required"] else C("33", "·"))
        print(f"  {mark} {r['name']:<34} {C('2', r['detail'])}")
    bad = [r for r in results if not r["ok"] and r["required"]]
    opt = [r for r in results if not r["ok"] and not r["required"] and not r["name"].endswith("_KEY")]
    if bad:
        print(C("1", "\nTo fix (required):"))
        for f in dict.fromkeys(r["fix"] for r in bad):
            print(f"  {f}")
    if opt:
        print(C("1", "\nOptional:"))
        for r in opt:
            print(f"  {r['name']}: {r['fix']}")
    print("\n" + (C("32", "Ready.") if not bad else C("31", f"{len(bad)} required item(s) missing.")))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", nargs="?", default="all", choices=["all", "reel"])
    ap.add_argument("--project", help="a reel project folder to check too")
    ap.add_argument("--fix", action="store_true", help="install Python packages and the render engine")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    project = os.path.abspath(a.project) if a.project else None

    def run():
        results.clear()
        check_common()
        if a.what in ("all", "reel"):
            check_reel(project, a.fix)

    run()
    if a.fix and run_fixes():
        run()
    report(a.json)
    return 1 if any(not r["ok"] and r["required"] for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())

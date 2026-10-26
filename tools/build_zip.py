#!/usr/bin/env python3
"""Build dist/video-studio.zip: the plugin, ready for Customize > Plugins > Add > Upload plugin in the Claude app.

  python3 tools/build_zip.py            -> dist/video-studio.zip (and checks it)

The archive holds one top-level folder, video-studio/, with .claude-plugin/plugin.json, the skills, README,
LICENSE and CHANGELOG. Development files (tests, CI, tools, the marketplace listing) are left out. It fails if the
copies are out of sync, if there's a top-level bin/ (the app refuses those), or if the plugin breaks the app's
limits (5,000 files, 200 MB).
"""
import json, os, subprocess, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INCLUDE = [".claude-plugin/plugin.json", ".claude-plugin/icon.png", "skills", "docs", "README.md", "LICENSE", "CHANGELOG.md"]
SKIP_DIRS = {"__pycache__", "node_modules", ".git", "out", ".venv", "bin"}
SKIP_FILES = {".DS_Store", ".env"}
MAX_FILES, MAX_BYTES = 5000, 200 * 1024 * 1024


def files():
    for item in INCLUDE:
        p = os.path.join(ROOT, item)
        if os.path.isfile(p):
            yield item
            continue
        for dirpath, dirs, names in os.walk(p):
            # keep the starter project's empty out/ placeholder, skip build output everywhere else
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS or (d == "out" and "reel-project" in dirpath)]
            for n in names:
                if n not in SKIP_FILES and not n.endswith(".pyc"):
                    yield os.path.relpath(os.path.join(dirpath, n), ROOT)


def main():
    if subprocess.run([sys.executable, os.path.join(ROOT, "tools", "sync.py"), "--check"]).returncode:
        sys.exit("copies out of sync: run python3 tools/sync.py first")
    if os.path.isdir(os.path.join(ROOT, "bin")):
        sys.exit("a top-level bin/ stops the Claude app from installing the plugin")
    version = json.load(open(os.path.join(ROOT, ".claude-plugin", "plugin.json")))["version"]
    out = os.path.join(ROOT, "dist", "video-studio.zip")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    names = sorted(set(files()))
    size = sum(os.path.getsize(os.path.join(ROOT, n)) for n in names)
    if len(names) > MAX_FILES or size > MAX_BYTES:
        sys.exit(f"too big for the Claude app: {len(names)} files, {size / 1e6:.1f} MB")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for n in names:
            z.write(os.path.join(ROOT, n), os.path.join("video-studio", n))
    with zipfile.ZipFile(out) as z:
        manifests = [n for n in z.namelist() if n.endswith(".claude-plugin/plugin.json")]
        assert manifests == ["video-studio/.claude-plugin/plugin.json"], manifests
        skills = sorted({n.split("/")[2] for n in z.namelist() if n.startswith("video-studio/skills/") and n.endswith("/SKILL.md")
                         and n.count("/") == 3})
    print(f"video-studio {version}: {len(names)} files, {size / 1e6:.1f} MB, skills {', '.join(skills)} -> {os.path.relpath(out, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Keep the copies that make every skill self-contained in step with their source.

In the Claude app, only a skill's own folder is copied into Claude's sandbox, so a skill can't reach files in
another skill or at the plugin root. The few files more than one skill needs therefore live in each of them.
This script copies each source over its copies.

  python3 tools/sync.py           update the copies
  python3 tools/sync.py --check   exit 1 and list what's out of date (tests and CI run this)
"""
import filecmp, os, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RE = "skills/reel-edit"
TEMPLATE = f"{RE}/assets/reel-project"

COPIES = {f"{RE}/scripts/doctor.py": [f"{TEMPLATE}/scripts/doctor.py"]}      # one checker: run.sh doctor runs it
for s in ("assemble.py", "detect-cuts.py", "jump-cuts.py", "measure-framing.py"):
    COPIES[f"{RE}/scripts/{s}"] = [f"{TEMPLATE}/scripts/{s}"]                 # run.sh runs these in the project
for c in ("Caption.tsx", "TextHook.tsx", "TwoThirdsPanel.tsx", "Silhouette.tsx", "JumpCut.tsx", "fonts.ts"):
    COPIES[f"{RE}/components/{c}"] = [f"{TEMPLATE}/src/shared/{c}"]          # the starter's src/shared


def main():
    check = "--check" in sys.argv
    stale = []
    for src, dsts in COPIES.items():
        s = os.path.join(ROOT, src)
        for dst in dsts:
            d = os.path.join(ROOT, dst)
            if os.path.exists(d) and filecmp.cmp(s, d, shallow=False):
                continue
            stale.append(dst)
            if not check:
                os.makedirs(os.path.dirname(d), exist_ok=True)
                shutil.copyfile(s, d)
                shutil.copymode(s, d)
    if check:
        if stale:
            print("out of date (run python3 tools/sync.py):\n  " + "\n  ".join(stale))
            return 1
        print(f"all {sum(len(v) for v in COPIES.values())} copies in sync")
        return 0
    print(f"updated {len(stale)} cop{'y' if len(stale) == 1 else 'ies'}" + (":\n  " + "\n  ".join(stale) if stale else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())

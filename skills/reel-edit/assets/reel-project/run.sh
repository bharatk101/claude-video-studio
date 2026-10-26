#!/usr/bin/env bash
# Everything that has to run on your own computer, as one short command each.
# Claude (in the Claude app or Claude Code) writes the edit; you paste one of these into Terminal when asked.
# macOS and Linux: Terminal. Windows: Git Bash (comes with Git for Windows) or WSL.
#
#   bash run.sh setup                          once per machine/project: tools, packages, whisper + model, self-test
#   bash run.sh assemble <clips...> --out <take.mp4> [--jumpcuts]   several clips -> one take (+ cuts, words)
#   bash run.sh transcribe <take.mp4>          word-level transcript -> <take>.words.json
#   bash run.sh cuts <take.mp4>                cuts in frames + contact sheets -> <take>.cuts.json
#   bash run.sh framing <take.mp4>             head top, eyes, mouth, chin per shot -> <take>.framing.json
#   bash run.sh jumpcuts <take.mp4> [--fillers] cut pauses (and um/uh) -> <take>.jumpcuts.json + preview mp4
#   bash run.sh render <Composition> [out.mp4] final render (default out/<Composition>.mp4)
#   bash run.sh check <Composition> <from-to>  review frames as JPEGs in out/check/
#   bash run.sh studio                         open the Remotion preview in your browser
#   bash run.sh doctor                         what's installed, what's missing
#
# Each step prints "ok" or "FAIL: <reason>". If something fails, paste the output back to Claude.
set -uo pipefail
cd "$(dirname "$0")"
ROOT=$(pwd)
OS=$(uname -s)
case "$OS" in MINGW*|MSYS*|CYGWIN*) OS=Windows ;; esac
FAILS=0

say_step() { printf "  %-44s" "$1"; }
ok() { echo "ok${1:+  ($1)}"; }
fail() { echo "FAIL: $1"; FAILS=$((FAILS + 1)); }
have() { command -v "$1" >/dev/null 2>&1; }

base_python() {   # python3 on macOS/Linux; on Windows often only "python" (and python3 may be a Store stub)
  local c
  for c in python3 python; do
    if have "$c" && "$c" -c 'import sys; sys.exit(sys.version_info < (3, 9))' >/dev/null 2>&1; then echo "$c"; return 0; fi
  done
  return 1
}
venv_python() {   # the venv's python: .venv/bin/python, or .venv/Scripts/python.exe on Windows
  local p
  for p in "$ROOT/.venv/bin/python" "$ROOT/.venv/Scripts/python.exe"; do [ -x "$p" ] && { echo "$p"; return 0; }; done
  return 1
}
py() {   # the project's own Python (a venv, so it never fights the system Python)
  local v; v=$(venv_python) || v=$(base_python) || { echo "FAIL: no Python 3 found (run: bash run.sh setup)"; return 1; }
  "$v" "$@"
}
hint() {   # $1 = macOS, $2 = Linux, $3 = Windows
  case "$OS" in Darwin) echo "$1" ;; Windows) echo "$3" ;; *) echo "$2" ;; esac
}
WHISPER_BIN=bin/whisper.cpp/build/bin
whisper_cli() {
  local p
  for p in "$WHISPER_BIN/whisper-cli" "$WHISPER_BIN/Release/whisper-cli.exe" "$WHISPER_BIN/whisper-cli.exe"; do
    [ -x "$p" ] && { echo "$p"; return 0; }
  done
  return 1
}

need_brew_pkg() {   # $1 = command, $2 = brew package
  if have "$1"; then return 0; fi
  if [ "$OS" = "Darwin" ] && have brew; then brew install "$2" >/dev/null 2>&1 && have "$1" && return 0; fi
  return 1
}

setup() {
  echo "Setting up $(basename "$ROOT") (5-10 minutes the first time)"

  say_step "ffmpeg"
  if need_brew_pkg ffmpeg ffmpeg; then ok "$(ffmpeg -version | head -1 | awk '{print $3}')"
  else fail "install it: $(hint 'brew install ffmpeg' 'sudo apt install ffmpeg' 'winget install Gyan.FFmpeg, then reopen Git Bash')"; fi

  say_step "Node.js 18+"
  if have node && [ "$(node -p 'process.versions.node.split(".")[0]')" -ge 18 ]; then ok "$(node -v)"
  else fail "install Node 18+: $(hint 'brew install node' 'https://nodejs.org (or your package manager)' 'winget install OpenJS.NodeJS.LTS, then reopen Git Bash')"; fi

  say_step "npm packages (Remotion)"
  if [ -d node_modules/remotion ] || npm install --no-audit --no-fund --loglevel=error >/tmp/vs-npm.log 2>&1; then
    ok "remotion $(node -p 'require("./node_modules/remotion/package.json").version' 2>/dev/null)"
  else fail "npm install failed, see /tmp/vs-npm.log"; fi

  say_step "Remotion's headless browser"
  if npx remotion browser ensure >/tmp/vs-browser.log 2>&1; then ok
  else fail "could not download it, see /tmp/vs-browser.log (renders can use --browser-executable=<Chrome>)"; fi

  say_step "Python 3 + venv (numpy, pillow, opencv)"
  local bp vp
  if bp=$(base_python) && { vp=$(venv_python) || { "$bp" -m venv .venv >/dev/null 2>&1 && vp=$(venv_python); }; } \
     && "$vp" -m pip install -q --disable-pip-version-check numpy pillow "opencv-python-headless<5" >/tmp/vs-pip.log 2>&1; then ok
  else fail "need Python 3.9+ with venv: $(hint 'brew install python' 'sudo apt install python3-venv' 'winget install Python.Python.3.12, then reopen Git Bash'), see /tmp/vs-pip.log"; fi

  # Speech to text: whisper.cpp (most accurate timings). Windows without a C++ compiler, or any failed build,
  # falls back to faster-whisper in the venv, so setup still finishes.
  say_step "cmake (to build whisper.cpp)"
  local have_cmake=1
  if need_brew_pkg cmake cmake; then ok
  elif [ "$OS" = "Windows" ]; then have_cmake=0; ok "not found, using faster-whisper instead"
  else fail "install it: $(hint 'brew install cmake' 'sudo apt install cmake build-essential' '')"; fi

  say_step "speech to text (whisper)"
  if whisper_cli >/dev/null && [ -f bin/whisper.cpp/models/ggml-base.en.bin ]; then ok "whisper.cpp, already built"
  elif [ "$have_cmake" = 1 ] && MODELS="${MODELS:-base.en}" bash scripts/setup-whisper.sh >/tmp/vs-whisper.log 2>&1; then ok "whisper.cpp + base.en"
  elif py -m pip install -q --disable-pip-version-check faster-whisper >>/tmp/vs-pip.log 2>&1; then
    ok "faster-whisper (whisper.cpp $( [ "$have_cmake" = 1 ] && echo "build failed, see /tmp/vs-whisper.log" || echo "skipped"))"
  else fail "whisper.cpp and faster-whisper both failed, see /tmp/vs-whisper.log and /tmp/vs-pip.log"; fi

  say_step "transcription self-test"
  local sample=bin/whisper.cpp/samples/jfk.wav out
  if [ ! -f "$sample" ]; then   # no whisper.cpp checkout (faster-whisper only): fetch just the sample
    mkdir -p "$(dirname "$sample")"
    curl -fsSL -o "$sample" https://raw.githubusercontent.com/ggml-org/whisper.cpp/master/samples/jfk.wav 2>/dev/null || rm -f "$sample"
  fi
  if [ -f "$sample" ]; then
    out=$(mktemp -d)/jfk.words.json
    if py scripts/transcribe.py "$sample" "$out" >/dev/null 2>&1; then
      ok "heard: $(py -c "import json,sys; print(' '.join(w['text'] for w in json.load(open(sys.argv[1]))[:6]))" "$out")..."
    else fail "transcribe.py could not read the sample"; fi
  else fail "could not get the test sample (no internet?); try: bash run.sh transcribe <your clip>"; fi

  mkdir -p "public/recordings" "public/screen-recordings" "public/images" "public/music pack" "public/sound pack" out brand
  echo
  if [ "$FAILS" -eq 0 ]; then
    echo "All set. Put a recording in public/recordings/ and tell Claude the edit you want."
  else
    echo "$FAILS step(s) failed. Paste this output to Claude, or fix them and run: bash run.sh setup"
    return 1
  fi
}

assemble() {
  [ $# -ge 1 ] || { echo "usage: bash run.sh assemble public/recordings/raw/*.MOV --out public/recordings/reel.mp4 [--jumpcuts] [--fillers] [--order time]"; return 2; }
  py scripts/assemble.py "$@"
}

transcribe() {
  [ $# -ge 1 ] || { echo "usage: bash run.sh transcribe public/recordings/take.mp4 [--force]"; return 2; }
  local take="$1"; shift
  py scripts/transcribe.py "$take" "${take%.*}.words.json" "$@"
}

cuts() {
  [ $# -ge 1 ] || { echo "usage: bash run.sh cuts public/recordings/take.mp4"; return 2; }
  local take="$1"; shift
  py scripts/detect-cuts.py "$take" --out-dir "out/measure/$(basename "${take%.*}")" "$@"
}

framing() {
  [ $# -ge 1 ] || { echo "usage: bash run.sh framing public/recordings/take.mp4"; return 2; }
  local take="$1"; shift
  py scripts/measure-framing.py "$take" --out-dir "out/measure/$(basename "${take%.*}")" "$@"
}

jumpcuts() {
  [ $# -ge 1 ] || { echo "usage: bash run.sh jumpcuts public/recordings/take.mp4 [--fillers] [--punch 1.12]"; return 2; }
  local take="$1"; shift
  py scripts/jump-cuts.py "$take" --render "out/$(basename "${take%.*}")-jumpcut-preview.mp4" "$@"
}

render() {
  [ $# -ge 1 ] || { echo "usage: bash run.sh render <Composition> [out/name.mp4]"; return 2; }
  local comp="$1" out="out/$1.mp4"
  shift
  if [ $# -ge 1 ] && [ "${1#--}" = "$1" ]; then out="$1"; shift; fi   # optional output path; flags pass through
  mkdir -p "$(dirname "$out")"
  local start=$SECONDS
  if npx remotion render src/index.ts "$comp" "$out" --codec=h264 --crf=17 --concurrency=75% --log=error "$@"; then
    echo "done: $out ($((SECONDS - start)) s)"
    case "$OS" in Darwin) open -R "$out" 2>/dev/null ;; Windows) explorer.exe /select,"$(cygpath -w "$out" 2>/dev/null || echo "$out")" >/dev/null 2>&1 ;; esac
    true
  else
    echo "FAIL: render of $comp did not finish. Paste the output above to Claude."; return 1
  fi
}

check() {
  [ $# -ge 2 ] || { echo "usage: bash run.sh check <Composition> <from>-<to>"; return 2; }
  rm -rf out/check && mkdir -p out/check
  npx remotion render src/index.ts "$1" out/check --sequence --frames="$2" --concurrency=75% --log=error \
    && echo "frames in out/check/"
}

doctor() {   # read-only: the same checker the skills use (scripts/doctor.py), scoped to this project
  py scripts/doctor.py reel --project "$ROOT"
}

case "${1:-help}" in
  setup) setup ;;
  assemble) shift; assemble "$@" ;;
  transcribe) shift; transcribe "$@" ;;
  cuts) shift; cuts "$@" ;;
  framing) shift; framing "$@" ;;
  jumpcuts) shift; jumpcuts "$@" ;;
  render) shift; render "$@" ;;
  check) shift; check "$@" ;;
  studio) npx remotion studio src/index.ts ;;
  doctor) doctor ;;
  *) sed -n '2,18p' "$ROOT/$(basename "$0")" | sed 's/^# \{0,1\}//' ;;
esac

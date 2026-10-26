# Video Studio guide

The details behind the [README](../README.md): everything it can do, the commands Claude runs for you, where it
works, setting up by hand, and how the repo is built. You don't need any of this to use Video Studio; Claude reads
the skills and does it.

- [Everything it can do](#everything-it-can-do)
- [The commands Claude runs](#the-commands-claude-runs)
- [Where it works](#where-it-works)
- [Setting up by hand](#setting-up-by-hand)
- [How it's built](#how-its-built)
- [Known limits](#known-limits)

## Everything it can do

- **Several clips into one video.** Any mix of phone `.MOV`, `.mp4`, vertical or landscape, any frame rate: turned
  upright, sized to 1080×1920, matched in loudness and joined in order. Landscape clips are cropped around your
  face (or fitted over a blurred copy when there's no face).
- **Jump cuts:** pauses, and if you like every "um" and "uh", removed automatically, never mid-word, with an
  optional punch-in on every other cut. Captions follow the edited timeline.
- **Captions that land on the word:** 1–3 word chunks in the TikTok outlined style, never held through pauses,
  never across a cut, black-on-white automatically over light backgrounds. If they drift, a re-timing pass votes
  word times across overlapping windows to fix them.
- **Measured, not guessed:** your cuts are found to the frame, and your head top, eye line, mouth and chin in
  every shot, so captions and hooks are placed against *your* footage and the Instagram 4:5 safe band.
- **Text hooks** in Instagram's native style (one outline round all lines), widths measured from a render.
- **Five layouts:** talking head, 50/50 split (made from a full-frame take in code), full-screen graphic,
  two-thirds panel, and full screen with a cut-out of you.
- **Screen recordings** with Screen Studio-style zooms and pans, checked for jerky moves before rendering.
- **Music and sound effects**, trimmed in code from your original files and *verified in the final render* by
  subtracting your voice and measuring what's left.
- **Storyboard review page:** a clip per beat with Keep / Maybe / Drop and notes, for round-by-round feedback.
- **Your look, every video:** a brand sheet (`brand/BRAND.md`) for colours, type, captions and hooks, which
  Claude can fill in from your website's styles or a past video.
- **Optional extras:** graphics behind your head (person matte), shader transitions, 3D and hand-drawn
  annotations through HyperFrames.

## The commands Claude runs

A reel project has one entry point, `run.sh`. Claude runs these for you (or, from the Claude app, hands you the
one line that has to run on your computer); they're listed here so you know what's happening.

| Command | What it does |
| --- | --- |
| `bash run.sh setup` | once: ffmpeg, npm packages, whisper.cpp + model, Remotion's browser, a self-test (Windows: double-click `setup.cmd`) |
| `bash run.sh assemble raw/*.MOV --out public/recordings/reel.mp4 --jumpcuts` | several clips joined into one take, pauses cut |
| `bash run.sh assemble public/recordings/coffee-reel --order time --out ...` | every video in a folder, in recording order |
| `bash run.sh transcribe public/recordings/take.mp4` | word-level transcript next to the take |
| `bash run.sh cuts public/recordings/take.mp4` | cuts in frames + contact sheets |
| `bash run.sh framing public/recordings/take.mp4` | head top, eye line, mouth, chin per shot + caption/hook suggestions |
| `bash run.sh jumpcuts public/recordings/take.mp4 --fillers` | cut pauses and ums, plus a preview mp4 |
| `bash run.sh check <Composition> <from>-<to>` | review frames as JPEGs |
| `bash run.sh render <Composition>` | the final mp4 in `out/` |
| `bash run.sh doctor` | what's installed, what's missing |

Every step prints `ok` or `FAIL: <reason>`. To start a project by hand:
`cp -r <plugin>/skills/reel-edit/assets/reel-project my-reels && cd my-reels && bash run.sh setup`.

## Where it works

| | Claude Code / desktop local session | Claude app with a linked folder | Claude app, no folder |
| --- | --- | --- | --- |
| How | Claude runs everything on your machine | Claude edits files in your linked folder and renders in its cloud workspace | You attach files, Claude sends the video back |
| Your Terminal | not needed | `bash run.sh setup` once, `bash run.sh transcribe` per take | not needed |
| Join clips, jump cuts | ✓ | ✓ | ✓ (attach the clips) |
| Reel editing with captions | ✓ | ✓ | ✓ with a transcript (made on your computer: `run.sh transcribe`) |

**From the Claude app:** link your project folder (the **+** menu next to the message box, **Add folder**) and ask
as usual. Claude builds and renders in the cloud and saves the results into your folder. When something has to
run on your computer, it gives you one line to paste into Terminal, such as
`cd ~/Movies/reels && bash run.sh setup`.

## Setting up by hand

`bash run.sh setup` does all of this; here's what it needs if you'd rather install things yourself.

- **ffmpeg**: `brew install ffmpeg` · `sudo apt install ffmpeg` · `winget install Gyan.FFmpeg`
- **Node.js 18+**: `brew install node` · [nodejs.org](https://nodejs.org) · `winget install OpenJS.NodeJS.LTS`
- **Python 3.9+** with `pip`; packages: `pip3 install numpy pillow "opencv-python-headless<5" faster-whisper`
- **cmake**, only to build whisper.cpp (`brew install cmake` · `sudo apt install cmake build-essential`)

To check an install, ask Claude **"check my Video Studio setup"**, run `bash run.sh doctor` in a reel project, or
from a clone of this repo:

```bash
python3 skills/reel-edit/scripts/doctor.py          # add --fix to install the Python packages
```

Everything a project needs is installed inside it (`node_modules/`, `.venv/`, `bin/whisper.cpp`), never inside the
plugin folder.

## How it's built

```
claude-video-studio/
├── .claude-plugin/          plugin + marketplace manifests, icon
├── .github/workflows/       CI (tests, renders and a real transcription on macOS, Linux, Windows); releases
├── skills/reel-edit/        the skill: SKILL.md, references/, components/, scripts/ (incl. doctor.py, the setup
│                            checker), assets/reel-project (the starter project)
├── tests/run_tests.py       tests with known answers (cuts, framing, jump cuts, joining clips, camera, doctor,
│                            run.sh, self-contained skill)
├── tools/                   sync.py (keeps the starter project's copies in step), build_zip.py (the release zip)
└── docs/                    this guide and the README's images
```

The skill is self-contained, because the Claude app copies only the loaded skill's folder into its sandbox. The
starter project carries copies of the skill's scripts and components; `tools/sync.py` keeps them identical and the
tests fail when one drifts.

## Known limits

- Remotion is free for individuals and small companies; larger companies need a
  [company licence](https://www.remotion.dev/license) to use the reel workflow.
- The first transcription downloads a whisper model (~150 MB for `base.en`); the first Remotion render downloads a
  headless Chrome. Both need the internet once.
- In the Claude app the plugin needs code execution (**Settings > Capabilities > Create and edit files**). Chat's
  sandbox usually can't download a speech model, so captions from your own voice are transcribed on your computer.
- Uploads from a linked folder are capped at about 400 MB per file: long 4K clips are better recorded at 1080p, or
  assembled on your computer with `bash run.sh assemble`.
- `run.sh` is a bash script. On Windows, double-click `setup.cmd`, or use `.\run.cmd <command>` from PowerShell:
  both run it in Git Bash (installed for you with winget if missing). Without Visual Studio Build Tools, setup uses
  faster-whisper instead of building whisper.cpp. See [prompts](prompts.md#set-up-a-project) for paths per OS.

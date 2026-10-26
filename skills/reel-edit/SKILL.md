---
name: reel-edit
description: Video Studio's reel editor. Edits vertical short-form reels (1080x1920 @ 30fps) end to end with Remotion, ffmpeg and whisper: joins several clips into one take, cuts pauses and filler words (jump cuts), measures cuts and framing, places frame-exact captions, hooks and motion graphics against the speaker's own words, cuts in screen recordings with smooth camera moves, lays in music and sound effects, verifies everything numerically, and renders. Use when someone wants a reel, short or talking-head video edited, captioned, cut or rendered, drops footage into public/recordings/, revises an existing reel, wants to start a reel project or set up or check their Video Studio install, or asks what Video Studio can do.
---

# Reel edit

You edit vertical reels for a creator who never opens a video editor. They film a
talking head, describe the edit in plain language, and you build it in code.

The job is not "generate something that looks like an edit". It is to land every
beat on the exact frame the creator speaks it, inside the real geometry of their
face and their frame. That means **measuring before building** and **verifying
after**, every time. Almost every defect in this workflow comes from guessing a
number that could have been measured.

`${CLAUDE_SKILL_DIR}` below is this skill's folder (in chat it isn't filled in: read it as the folder this
SKILL.md was loaded from). Everything this skill uses is inside it, including the starter project
(`assets/reel-project`) and the Claude-app guide (`references/app-mode.md`).

The defaults in this skill (caption placement, the text hook, layouts, what
reads as cheap) were learned from many rounds of real notes on one creator's
channel. Treat them as strong defaults: the project's brand sheet
(`brand/BRAND.md`) overrides any of them, and so does the creator in chat.

## Where you're running

Check once, before the first step:

- **Local** (your shell is the creator's own machine, e.g. Claude Code or a desktop-app local session): run
  every command yourself.
- **Claude app with a linked folder** (your shell is a Linux cloud workspace, and linked-computer tools such as
  `device_list_dir` / `device_stage_files` / `device_commit_files` are available): read
  `${CLAUDE_SKILL_DIR}/references/app-mode.md` now and follow it. Work in the cloud and write results into their
  folder; the creator only runs `bash run.sh setup` and `bash run.sh transcribe` in Terminal, handed off as one
  plain line each.
- **Cloud only** (no linked folder): ask for the clips as attachments, and deliver the video with SendUserFile.

**"What can you do?"** Edit reels from one take or several clips: clips of any size, orientation or format joined
into one take, pauses and ums cut, frame-exact captions, Instagram-style text hooks, five layouts, screen
recordings with smooth camera moves, music and sound effects verified in the render, and a storyboard review page.

**"Check my setup":** `bash run.sh doctor` in a project, or `python3 ${CLAUDE_SKILL_DIR}/scripts/doctor.py`
(`--fix` installs the Python packages). It lists anything missing with the install command for their OS.

---

## 0. New project

No project yet? Start from the starter template, then set the machine up once:

```bash
cp -r ${CLAUDE_SKILL_DIR}/assets/reel-project ./my-reels && cd my-reels
bash run.sh setup      # ffmpeg, Node, npm packages, whisper.cpp + model, Remotion's browser, a self-test
```

`run.sh` is the project's single entry point for anything that runs on the creator's machine:
`setup`, `assemble <clips> --out <take>`, `transcribe <take>`, `cuts <take>`, `framing <take>`,
`jumpcuts <take>`, `render <Comp> [out]`, `check <Comp> <from-to>`, `studio`, `doctor`. Each step prints `ok` or
`FAIL: <reason>`.

**In the Claude app with a linked folder** (a cloud shell plus linked-computer tools), follow
`${CLAUDE_SKILL_DIR}/references/app-mode.md`: measure, build and render in the cloud and commit the results into
their folder; hand off only `bash run.sh setup` and `bash run.sh transcribe ...` as one plain line each.

The template ships `src/shared/` (the components below, the bundled Inter
font, `captions.ts` with the chunking rules), a `HookMeasure` composition,
`scripts/transcribe.mjs`, and `brand/BRAND.md` to fill in. Transcription uses
whisper.cpp when `scripts/setup-whisper.sh` has built it (most accurate
re-timing), otherwise `faster-whisper` (`pip3 install faster-whisper`, no
compiler).

The first Remotion render downloads its own headless Chrome. Where that
download is blocked, pass `--browser-executable=/path/to/chrome`.

## Project layout

```
project-root/
├── bin/whisper.cpp/              # optional: built whisper.cpp + ggml-base.en.bin, ggml-small.bin
├── brand/BRAND.md                # the creator's brand sheet + theme code (references/brand-sheet.md)
├── public/
│   ├── recordings/               # talking-head takes + <name>.words.json transcripts
│   ├── screen-recordings/        # screen captures, plus pre-cut clips
│   ├── images/ logos/            # stills the edit uses
│   ├── music pack/ sound pack/   # audio assets (original files; trim in code)
├── scripts/transcribe.mjs        # transcriber -> [{text,startMs,endMs}] (whisper.cpp or faster-whisper)
├── src/<project>/<Comp>.tsx      # one folder per video
├── src/Root.tsx                  # registers every <Composition>
└── out/                          # rendered mp4s
```

One folder and one composition per video. Never edit a composition the creator
has already approved in order to serve a new one; copy it or parameterise it.

---

## The pipeline

### 1. Ingest

Probe the file. If it is HEVC or `.mov`, **transcode to H.264 mp4 before doing
anything else**:

```bash
ffmpeg -y -i "raw.MOV" -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p \
  -r 30 -c:a aac -b:a 192k public/recordings/name.mp4
```

Confirm the frame count survived (`ffprobe -count_frames`). Remotion's
`OffthreadVideo` decodes `.mov` with duplicate-frame glitches that appear as a
one-frame flash, usually only in the final render.

### 1b. Several clips into one take

When the creator hands over several files ("here are my 3 takes", a folder of phone clips), assemble them first;
everything after this step then treats the result as one take:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/assemble.py public/recordings/raw/*.MOV --order time --jumpcuts \
  --out public/recordings/reel.mp4          # or: bash run.sh assemble ... in the project
```

It turns every clip upright and into 1080x1920 at 30 fps (any size, frame rate, `.mov` or HEVC; landscape clips
are cropped on the speaker's face, or fitted over a blurred copy when there's no face), gain-matches them to
-16 LUFS, and joins them frame-exactly with audio in sync. `--jumpcuts` (and `--fillers`) cuts each clip's pauses
the same way `jump-cuts.py` does; `--trim-ends` only removes dead air at each clip's start and end; `--punch 1.1`
alternates a zoom to hide the joins; `--order given|name|time` sets the running order (say which you used).

It also writes `reel.cuts.json` (every join, marked `clip` or `jump`, so captions break there and
`measure-framing.py` measures each shot), `reel.assembly.json` (what came from where), and `reel.words.json` when
every clip had a transcript; otherwise transcribe the assembled take once. Confirm the order and what was cut
with the creator before building on it, and never transcode or overwrite their original clips: they stay as
they are, the assembled take is a new file.

### 2. Transcribe

```bash
bash run.sh transcribe public/recordings/name.mp4        # -> public/recordings/name.words.json
```

**Never re-transcribe an unchanged file.** Whisper jitters between runs and every
beat you anchored will drift. (`transcribe.py` refuses to overwrite a transcript
without `--force`.)

### 3. Measure the take

This step is what makes the edit land. Do all of it before proposing anything.

**One command does the first pass:**

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/detect-cuts.py public/recordings/name.mp4 --out-dir "$TMPDIR/name"
```

It writes `name.cuts.json` (cut frames, frame count, warnings such as "still a .mov, transcode first") for the
composition to import, plus `sheet.jpg` (a timecoded contact sheet), `cuts.jpg` (the first frame after each cut)
and a measuring grid per shot. Then measure the framing per shot:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/measure-framing.py public/recordings/name.mp4 --out-dir "$TMPDIR/name"
```

It writes `name.framing.json`: per shot, the head top (hair or cap), eye line, mouth, chin and centre as min-max
ranges across the shot, plus a suggested caption baseline and hook position, and `framing-<shot>.png` with every
line drawn on a frame. **Look at those frames** before using the numbers: detection can miss a turned head or
find a face in b-roll. It does not find a handheld mic's windscreen; read that off the grid. Read all of it, then
refine with the manual steps below where needed.

**Cuts.** Use a low threshold, not the default:

```bash
ffmpeg -v error -i name.mp4 -vf "select='gt(scene,0.05)',metadata=print:file=-" \
  -f null - 2>&1 | grep -E "pts_time|scene_score" | paste - -
```

At 0.15 you will miss the creator's softer cuts, and a missed cut silently
becomes a caption-drift bug later. Convert to frames (`round(t * 30)`).

**Baked-in content.** Pull a contact sheet across the take and look for footage
the creator already edited: b-roll inserts, a title card, their own captions.
Schedule around it. Never overlay on top of the creator's own edits unless asked.

**Framing.** Extract a few frames with a measuring grid and read off the pixel
rows that matter:

```bash
ffmpeg -v error -i name.mp4 -vf "select=eq(n\,200),drawgrid=w=108:h=96:t=2:c=red@0.5,\
drawgrid=w=540:h=480:t=4:c=yellow@0.9" -vsync 0 -frames:v 1 grid.png
```

Record: baked title bottom, hair or cap top, eye line, mouth, chin, and the mic
windscreen top and bottom. These vary per take and per setup. Do not reuse
numbers from a previous video.

**Instagram safe band.** The 4:5 grid preview crops to roughly **y285 to y1635**
of 1920. Anything that must not be clipped lives inside that band.

### 4. Map the brief to frames

Turn every instruction into a frame number anchored to either a **word start**
from the transcript or a **cut**. Print the mapping before you build. "Around the
30 second mark" is not a frame; `f894, their cut at 29.8s` is.

When the creator says "when I say X", use the word's `startMs`. When they say "at
the next cut", use the detected cut. When both are available and they disagree by
more than a few frames, say so.

### 4b. Jump cuts (when asked)

"Cut the pauses", "make it tighter", "remove the ums": run

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/jump-cuts.py public/recordings/name.mp4 [--fillers] [--punch 1.12] --render "$TMPDIR/jc.mp4"
```

It finds pauses with the same voice envelope the caption checks use and, with `name.words.json`, never cuts
inside a word. It writes `name.jumpcuts.json` (kept spans) and `name.cut.words.json` (the transcript on the
**edited** timeline). Build on the edited timeline from then on: `components/JumpCut.tsx` plays the spans,
the composition is `outFrames` long, and every caption, graphic and cue anchors to `name.cut.words.json`.
`--punch 1.12` alternates a slight zoom per span (set `originY` on the eye line) so the jumps read as
intentional. Watch the preview and list the cuts in frames before building on them; a cut that eats the end
of a thought gets `--min-pause` raised or that span kept by hand.

### 5. Build

**Own-channel videos start from the project's brand sheet**
(`brand/BRAND.md` at the project root): its colours, type, captions, hooks and
motifs. The skill holds the workflow and editing preferences only; the look
belongs to the creator. No sheet yet: ask to set one up
(`references/brand-sheet.md`), never borrow another creator's. Brand deals
use the partner's palette instead.

See the references for the detailed conventions:

- `references/brand-sheet.md` — where the creator's look lives (`brand/BRAND.md`), what it
  covers, and how to set one up when a project has none
- `references/motion-graphics.md` — how to design the graphics: read the story, a job per
  moment, "illustrate it" vs "pitch me", cinematic type (words appear once), the quality
  bar and checklist, and a menu of capabilities
- `references/captions.md` — caption style, chunking, and the re-timing method
- `references/screen-recordings.md` — the camera engine and its traps
- `references/audio.md` — music beds, sound effects, and verification
- `references/background-removal.md` — graphics *behind* the speaker (optional)
- `references/split-screen-from-full-frame.md` — turn a full-screen take into the split format in code
- `references/text-hook.md` — the on-screen text hook (shared `TextHook` component, three
  variants: black on white, white on black, plain white) and how to measure its line widths
- `references/layouts.md` — the five layouts (talking head, 50/50 split, full-screen graphic,
  two-thirds split with a full-width rounded panel, full screen + silhouette) and where captions go in each
- `references/hyperframes-hybrid.md` — optional add-on: when a look (shader transition, real 3D,
  hand-drawn annotation, liquid glass) is better rendered in HyperFrames, render that one asset
  there and composite it here. Remotion still owns the reel; nothing above changes.

The skill is self-contained. Reusable pieces ship inside it, never in a
video's own folders (those get deleted when a video is done):

| Component (`components/`) | What it is |
| --- | --- |
| `fonts.ts` | Inter bundled from npm (`@fontsource/inter`): renders work offline and never time out on Google Fonts |
| `Caption.tsx` | a neutral caption line (outlined TikTok style or plain, optional emphasis style from the brand sheet) and `CARD_SHADOW`; the brand sheet's captions win when they exist |
| `TextHook.tsx` | the IG-native Inter text hook, three variants; one hook option among those in the brand sheet |
| `JumpCut.tsx` | plays only the kept spans of a take (from `jump-cuts.py`), optional punch-in per span, de-clicked audio |
| `TwoThirdsPanel.tsx` | layout 4b: the rounded panel, caption colour by background |
| `Silhouette.tsx` | layout 5: the matte cut-out at the bottom edge |

Theme code (palettes, fonts, grounds, the creator's caption and title
components) lives with the brand sheet in `brand/`, not here.

Copy a component into `src/shared/` the first time a video uses it. Anything
made for one video (its logos, cut clips, measurements) lives in
`public/<video>/` and `src/<video>/` only.

The scripts do the measuring that is tedious to redo by hand:

| Script | Use it when |
| --- | --- |
| `scripts/assemble.py` | several clips to edit as one: normalise, jump-cut, loudness-match and join them into one take |
| `scripts/doctor.py` | checking an install (the same checker `run.sh doctor` runs) |
| `scripts/detect-cuts.py` | first thing on a new take: cuts in frames, frame count, contact sheets, measuring grids |
| `scripts/measure-framing.py` | right after: head top, eye line, mouth, chin per shot; caption and hook suggestions |
| `scripts/jump-cuts.py` | the creator wants pauses (or um / uh) cut: keep-list, re-timed transcript, a preview mp4 |
| `scripts/retime-captions.py` | the creator says captions are behind or early (`--backend faster-whisper` without whisper.cpp) |
| `scripts/camera-check.py` | before rendering any screen-recording camera move (`--src WxH --keys "f:w:cx:cy ..."`; exits 1 over the limit) |
| `scripts/verify-audio.py` | after any render that added music or sound effects |
| `scripts/measure-hook.py` | setting or rewording a text hook (its line widths) |
| `scripts/caption-tone.py` | caption treatment per chunk: measures how light the caption band is (light clothing, a light wall, the two-thirds layout) |

General rules:

- Text graphics (hooks, headers) go in the clear band above the speaker's head.
  **Overlay images** (screenshots, reel tiles) go big and centred, covering the
  face rather than shrunk to the edges, where they are hard to read and get
  cut off on Instagram.
- Graphics start on their frame with motion already happening. Fade-ins read as
  slow on short-form.
- Anything anchored to a spoken word must be re-derived if the transcript is
  ever re-timed.
- Text in a grid or list must be **measured against its column**, not eyeballed.
  Render a still, find the white-pixel extent of each row, and confirm nothing
  overflows.

### 6. Verify before you render

Verify with **one range render**, never a stack of `remotion still` calls. Each
`still` re-bundles the whole project and costs 20 to 40 seconds; ten of them is
five minutes of pure rebuilding.

```bash
npx remotion render src/index.ts <Comp> "$TMPDIR/check" --sequence --frames=675-870 \
  --concurrency=75% --log=error
```

That writes `$TMPDIR/check/element-<frame>.jpeg`. Keep check frames out of `out/`, which
holds only deliverables; clear the check folder before each range. Build a contact sheet with ffmpeg
`hstack` and read it. `--frames` takes one range or one number; a comma list is
rejected.

Then render the whole thing. A 1480-frame 1080x1920 render is around **70 seconds**
on 12 cores (`--concurrency` takes a percentage of cores, so the commands work on any machine), so rendering is never the thing to avoid.

```bash
npx remotion render src/index.ts <Comp> out/name.mp4 --codec=h264 --crf=17 \
  --concurrency=75% --log=error
```

### 7. Verify the audio

Never assume music or a sound effect landed. Subtract the source voice out of the
render and inspect what is left: `scripts/verify-audio.py`. It reports the voice
gain (should be ~1.0), the isolated bed level, and the peak of every cue.

### 8. Deliver

Send the finished mp4. When a note touches only one beat, also send that segment
on its own (`--frames=A-B` to an mp4) so it can be judged without scrubbing.

State what you changed, in frames. If you made a judgment call the creator did
not specify, say which one and why.

When the creator asks for a storyboard, or the video has several motion-graphic
beats, review runs on an Artifact page: a clip per beat with Keep / Maybe / Drop
and a notes box, and one Submit review for the round. See
`references/storyboard.md` (flow) and `components/storyboard-review.html` (the
review kit).

---

## Gotchas

These are all expensive to rediscover.

1. **`.mov` in `OffthreadVideo`** produces duplicate-frame flashes. Transcode
   first, always.
2. **Trim music in code, not with copies.** `<Audio trimBefore={frames}>` (or
   `startFrom`) plays the creator's original file from that point; verified on
   Remotion 4.0.475 (2026-10-08). Do not write trimmed or loudnormed copies of
   their music; match levels with `volume` instead. (An older note here said
   `startFrom` was silent; that no longer holds.)
3. **Two `<OffthreadVideo>` elements on the same source file in one composition
   deadlock the decoder.** Splice a second copy to its own file instead.
4. **Whisper emits standalone punctuation as words.** Filter anything without an
   alphanumeric before chunking.
5. **Whisper drifts late inside long speech and pads sentence-final words.** See
   `references/captions.md`. This is the single most common complaint.
6. **Key any word-fix dictionary by index, not by `startMs`.** A fix keyed on a
   timestamp stops firing the moment you re-time the transcript, silently.
7. **A re-exported take re-paces non-uniformly.** Re-detect every anchor. Never
   apply a uniform frame offset.
8. **A camera clamp that keeps the window inside the source pinches to a single
   value** where the window height equals the source height, so any zoom crossing
   that width snaps. See `references/screen-recordings.md`.
9. **Mute every screen recording.** Their audio is almost never wanted.
10. **Check the creator's own cuts before letting a caption span one.** A line
    that survives a hard cut into new speech reads as broken.
11. **`interpolate()` needs a strictly increasing input range.** Mapping
    "further from zero means less" as `interpolate(x, [55, 5], ...)` throws
    at render time. Flip it: `interpolate(x, [5, 55], [outFor5, outFor55])`.
12. **A second video layered on top must be wrapped in its own
    `<AbsoluteFill>`.** `AbsoluteFill` is a flex column, so a bare second
    `OffthreadVideo` becomes a flex item and renders *below* the frame. The
    symptom is a render with zero changed pixels.
13. **Remotion render sequences name frames without padding past the range's
    width** (`element-925.jpeg` vs `element-1061.jpeg`). List the folder
    before building contact sheets from it.

---

## Working with the creator

- **Propose before building** anything with creative latitude: motion graphic
  concepts, sound effect placements, hook lines. Print a numbered list with
  frames and wait.
- **Prune-friendly lists.** Creators cut roughly a third of any sound effect plan.
  Offer more than you think is needed and mark which are optional.
- **Report in frames and timecodes**, so notes can come back precisely.
- **Flag trade-offs rather than silently resolving them.** If honouring one
  instruction costs something elsewhere, say what it cost.
- **Do not retro-patch approved compositions.** Fixing a shared helper can shift
  framing in a cut that has already shipped.

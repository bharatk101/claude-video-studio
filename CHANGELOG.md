# Changelog

## 0.6.1 (2026-10-26)

Prompts to copy, any folder on any OS.

- **[docs/prompts.md](docs/prompts.md):** what to say to Claude, from setting up a project (macOS, Windows,
  Linux, or any folder you choose) to joining clips picked by file name or as a whole folder, the options you
  can add, and notes after the first cut. The README's quick start shows both ways to pick clips.
- **Join a whole folder:** `bash run.sh assemble public/recordings/coffee-reel --order time --out ...` takes every
  video directly inside the folder (`.mov`, `.mp4`, `.m4v`, `.mkv`, `.webm`, ...), skipping subfolders, other
  files and the output itself. Files and folders can be mixed; duplicates are dropped.
- **Windows:** `bash run.sh setup` works in Git Bash. It finds Python as `python` or `python3`, uses the venv's
  `Scripts\python.exe`, finds the Windows whisper.cpp build, prints `winget` commands for anything missing, and
  falls back to faster-whisper when there's no C++ compiler. CI now runs the full setup, a real transcription,
  a render and a folder join on Windows as well as macOS and Linux.
- The reel skill knows where a project can go (each OS's default, or any path the creator names) and how to
  write that path in the setup line for their shell.

## 0.6.0 (2026-10-26)

First public release: edit reels by talking to Claude.

**Install**
- From the Claude app with no commands: Customize > Plugins > Add > Add marketplace (`bharatk101/claude-video-studio`),
  or Upload plugin with `video-studio.zip` from the release. Saved to your account, so it's also in Cowork and
  syncs to Claude Code. Or `/plugin marketplace add` in Claude Code.
- A reel project sets itself up with one Terminal line, `bash run.sh setup`: ffmpeg, the npm packages,
  whisper.cpp and its speech model, Remotion's browser, then a transcription self-test, `ok` or `FAIL` per step.

**Editing**
- **Several clips into one take** (`run.sh assemble`): any size, orientation, frame rate, `.mov` or HEVC, turned
  upright and sized to 1080x1920 at 30 fps (landscape clips cropped on the speaker's face), matched to -16 LUFS,
  joined frame-exactly with audio in sync.
- **Jump cuts** (`run.sh jumpcuts`): pauses and, with `--fillers`, um/uh removed, never mid-word, optional
  punch-ins; the transcript is re-timed onto the edited timeline.
- **Measured framing** (`run.sh framing`): head top, eye line, mouth and chin per shot, with caption and hook
  positions suggested; offline (OpenCV).
- **Cuts to the frame** (`run.sh cuts`), contact sheets and measuring grids.
- Frame-exact captions, Instagram-style text hooks, five layouts, screen recordings with smooth camera moves,
  music and sound effects verified in the render, a storyboard review page, and a brand sheet for your look.

**Works where you are**
- Claude Code, or the Claude app with a linked folder: Claude edits and renders in its cloud workspace and saves
  the results into your folder; the only Terminal steps are setup and transcription, handed to you as one line.
- The skill is self-contained (the app loads only the skill's own folder).

**Quality**
- Known-answer tests for cuts, framing, jump cuts, joining clips, camera moves, the setup checker and `run.sh`;
  CI on macOS, Linux and Windows, including a real whisper.cpp transcription.

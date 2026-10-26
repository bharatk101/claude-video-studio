# Changelog

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

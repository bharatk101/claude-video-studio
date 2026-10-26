# Working from the Claude app with a linked folder

The creator chats in the Claude app (desktop, web or phone) and has linked a folder on their own computer, for
example `~/Movies/reels`. Claude edits the project files in that folder; the creator never opens an editor.

## Know which mode you're in

| Signal | Mode | What to do |
| --- | --- | --- |
| Your shell (`uname`) is the creator's own OS and sees their folder directly | **Local** (Claude Code, the desktop app's local sessions) | Run everything yourself, including `bash run.sh ...` |
| Your shell is a Linux cloud workspace, and linked-computer tools (`device_list_dir`, `device_stage_files`, `device_commit_files`, `device_bash`) are available | **App mode** (this page) | Split the work as below |
| A cloud workspace and no linked-computer tools | **Cloud only** | Ask for uploads; deliver files with SendUserFile |

In app mode, `device_bash` is a small Linux VM on their machine with the linked folders mounted under
`~/mnt/<folder>`. It is good for listing, moving and light file edits. It is **not** their Mac: no Homebrew,
no Mac binaries, often no internet, and each command is capped at about 3 minutes. Never try to render, build
whisper.cpp or `brew install` there.

## Who runs what

| Step | Where it runs | How |
| --- | --- | --- |
| Create the project, write compositions, components, brand sheet | **Cloud**, then copied into their folder | Write files in the cloud copy, then `device_commit_files` them into the folder |
| One-time setup: npm packages, whisper.cpp + model, Remotion's browser | **Their computer** | Hand off `bash run.sh setup` (5-10 min) |
| Transcribe a take | **Their computer** (the cloud usually can't download whisper models) | Hand off `bash run.sh transcribe public/recordings/<take>.mp4` |
| Join several clips into one take (`assemble.py`), jump cuts | **Cloud** | Stage the clips (and their transcripts), assemble there, commit the take + its `.cuts.json` / `.words.json` / `.assembly.json` back |
| Measure the take: cuts, contact sheets, grids, framing | **Cloud** | Stage the take, run `detect-cuts.py` and ffmpeg there, read the sheets yourself |
| Typecheck, review frames, the final render | **Cloud** by default | Stage what the composition uses, render there, commit the mp4 into their `out/` |
| A render the cloud can't do (very large footage, a HyperFrames/WebGPU asset, a blocked download) | **Their computer** | Hand off `bash run.sh render <Composition>` |

Prefer the cloud for everything it can do: the creator should only touch Terminal for the one-time setup
and transcription.

## Moving files

- **Folder to cloud:** `device_stage_files` for exactly what the step needs: the take, `*.words.json`,
  `*.cuts.json`, `brand/`, the `src/` folder, the music and sound files the edit uses. Never stage
  `node_modules/`, `bin/` or `.venv/`; run `npm install` in the cloud copy instead.
- **Cloud to folder:** `device_commit_files` for the files you wrote or changed (`src/<Video>/...`,
  `brand/BRAND.md`, `public/<video>/...`) and the deliverable (`out/<name>.mp4`). Commit only what changed, and
  never overwrite their recordings or music.
- Keep one cloud working copy per project for the session (for example `~/work/<project>`), so re-renders don't
  re-stage the footage.
- In the cloud, Remotion may not be able to download its own headless browser. Render with
  `--browser-executable=<Chrome>` (find one with `which google-chrome chromium chromium-browser`).

## Handing off a Terminal command

This is where app-mode sessions go wrong: commands arrive garbled (`[object Object],[object Object]`), half
pasted, or with no way to tell whether they worked. The rules:

1. **Put the command in the reply text itself**, in a plain fenced block, exactly as it should be pasted. Never
   pass a command through a widget, a tool argument, an object or a list that the app renders for you.

   ```bash
   cd ~/Movies/reels && bash run.sh setup
   ```

2. **One short line.** Every step is a `run.sh` subcommand, so there's never a multi-line script to paste.
   Always start with `cd <their folder> &&` because Terminal opens in their home folder. **Windows is different:**
   setup is a double-click on `setup.cmd` in their folder, and later steps are PowerShell lines with `;` and
   `.\run.cmd` (`cd ~\Videos\reels; .\run.cmd transcribe public/recordings/take.mp4`). Never hand a Windows user
   a `&&` line. SKILL.md section 0 has the table. Tell them plainly why it's theirs to run: your shell here is a
   sandbox that can't install programs on their computer.
3. Say **how long** it takes and **what success looks like** ("about 5 minutes; it ends with *All set.*").
   Every `run.sh` step prints `ok` or `FAIL: <reason>`; ask them to paste the output back if anything fails.
4. **Don't claim it's done until you've checked.** When they say it finished, look: `device_list_dir` on
   `out/` or `public/recordings/` to see the new file, then stage it and check frames or the transcript
   before saying it's ready.
5. If the folder has no `run.sh` (an older project), copy `run.sh` and `scripts/` in from the reel-edit skill's
   `assets/reel-project/` first.

## A typical session

1. "Edit my take": `device_list_dir` the folder. No project yet? Copy the starter template in
   (`device_commit_files` from a cloud copy of the reel-edit skill's `assets/reel-project`), then hand off
   `bash run.sh setup`.
2. The take is in `public/recordings/`. Not transcribed yet? Hand off `bash run.sh transcribe ...`.
3. Stage the take and its `words.json`; measure it (cuts, framing) in the cloud; map the brief to frames; build
   the composition in the cloud copy; typecheck; render review frames and look at them.
4. Render in the cloud; commit `out/<name>.mp4` (and the source files) into their folder; tell them where it is
   and what you changed, in frames.
5. Notes come back: edit, re-render the touched range, commit again. No Terminal needed.

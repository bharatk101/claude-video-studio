# Prompts you can copy

Things to say to Claude, from setting up a project to joining clips and asking for changes. Change the parts in
*italics* and paste the rest. You don't need the exact wording: Claude understands plain requests. These just
include the details that save a round of questions.

- [Set up a project](#set-up-a-project) on macOS, Windows, Linux, or in any folder you choose
- [Join and edit several clips](#join-and-edit-several-clips), picked by file name or as a whole folder
- [What you can add to any request](#what-you-can-add-to-any-request)
- [After the first cut](#after-the-first-cut)

---

## Set up a project

Link the folder to the chat first (the **+** menu, **Add folder**), or in Claude Code open a terminal there. The
project can live anywhere. These are the usual places:

| Your computer | Say | Then paste this one line |
|---|---|---|
| **macOS** | > Set up a reel project in ~/Movies/reels | `cd ~/Movies/reels && bash run.sh setup` in **Terminal** |
| **Windows** | > Set up a reel project in C:\Users\\*you*\Videos\reels | `cd ~/Videos/reels && bash run.sh setup` in **Git Bash** |
| **Linux** | > Set up a reel project in ~/Videos/reels | `cd ~/Videos/reels && bash run.sh setup` in a terminal |

**Your own folder.** Any path works, including another drive or a synced folder:

> Set up a reel project in *~/Dropbox/Shorts/2026*

> Set up a reel project in *D:\Content\Reels*

> Set up a reel project in the folder I just linked

Claude gives you the line for that folder. In Git Bash, a Windows path like `D:\Content\Reels` is written
`/d/Content/Reels`, and Claude converts it for you. Folder names with spaces are fine too: Claude quotes
them, for example `cd ~/"My Videos/reels"`.

**Windows notes.** `run.sh` is a bash script, so it runs in **Git Bash** (installed with
[Git for Windows](https://git-scm.com/download/win)) or in WSL, not in PowerShell or Command Prompt. Setup tells
you what to install if something is missing, for example `winget install Gyan.FFmpeg`. Building whisper.cpp
needs a C++ compiler, so without Visual Studio Build Tools, setup uses faster-whisper instead. Your captions work
either way.

**Already have a project?**

> Check my Video Studio setup in *~/Movies/reels*

---

## Join and edit several clips

Clips go anywhere inside the project, usually `public/recordings/`. Claude never changes your original files:
the joined video is a new file.

### Pick clips by file name

Name them in the order you want them:

> Join *intro.MOV*, *take3.MOV* and *outro.mp4*, in that order. Cut the pauses and the ums, add captions, and
> add a hook that says "*the 3 apps I use every day*".

Leave some out:

> Use every clip in public/recordings except *take2.MOV* (I fluffed it). Keep them in recording order.

Use part of a clip:

> Join *take1.MOV* and *take4.MOV*, but only use *take4* from *0:12* onwards.

### Use a whole folder

Put the clips for one video in their own folder, for example `public/recordings/coffee-reel/`, then:

> Join everything in *public/recordings/coffee-reel* in the order I filmed it. Cut the pauses and the ums,
> add captions and a hook that says "*my 5 am routine*".

Claude takes every video directly inside that folder (`.mov`, `.mp4`, `.m4v`, `.mkv`, `.webm`) and skips
anything else. Subfolders, audio and other files are left out. Choose the order:

| Say | Order |
|---|---|
| "in the order I filmed it" | recording time, read from the phone's metadata |
| "in name order" / "alphabetically" | file names: `01-intro.mov`, `02-...` |
| "in this order: ..." | exactly the order you list |

Tip: number your files (`01-hook.mov`, `02-point.mov`, ...) and ask for name order. It's the easiest way to
reorder things without typing every name.

### A full template

> Make a reel from *the clips in public/recordings/coffee-reel*, *in the order I filmed them*.
> - Cuts: *remove the pauses and the ums*, *small zoom on every other cut*
> - Captions: *yes, in my brand style*
> - Hook: "*my 5 am routine*" for the first *2* seconds
> - Music: *public/music pack/lofi.mp3*, quiet under my voice
> - Save it as *out/coffee-reel.mp4*

Before it builds the edit, Claude confirms the clip order and what it cut.

---

## What you can add to any request

| You say | What Claude does |
|---|---|
| "cut the pauses" | jump cuts: removes silences, never mid-word |
| "and the ums" | also removes um / uh / er |
| "just trim the start and end" | only removes dead air at the start and end of each clip |
| "small zoom on every other cut" | alternates a 10% punch-in to hide the joins |
| "crop on my face" / "keep the whole frame" | for landscape clips: crop to your face, or fit them over a blurred copy |
| "match the volume" | done for you: every clip is levelled to the same loudness |
| "add captions" | word-timed captions, placed clear of your face |
| "add a hook that says ..." | an on-screen title over the opening seconds |
| "cut in my screen recording at ..." | a screen recording from `public/screen-recordings/` with smooth zooms |
| "add music / a whoosh on the cut" | from `public/music pack/` and `public/sound pack/`, checked in the render |

---

## After the first cut

Give notes the way you would to an editor, with a time if you have one:

> The captions are a bit late around *0:12*.

> Make the hook shorter: "*5 am routine*".

> Put *take3* before *take2*.

> Cut *"so basically"* at *0:21*.

> Too many zooms, keep only the first two.

> Render the final version.

Claude re-renders only what changed and tells you where the new file is.

---

<sub>For people curious about what runs underneath: joining clips is `bash run.sh assemble <files or a folder>
--out <file> [--order given|name|time] [--jumpcuts] [--fillers] [--trim-ends] [--punch 1.1] [--fit crop|blur]`.
The [guide](guide.md#the-commands-claude-runs) lists all the commands.</sub>

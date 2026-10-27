# Roadmap

Where Video Studio is going, in the order we plan to build it. Every item says what changes for a creator, which
existing tool it builds on, and roughly how big it is (**S** = a day or two, **M** = about a week, **L** = more).

Want to help? Open an issue naming the item, or comment on an existing one, before you start. Done items move to
the [changelog](../CHANGELOG.md).

**The idea in one line:** Video Studio stays the *editor* that measures your footage and keeps everything
frame-exact. Remotion stays the engine that draws and renders it. Remotion's own skills and HyperFrames' skills
come in as *companions* for the things they do best.

---

## Phase 1: use Remotion fully (0.7)

Today the reels use Remotion's basics: clips on a timeline, trimmed video, `spring` and `interpolate` animation,
audio, bundled fonts. The measuring happens before Remotion, in Python. These items use more of Remotion itself.

| | Item | What changes for you | Built on | Size |
|---|---|---|---|---|
| 1.1 | **Automatic video length** | A reel's length is read from the take itself, so a trimmed or re-cut take never leaves black frames at the end | [`calculateMetadata`](https://www.remotion.dev/docs/calculate-metadata) | S |
| 1.2 | **Transitions between clips and sections** | "Fade between my clips" or "slide to the next point" just works, without hand-built animation | [`@remotion/transitions`](https://www.remotion.dev/docs/transitions) (`TransitionSeries`) | S |
| 1.3 | **Drag to adjust in the preview** | Open the preview (`bash run.sh studio`) and drag a caption, hook or sticker into place; the change is written back to the code | [Studio interactivity](https://www.remotion.dev/docs/studio/interactivity) (Remotion 4.0.475+) | M |
| 1.4 | **Remotion's official skills as companions** | Claude follows Remotion's own guidance for rendering, captions, upgrades and docs lookups, alongside this skill's reel rules | [`remotion-dev/skills`](https://www.remotion.dev/docs/ai/skills) | S |
| 1.5 | **Music that ducks under your voice, waveforms** | Music dips automatically while you speak; optional audio waveform graphics | [`@remotion/media-utils`](https://www.remotion.dev/docs/media-utils) | M |
| 1.6 | **Playable storyboard** | The review page plays each section in the browser instead of showing still frames | [`@remotion/player`](https://www.remotion.dev/docs/player) | M |
| 1.7 | **Easy upgrades** | "Update Remotion" bumps every package together and re-runs the checks | `/remotion-upgrade` skill | S |

**How the companion skills split the work (1.4).** Remotion's skills cover Remotion in general; this skill
covers reels and the measured, frame-exact workflow. When both could apply, this skill decides, and calls theirs for:

| Remotion skill | Used for |
|---|---|
| `/remotion-render`, `/remotion-studio` | render flags, still frames, opening the preview |
| `/remotion-docs` | looking up any Remotion API before using it |
| `/remotion-upgrade` | version bumps (1.7) |
| `/remotion-interactivity` | making components draggable in Studio (1.3) |
| `/remotion-markup`, `/remotion-best-practices` | general Remotion code patterns (fonts, media, effects) |
| `/remotion-maps` | map animations ("show where I travelled") |
| `/remotion-captions` | not for reels: Video Studio's captions are measured against the face and timed per word |
| `/remotion-create`, `/remotion-saas`, `/remotion-multimedia` | not needed for reels |

Install: `npx skills add remotion-dev/skills`. They stay a separate install (their licence is Remotion's own).

---

## Phase 2: HyperFrames as a companion (0.8)

[HyperFrames](https://github.com/heygen-com/hyperframes) (by HeyGen, Apache 2.0) renders plain web pages to
video and ships skills for AI agents. The reel skill already has a guide for using it to build single effects
([hyperframes-hybrid.md](../skills/reel-edit/references/hyperframes-hybrid.md)). This phase makes that a
first-class path: Video Studio keeps the timeline, and HyperFrames builds assets that drop into it.

| | Item | What changes for you | HyperFrames skill | Size |
|---|---|---|---|---|
| 2.1 | **One-line companion install, detected by the doctor** | "Add HyperFrames" installs it; `run.sh doctor` shows it as available | plugin `hyperframes@hyperframes` | S |
| 2.2 | **450 ready-made effects** | "Add a glitch title", "film grain", "a bar chart of my stats": picked from HyperFrames' catalog, rendered with a transparent background, placed on your timeline at the word you say it | `/hyperframes-registry` | M |
| 2.3 | **Free music, sound effects and cut-outs** | Royalty-free music and SFX, background removal for silhouette layouts, colour grades for dull footage, with free local tools | `/media-use` | M |
| 2.4 | **Brand from Figma** | Paste a Figma link; your colours, fonts and logo fill the brand sheet | `/figma` | S |
| 2.5 | **Smoother scene changes** | Their motion rules (how a scene exits sets how the next enters; velocity-matched zoom-through and blur cuts) adapted to reels | ideas from `motion-doctrine`, `cut-the-curve`, `seam-craft` (HyperFrames' in-repo skills; studied, not copied) | M |
| 2.6 | **A licence-free render path (study)** | Remotion needs a paid company licence for teams of 4+. Spike: can the same reel render through HyperFrames, so companies can use Video Studio for free? Decide after a prototype | `/remotion-to-hyperframes`, `/hyperframes-cli` | L |

Not planned: `/slideshow` (live decks) and `changelog-video` (HeyGen's own weekly video) don't fit reels.

**Who decides.** HyperFrames' main skill calls itself the entry point for *any* video request. For reels, Video
Studio's skill stays in charge and opens a HyperFrames skill only to build an asset, as the hybrid guide already
says. 2.1 makes the reel skill say this the moment HyperFrames is installed, so the two never compete.

---

## Phase 3: better edits, faster (0.9)

| | Item | What changes for you | Built on | Size |
|---|---|---|---|---|
| 3.1 | **Quick mode** | "Just cut the pauses and add captions" renders in seconds with ffmpeg alone, no browser, no Remotion | ffmpeg, the existing jump-cut and caption tools | M |
| 3.2 | **Auto-reframe 16:9 to 9:16** | Landscape footage follows your face across the frame, not one fixed crop | `measure-framing.py` face tracking | M |
| 3.3 | **Find the handheld mic** | Captions sit clear of a mic without measuring by hand | OpenCV | M |
| 3.4 | **Captions in Hindi, Kannada and more** | Multilingual transcription and fonts for Indic scripts | whisper multilingual models, Noto fonts | M |
| 3.5 | **A sample clip in the repo** | Try the whole workflow in a minute before filming anything | a short clip (with permission) | S |
| 3.6 | **Background removal built in** | Silhouette layouts without another app | local matting model, or 2.3 | M |

---

## Phase 4: after the edit (1.0)

These use apps you can connect to Claude. Each one is optional: Video Studio works without them.

| | Item | What changes for you | Connects to | Size |
|---|---|---|---|---|
| 4.1 | **Hand touch-ups in a real editor** | Export the cut to Premiere Pro or DaVinci Resolve with every clip and cut in place | FCPXML / OpenTimelineIO from `cuts.json`; or the Descript connector, which exports Premiere and Resolve timelines | M |
| 4.2 | **Thumbnails and covers** | A cover frame for the reel in your brand style | Remotion still from the brand sheet; Canva connector for templates | M |
| 4.3 | **Publish and schedule** | "Post this to Instagram at 7 pm with this caption" | Instagram via the vidIQ connector, or many networks via the Postiz plugin | M |
| 4.4 | **Titles and captions that perform** | Title and caption ideas scored before you post | vidIQ connector | S |

---

## Always

- **Setup that just works**: every new failure someone hits becomes a fix plus a CI check (as with Windows
  `setup.cmd`).
- **CONTRIBUTING.md** and good-first-issue labels for each S item above.
- **An examples gallery**: before and after reels made with Video Studio.

## Licences, in one place

| Tool | Licence | What it means for you |
|---|---|---|
| Video Studio | MIT | free for anyone |
| Remotion | Remotion licence | free for individuals, teams up to 3 and non-profits; companies of 4+ pay ([details](https://www.remotion.dev/docs/license/faq)) |
| Remotion skills | Remotion licence | separate install |
| HyperFrames and its skills | Apache 2.0 | free for anyone, including companies |
| ffmpeg, whisper.cpp, faster-whisper, OpenCV | LGPL / MIT / Apache | free |

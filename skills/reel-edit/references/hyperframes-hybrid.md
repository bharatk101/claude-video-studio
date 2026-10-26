# Remotion + HyperFrames: who does what

**Remotion owns the reel.** The timeline, the footage, every word-synced beat,
captions, screen-recording cameras, audio and the final render all stay in
Remotion. **HyperFrames is an asset generator**: when a look is genuinely
easier or only possible there, render that one asset in HyperFrames and drop
it into the Remotion timeline as a transparent layer or a full-frame insert.

The HyperFrames skills describe themselves as the "mandatory entry point" for
any video request and default the output to HyperFrames. For reels edited with this skill
that does not apply: route through this skill, and open a HyperFrames
skill only to build an asset this page sends you to.

---

## Decide per element

### Keep in Remotion (the default)

| Element | Why Remotion |
| --- | --- |
| Anything anchored to a spoken word: logo pops, thumbnails, stat hits, lists | frame-exact against the transcript, measured against the creator's framing |
| Captions (TikTok black-outline style) | the creator's fixed style; HyperFrames' caption pipeline is a different look and needs a full-frame matte |
| Screen recordings, Screen Studio camera, own cursor | our camera engine, clamp rules and pan-speed check |
| Brand-matched 2D motion graphics (gradient plates, cards, grids, waveforms, mock UI built from real screenshots) | React + `spring` does this well, and it lives next to the footage it syncs with |
| Music beds, SFX, voice-over sync, the final mix | one audio timeline, verified with `verify-audio.py` |
| Lottie files | `@remotion/lottie` covers it |

### Render in HyperFrames, composite in Remotion

| Look | Registry items / adapter | Notes |
| --- | --- | --- |
| **WebGL shader transitions** between two shots | glitch, whip-pan, light-leak, domain-warp-dissolve, cross-warp-morph, ripple-waves, thermal-distortion, gravitational-lens, swirl-vortex, sdf-iris, ridged-burn, chromatic-radial-split, flash-through-white | They blend scene A into scene B, so feed both shots in as stills or short clips and render a full-frame MP4 insert covering the cut |
| **Light / texture overlays** | organic-light-leak-overlay, editorial-flash-overlay, grain-overlay, halftone-field, ordered-dither-pass, ascii-render-pass, light-sweep-pass | Overlays render as transparent MOV; texture *passes* process footage, so the clip goes into the HF project |
| **Real 3D** (Three.js / WebGPU) | orbit-card, glass-shard-title, cuboid-carousel, canopy-part-title, wireframe-portal-title, frost-sequence-camera-orbit, gallery-tunnel, cosmic-orb, camera-dolly-zoom, vfx-iphone-device, carousel-orbit-*, code-3d-extrude | Authored at 1920x1080 (see "16:9 blocks" below) |
| **Hand-drawn annotation** with boil jitter and squash | hw-callout-circle, hw-arrow, hw-underline, hw-box-label, hw-write-title, hw-path-text, hw-scribble-transition, marker-highlight, marker-checklist-card | Tested: transparent MOV over talking head, clean edges |
| **Liquid Glass UI** | ios26-liquid-glass, macos-tahoe-liquid-glass, vfx-liquid-glass, liquid-glass-notification | Renders through Google Chrome; see "Liquid Glass" below |
| **Ready-made vertical mock UI / social props** | ai-chat-reveal, chatgpt-exchange, claude-exchange, message-thread-reveal, notification-cascade, notes-reveal (all 1080x1920); instagram-follow, tiktok-follow, spotify-card (1080x1920) | Good for a CTA ending or an "AI answers" beat when no real screen recording exists |
| **Maps, chart races** | us-map (bubble / flow / hex), world-map, bar-chart-race, data-chart | |
| **Named text effects** when one matches exactly | char-slam-explode, matrix-decode, scramble-reveal, slot-machine-roll, rgb-glitch-text, wordmark-tiles, split-flap-board, variable-axis-type | Plain rises, fades and pops stay in Remotion |

When a brief names a look ("glitch", "film burn", "CRT", "confetti", "chart"),
search the registry before hand-building it:

```bash
npx hyperframes catalog --query "film burn" --json   # local, no account, sends nothing
npx hyperframes catalog --tag shader --json
```

---

## The handoff

1. **Project.** One folder per asset: `hyperframes/<reel>-<asset>/`.
   ```bash
   cd hyperframes && HYPERFRAMES_SKIP_SKILLS=1 npx hyperframes init <reel>-<asset> \
     --example blank --resolution portrait --non-interactive
   cd <reel>-<asset> && npx hyperframes add <registry-item> --no-clipboard
   ```
   Telemetry stays off (`npx hyperframes telemetry disable`). Skip the
   skills' `hyperframes feedback` step; it posts publicly.
2. **Author in reel coordinates.** The root is `data-width="1080"
   data-height="1920"`. Measure positions off the reel frame first (cap top,
   eye line, caption band), exactly as for a Remotion graphic, so Remotion
   mounts the asset at 1:1 with no scaling.
3. **Author in reel time.** Duration comes from the root `data-duration`
   (there is no CLI flag): set it to `frames / 30`. The asset's t=0 is the cue
   frame. If it has internal beats tied to words, compute them as
   `(wordFrame - cueFrame) / 30` and put them in the GSAP timeline or pass them
   with `--variables`. The word map still comes from the Remotion side.
4. **Render.**
   ```bash
   npx hyperframes check
   npx hyperframes render . --format mov --fps 30 -o renders/<asset>.mov   # transparent overlay
   npx hyperframes render . --fps 30 --quality delivery -o renders/<asset>.mp4  # full-frame insert
   ffprobe -v error -select_streams v -show_entries stream=pix_fmt,nb_frames -of csv=p=0 renders/<asset>.mov
   ```
   Expect `yuva444p12le` and the frame count you asked for. A 53-frame 2D
   overlay renders in about 8 seconds; WebGL and 3D are slower and should run
   one at a time. 4K cannot be combined with alpha.
5. **Composite.** Copy the asset to `public/hyperframes/` and mount it:
   ```tsx
   <Sequence from={CUE} durationInFrames={LEN}>
     <AbsoluteFill>                                  {/* wrapper required */}
       <OffthreadVideo src={staticFile("hyperframes/<asset>.mov")} transparent muted />
     </AbsoluteFill>
   </Sequence>
   ```
   Use the `.mov`, never the `.webm` (VP9 alpha renders fully transparent in
   Remotion). For a full-frame insert, use the `.mp4` without `transparent`.
6. **Verify** with one range render over the cue, as always. If the MOV shows
   a one-frame duplicate flash, re-render as `--format png-sequence` and mount
   the frames instead.

### 16:9 blocks

Every 3D and shader block is hard-coded to 1920x1080 (CSS, canvas and camera
aspect). Mounting one in a portrait host does not reframe it. Two options:

- **Use it as a band.** 1920x1080 scaled to 1080 wide is 1080x608, which is
  exactly the top half of the split-screen format, or a band above the head.
  Render it as is and scale it in Remotion.
- **Retarget it.** Edit the block's source (canvas size, camera aspect, layout
  constants, e.g. `orbit-card/assets/orbit-scene.js`). This is real work: quote
  it to the creator before doing it.

Some blocks (canopy-part-title, glass-shard-title, wireframe-portal-title)
load three / gsap / d3 from CDNs at render time and need the network.

### Liquid Glass (WebGPU + html-in-canvas)

The bundled headless shell cannot run WebGPU and `drawElementImage`
together, so liquid-glass blocks render through the full Google Chrome app:

```bash
export PRODUCER_HEADLESS_SHELL_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
npx hyperframes render . --fps 30 --workers 1 -o renders/<asset>.mp4
```

- The log should show `LiquidGlass: WebGPU renderer initialized` and
  `hardware gpu`. A 4s block renders in about 8s; it is pinned to one worker.
- Tested 2026-10-06 (hyperframes 0.8.136): Chrome's render is bit-identical to
  Brave's (every decoded frame hashes the same), so Brave is not needed. It
  runs fine while the creator's own Chrome is open.
- Always run these renders with a time cap and kill any leftover headless
  Chrome process if one stalls.

---

## What not to do

- Do not port the reel to HyperFrames (`remotion-to-hyperframes` is one-way
  and would throw away the caption, camera and audio tooling).
- Do not caption in HyperFrames. `embedded-captions` is a separate full-frame
  pipeline (WhisperX, a CPU matte at ~2 fps) with its own styles.
- Do not route an element through HyperFrames just because a registry item
  exists. If Remotion builds it in comparable time and it must sync to
  several words, keep it in Remotion.
- Do not reach for `media-use resolve`; it needs a signed-in HeyGen CLI. Our
  own sound pack, music pack and image folders come first.

# Motion graphics

How to design the graphics in a reel: what to illustrate, how, and what the
creator expects before they see anything. Colours, type and motifs come from
the project's brand sheet (`brand/BRAND.md`, see `brand-sheet.md`); layouts
and caption positions from `layouts.md`. These are editing preferences built
up over many rounds of notes; they hold whatever the brand.

## Two modes

- **"Illustrate it"** (or no instruction beyond the edit): pick the best idea
  per moment yourself, build it, and show it on the storyboard page
  (`storyboard.md`) where they leave notes per beat. No proposal round.
- **"Pitch me"**: list 2-3 angles per moment first (frames, the words it
  hangs on, layout, style, assets), wait for their picks, then build.

## Safe area (every graphic)

All motion-graphic content sits inside **x 90-990** and the Instagram 4:5 band
**y 285-1635**. Big serif type is the usual offender: a 200 px two-word serif
line runs about 1050 px wide, so size headlines to about 860 px. Thumbnail fans
and orbiting card rings drift past the sides too. After the render, measure the
real pixel extents (column scan or `drawbox` guides at x90/x990); never
eyeball it. Decorative full-bleed shapes (blobs, grounds) are exempt.

Timing: graphics enter a few frames before the spoken word and hold until the
next graphic replaces them. Camera moves inside a take are slow eased pushes,
and framing only jumps on a real cut.

## 1. Read the story, not the sentences

Find the script's shape: hook, setup, turn, payoff, CTA. Pick the moments where
a visual adds something the words can't; in a 50 s reel that is usually 3 to 6,
with talking head between them so each one lands. A graphic on every line is
noise.

## 2. Give each moment a job

| Job | When | Treatment |
| --- | --- | --- |
| **Prove** | a claim, a stat, a result | the real source: paper, screenshot, metric, its actual figure or numbers |
| **Explain** | an idea or process | an analogy or diagram, drawn |
| **Show** | a product, a feature, a workflow | their screen recording, or the UI redrawn |
| **Feel** | a story beat, a turn, a joke | an illustrated scene or mood |
| **Emphasize** | the line they lean on | cinematic type (below) |

Research claims always **prove** with the source's own figure, never a
metaphor (a paper's own figure beats a stylised arc). Show compared groups one at a time, each filling the frame, on one
shared scale.

## 3. Layout and style

- Layout per moment: full screen, 50/50 split pane, over their face, two-thirds
  panel, word behind their head (`layouts.md`).
- Style from the brand sheet's theme by default, so the channel stays
  consistent; the creator may name another look for a moment, or say
  "surprise me".
- **One style family within a video** so it feels designed; **a different
  family from the last video** so the channel doesn't repeat itself.
- Drawn analogies or their own screenshots and recordings, decided per moment;
  never rule their assets out.

## The creator's theme

Motion graphics use the brand sheet's main theme (its grounds, cards, label
style, headline type, accent colour and transitions) so every video reads as
one channel. Captions keep the sheet's caption style. Anything the sheet marks
as an option (a second palette, another hook style) is used only when the
creator picks it for a video.

## 4. Cinematic type

Designed words are allowed, including the exact words they are saying, when the
typography itself is the visual: a giant serif word filling the frame, a word
half behind their head, their video playing inside the letters, a full-screen
"script page" line with an italic payoff word, a title card with a timecode.

- **Words appear once.** While a graphic shows the words they are saying, hide
  the regular captions for that span; bring them back on the next phrase.
- Use it for the line they lean on, sparingly: a few per video, mostly the hook
  and the turns. Plain restating of caption text in a box is still out.
- Type from the brand sheet: its headline face for the big word, a heavy sans
  for weight contrast, its italic or accent face for the payoff word.
- Behind-the-head words need the person matte (`background-removal.md`).

## 5. Anchor to the creator's words

- Every graphic starts on a word's frame or a cut, already moving (no fade-ins).
- Its key hits (a number landing, a piece snapping in, a card flipping) land on
  the words they illustrate. Map them to frames before building.
- Overlay images (screenshots, reel tiles) go big and centred and cover the
  whole face, hair to chin; a card that stops mid-face looks wrong, and small
  tiles pushed to the edges are hard to read and get cut off on Instagram.
  Straight, square, no border, a soft shadow (`CARD_SHADOW`); rounded corners
  or a fade-in only when asked. Blur or crop other people's names and handles
  out of DM and comment screenshots.
- Anything that matters stays inside the IG 4:5 band (about y285 to y1635).
- Captions never sit under a full-screen graphic or on their chin; move them.
- Sound: pops on lands, whooshes on moves. Offer a plan they can prune.

## 6. The bar, and what is out

**Quality, not a house style.** It must look impressively made. Craft is in
the details: texture (grain, paper fibre, halftone), real light and shadow
(soft, low, on the object), weight in the motion (overshoot, squash, stepped
stop-motion when it suits), layered depth.

Out: purple anywhere (it reads as an easy sign of AI; blue is fine); busy animated backgrounds behind a cutout (they expose matte errors like a chair behind the creator: keep them plain, dark hides remnants best); skin smoothing ("too filtered"); letterbox bars for "cinematic captions" (that means fancy type, not bars); paper collage / scrapbook looks; flat simple vector shapes or clip-art; slam-in stamp text; hand-drawn
circles and underlines over cards; a colour glow or vignette pooled in the
middle of the background (flat ground plus grain instead; glows that belong to
an object are fine); image-generator art (Higgsfield, Arcads) unless asked;
retired looks the brand sheet lists.

**Check before the creator sees it:** render a contact sheet of each graphic's key
frames and look at it full size. Does each one do its job without the
captions? Is anything flat, cramped, clipped by the IG crop, or covering their
chin? Does every hit land on its word?

## 7. Capabilities worth having

A menu, not a checklist. All doable in Remotion in the brand sheet's theme unless noted:

- Cinematic type: frame-filling serif words, word behind head, video inside
  letters (text mask), script-page cards, title cards with timecodes.
- Proof: real screenshots that pop, zoom to the key line and get highlighted;
  metric cards; a wall of their past reels.
- Product: redrawn UI that types and reacts; phone mockups playing a flow;
  instruction or ticket cards; keyboard keycaps for shortcuts; app icons
  popping in and getting struck out.
- Editing showcase: film strips of raw footage with cuts marked; before and
  after colour grades on the live footage; a storyboard of frames assembling;
  the edit's own review page shown as an insert.
- Illustration: storybook scenes, drawn portraits with callouts, hero objects,
  data fields from real figures, a mascot or object rebuilt in 3D voxels, flat
  2D and pencil.
- Transitions: whip blur, match cut into a colour field, iris.
- Via HyperFrames, one asset at a time (`hyperframes-hybrid.md`): shader
  gradients and transitions, Three.js 3D, liquid glass.

## Tools

- A shot-recipe library, if the creator has one installed (camera, data,
  effects, transitions, typography, UI entrances): browse the matching
  category when designing a move; name recipes when pitching.
- Halftone cutouts: background-remove a still (`npx hyperframes
  remove-background img.png -o cut.png`), cut a clean scissor line, halftone
  it in Python with a 45° dot screen and a cream outline.

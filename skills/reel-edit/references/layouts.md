# The five layouts

Every reel segment uses one of these. Switch layouts only on the creator's own
cuts, and keep captions in the position each layout prescribes.

| # | Layout | Top of frame | Bottom of frame | Captions (baseline) |
| --- | --- | --- | --- | --- |
| 1 | **Talking head** | the take, full frame | | on the fuzzy top of the mic, ~40-50px below the windscreen's highest top |
| 2 | **50/50 split** | graphic or recording, top half | the take, bottom half | slightly above the middle line |
| 3 | **Full-screen motion graphic** | the graphic owns the frame | | same spot as the talking head; keep that band clear in the graphic |
| 4 | **Two-thirds split** (use 4b) | graphic or recording, full-bleed top | the take in a full-width panel with rounded top corners, whole head inside | just above the panel edge, colour switched by background |
| 5 | **Full screen + silhouette** | graphic or recording owns the frame | a small cut-out of the creator, bottom-left / centre / right | just above the cut-out's head, centred |

Layout 2 is built in `split-screen-from-full-frame.md`. Layout 5 (and the
older 4a) need a person matte of the segment (`background-removal.md`). Render the matte for
exactly the frames that use it, as its own clip, so the matte's frame 0 is the
segment's first frame (`<Sequence from={segmentStart}>`).

---

## 4. Two-thirds split

**Use 4b below by default.** 4a is the older breakout version, kept for
reference.

### 4a. Card with head breakout (superseded)

The
reference is the creator-style "graphic on top, me at the bottom" look: the
top two thirds belong to the screen recording or motion graphic, the bottom
third is the take in a rounded card, and the head pops out above the card's
top edge.

```
CARD   = { x: 24, top: 1290, r: 56 }    // full width minus 24px gutters, bottom corners off-frame
S      = 0.96                           // the take's scale: the smallest that still fills the card's width
VX     = (1080 - 1080 * S) / 2
VY     = 1205 - capTop * S              // cap top lands ~85px above the card edge
FOCUS  = 700                            // the graphic centres here (IG band is y285-1635)
```

Layers, bottom to top:

1. **The graphic or recording**, full width, filling y0 to the card top. A
   light app-matching ground (`#FDFDFD` for ElevenLabs) behind screen content.
   Centre what matters on `FOCUS`; content above y285 is outside the grid
   crop.
2. **The card**: a `div` at `CARD` with `overflow: hidden`, `border-radius`,
   a soft upward shadow, holding the take as an `OffthreadVideo` at scale `S`,
   offset by `(VX - CARD.x, VY - CARD.top)`. This carries the audio.
3. **The breakout**: the matte `.mov` at the same `VX, VY, S`, inside an
   `AbsoluteFill` clipped to
   `inset(0 CARD.x (1920 - CARD.top - CARD.r) CARD.x)`, so only the head above
   the card edge (plus the corner radius) draws. Inside the card it would be
   pixel-identical anyway.
4. **Captions** at baseline `capTop' - 40` (y1165 when the cap sits at y1205).

Measure the cap top across the segment's frames first. If it moves more than
~30px, set `VY` from its highest point so the head always clears the edge.

The bottom third falls mostly below the Instagram 4:5 crop (y1635), so in the
grid preview only the cap and eyes show. That is expected for this layout.

---

### 4b. Full-width rounded panel, head inside (the default)

Settled after three rounds of creator notes. The skill
ships it as `components/TwoThirdsPanel.tsx` (the panel, `isLight` and
`SplitCaption`); copy it into `src/shared/` the first time a video needs it.
Measure the cap top first (`capTop`, source px).

```
GA         = 1400                      // graphic area: the recording, full-bleed, y0-1400
TAKE_Y     = 1205 - capTop             // the take at 1:1, cap top lands at y1205
PANEL_TOP  = 1165                      // ~40px above the cap: the WHOLE head sits inside
PANEL_R    = 110                       // big rounded top corners, full width (no side gutters)
CAPTION_Y  = PANEL_TOP - 35            // baseline just above the panel edge (~y1130)
```

Layers, bottom to top:

1. **The graphic or recording**, full-bleed across y0-1400 with the
   Screen Studio camera (`screen-recordings.md`): zooms and pans that follow
   what the creator is saying, our own cursor, and plain highlight rings. Hide browser
   chrome with a fill over the source rows above the page.
2. **The panel**: the take at 1:1 inside
   `clipPath: path('M0 1920 L0 {T+R} Q0 {T} {R} {T} L{1080-R} {T} Q1080 {T} 1080 {T+R} L1080 1920 Z')`,
   under a soft upward shadow (`drop-shadow(0 -8px 24px rgba(0,0,0,0.28))`)
   with a faint white rim gradient on the edge (40px, 0.28 to 0).
3. **Captions** (see `captions.md`, "Caption colour by background"): measure
   the ground with `scripts/caption-tone.py` off a caption-free render of the
   segment, then `SplitCaption` with `isLight(chunk, lum)`.

Rejected on the way here (do not reintroduce unless the brand sheet asks):

- Black side gutters around the take (the old 24px card).
- An arch across the top edge.
- The reference screenshots' light stage, centred landscape card and enlarged
  head: only their **panel edge** was the point.
- A matte breakout: its soft edge made the top of the hat fuzzy, and any edge,
  shadow or rim clipped above the panel cut across the head.
- Too much gap between cap and edge (75px was too much; ~40px is right).
- An on-screen text hook: not used on two-thirds videos.
- Text labels on highlight rings ("237,918 words dictated"): the ring alone.
- Check-mark pills over feature names.

Motion rules for the top area: every second of a graphics stretch moves
(no dead air); content that must read in the IG grid stays in y300-875.

## 5. Full screen + silhouette

The skill ships it as `components/Silhouette.tsx`; copy it into `src/shared/`
when a video needs it.
The graphic or screen recording fills the whole frame; the creator is a matte
cut-out with no background, scaled down and standing at the bottom edge.

```
SIL_S   = 0.55                          // cut-out scale
SIL_TOP = 1240 - capTop * SIL_S         // cap top at y1240; the source's bottom edge meets the frame's
spots   = { left: cx 270, centre: cx 540, right: cx 810 }   // cut-out centre x
left    = cx - 1080 * SIL_S / 2
```

- Draw the matte `.mov` (`transparent muted`) last before captions, with
  `filter: drop-shadow(0 12px 28px rgba(0,20,50,0.35))` so it sits on light
  or busy backgrounds.
- The audio comes from the take mounted as `<Audio>` (the video itself is
  not shown in this layout).
- Moving between spots: spring the centre x over ~12 frames on a cut or a
  beat. Do not drift it continuously.
- Keep the graphic's important content above y1180; the cut-out covers the
  bottom corner and captions sit at baseline ~y1185.
- Screen recordings framed for the two-thirds split leave page edges visible
  near the bottom. Re-frame them for full height (or put them in a card on a
  brand plate) when using this layout.

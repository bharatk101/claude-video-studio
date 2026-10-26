# The text hook

The creator's on-screen hook, the line that frames the video in the first
seconds ("How to start content / if you're shy"). It is Instagram's native
text style, not a caption: it sits still, above the head, from the first frame.

The component ships with the skill (`components/TextHook.tsx`). Copy it to
`src/shared/TextHook.tsx` if the project does not have it yet, never hand-roll it:

```tsx
import { TextHook } from "../shared/TextHook";

<Sequence from={0} durationInFrames={FIRST_FULL_SCREEN} layout="none">
  <TextHook lines={["How to start content", "if you're shy"]} widths={[792, 496]} top={300} />
</Sequence>
```

## The look

- **Font:** the caption font (Inter), weight **600**, 78px, line height 1.15,
  letter spacing -1. Not 800: the creator found extra bold too heavy.
- **Shape:** ONE outline traced round all the lines (`hookPath`). Corners are
  tight (radius 12). Where a line is narrower or wider than the one above, the
  inside corner **flares outward** (or runs straight). Separate rounded boxes
  per line pinch inward at the join, which the creator rejected.
- **No animation.** It is on screen from frame 0, like a native text sticker.

## Three variants

| `variant` | Text | Background |
| --- | --- | --- |
| `"white"` (default) | black | white outline |
| `"black"` | white | black outline |
| `"plain"` | white with a black outline, same as the captions (10px stroke behind the fill) | none |


## Placement and timing

- Above the head, inside the IG band: `top` around y300 (two lines end ~y510).
  Measure the cap top first and keep at least ~30px clear above it, unless
  something else needs that space.
- **In a 50/50 split it goes just below the seam, over the hair**: `top`
  about 40px under the seam (y1000 with the seam at 960), so two lines end
  above the eyebrows. Never in the top pane,
  even when it's free. Measure the hair and eyebrow rows of the bottom pane
  first; captions stay at the seam above it.
- From frame 0 until the first full-screen graphic or a layout change, unless
  the creator says otherwise.
- If a logo or graphic also appears above the head while the hook is up, move
  that graphic down (overlapping the cap is fine), never the hook.
- Break lines where the creator's phrasing breaks, roughly balanced; keep each
  line under ~880px wide.

## Widths

The outline needs each line's box width. Measure it, don't guess:

1. Render one frame of the `"measure"` variant with the real lines. Projects
   from the starter template already register it as `HookMeasure`:
   `npx remotion still src/index.ts HookMeasure "$TMPDIR/m.png" --props='{"lines":["How to start content","if you'"'"'re shy"],"top":300}'`
   (otherwise register a one-frame composition that draws
   `<TextHook lines={...} widths={[0, 0]} top={300} variant="measure" />`).
2. `python3 ${CLAUDE_SKILL_DIR}/scripts/measure-hook.py "$TMPDIR/m.png" <top> <lineCount>`
3. Paste the printed widths into `widths`.

Changing the wording means re-measuring.

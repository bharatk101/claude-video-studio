# Split screen from a full-frame take

The creator filmed a normal full-screen talking head but wants the split
format: a graphic in the top half, them in the bottom half. No re-shoot and no
manual prep. Crop and scale the take into the bottom pane in code.

## 1. Pick the segment

Prefer an uncut stretch. Each of the creator's cuts usually changes the
framing, so every shot needs its own crop (step 4). Note the cut frames before
choosing.

## 2. Measure the head across every frame, not one

Heads move while talking. On a 5-second test the cap top travelled 34 px; a crop
set from a single frame can clip it on another.

Measure, per frame:

- **top of the head or hat** (min and max over the segment)
- **horizontal centre of the head** (its range)
- **eye line and mouth**, roughly, to sanity-check the framing

The most general way is the person matte from the background-removal step
(`references/background-removal.md`): the first alpha row above a threshold is
the top of the head. When the creator wears something distinctive, a colour key
is faster and needs no preprocessing:

```python
a = np.array(Image.open(frame).convert("RGB")).astype(int)
r, g, b = a[..., 0], a[..., 1], a[..., 2]
cap = (b > 140) & (b > r + 50) & (b > g + 25)          # e.g. a blue cap
rows = np.where(cap.sum(1) > 30)[0]
top = rows.min()
cols = np.where(cap[top:top + 200].sum(0) > 3)[0]      # head width near the top
```

## 3. Solve the crop

The bottom pane is the frame below the seam (`SEAM = 960` for an even split,
or the bar height the creator uses in their own filmed split screens, which is
the best reference if they exist). Targets that matched hand-filmed splits:

- head top **25-60 px under the seam** across the whole segment
- eyes around **y1290** (~330 px under the seam)
- face roughly centred horizontally

Then:

```ts
const S = 1.1;                                   // zoom; keep it <= ~1.3
const SRC_Y0 = headTopMin - 25 / S;              // source row that lands on the seam + 25px
// check: SEAM + (headTopMax - SRC_Y0) * S stays under SEAM + 60
const visibleW = 1080 / S;
const SRC_X0 = clamp(headCentreX - visibleW / 2, 0, 1080 - visibleW);
```

**Scale limit:** past about 1.3x the upscale goes visibly soft. If a take is
framed too tight to hit the targets under that, say so rather than forcing it.
Wide takes with headroom above the head need only ~1.1x.

## 4. Build the pane

```tsx
const Head: React.FC = () => (
  <div style={{ position: "absolute", left: 0, top: SEAM, width: 1080, height: 1920 - SEAM, overflow: "hidden" }}>
    <OffthreadVideo
      src={staticFile("recordings/segment.mp4")}
      style={{ position: "absolute", width: 1080 * S, height: 1920 * S, left: -SRC_X0 * S, top: -SRC_Y0 * S }}
    />
    {/* a soft shadow off the seam so the halves read as stacked */}
    <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: 26,
      background: "linear-gradient(rgba(0,0,0,0.28), rgba(0,0,0,0))" }} />
  </div>
);
```

Pre-cut the segment to its exact frame count with its audio (see
`SKILL.md`, Ingest). If it ends mid-sentence, fade the last ~0.15s:
`-af "afade=t=out:st=<dur-0.15>:d=0.15"`.

For a stretch containing cuts, wrap each shot in its own `<Sequence>` with its
own measured `S`, `SRC_X0`, `SRC_Y0`.

## 5. The top half

The band is y0 to the seam. Content that must survive the Instagram 4:5
preview lives in **y285 to ~930**. Fill it with a graphic that illustrates what
is being said in that stretch, anchored to word starts like any other overlay.

## When a fixed crop is not enough

A fixed crop suits a seated take. If the head-top range is larger than the
seam margin allows (the creator leans in, stands, walks), the crop has to
follow the head: measure per frame, smooth it (a moving average over ~9
frames), and drive `SRC_X0`/`SRC_Y0` from that table. Check the result with
`scripts/camera-check.py` logic so the follow never jitters.

## Verify

Render the segment with `--sequence`, confirm the head never crosses the seam
on any frame, and check one frame at full size for sharpness.

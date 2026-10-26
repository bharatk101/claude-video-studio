# Screen recordings

## The aspect problem

A screen recording is landscape, typically 1.6:1. The frame is 0.5625:1. Any
window wider than `sourceHeight * 0.5625` is taller than the recording itself.
For a 3024x1898 capture that is **1068 source px**, which is usually too narrow
to hold a full line of UI text.

Three ways out, in order of preference:

1. **Bleed against the app's own background.** Most app windows have a perfectly
   flat row of one colour at their very top and bottom edges. Measure it
   (`numpy` mean and std over the first and last few rows; std should be 0), set
   the composition background to that exact colour, and let the window hang off.
   The overflow is invisible and reads as the app's own padding.

   **Watch for the app changing that colour.** When a modal opens, most apps
   dim the whole window to a flat grey, and a fixed fill then shows as bright
   bands above and below. Sample the edge rows on every frame across the
   change (they stay flat, zero variance, at each step) and drive the fill
   from a per-frame table:

   ```tsx
   const DIM: Record<number, number> = { 133: 197, 134: 167, 135: 150, 136: 144, 137: 141 };
   const fill = (f: number) => (f <= 132 ? "#FCFCF9" : `rgb(${DIM[f] ?? 140},${DIM[f] ?? 140},${DIM[f] ?? 140})`);
   ```

   A recording of a **whole desktop** (menu bar, dock, wallpaper) has no flat
   edge, so keep that window inside the source, or accept a thin letterbox.
2. **Split screen**, with the recording in a band and the speaker below. Lets the
   recording run roughly 35% larger.
3. **Crop into the content** and accept losing the edges. Only acceptable when
   the region of interest is genuinely narrow, never for body text.

Measure the text you need to show before choosing a window width:

```python
im = np.array(Image.open('frame.png').convert('L')).astype(int)
dark = im < 140
cols = np.where(dark[y0:y1, x0:x1].any(axis=0))[0]
print('text spans', x0 + cols.min(), 'to', x0 + cols.max())
```

## The camera

Express keyframes in **source pixels**: window width plus the centre point.

```tsx
type Key = { f: number; w: number; cx: number; cy: number };

const camAt = (keys: Key[], f: number): Key => {
  if (f <= keys[0].f) return keys[0];
  const last = keys[keys.length - 1];
  if (f >= last.f) return last;
  let a = keys[0], b = last;
  for (let i = 0; i < keys.length - 1; i++)
    if (f >= keys[i].f && f <= keys[i + 1].f) { a = keys[i]; b = keys[i + 1]; break; }
  const t = interpolate(f, [a.f, b.f], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });
  return { f, w: a.w + (b.w - a.w) * t, cx: a.cx + (b.cx - a.cx) * t, cy: a.cy + (b.cy - a.cy) * t };
};
```

Render it by scaling the whole source and offsetting, with the pane clipping:

```tsx
const c = camAt(keys, frame);
const wh = (c.w * H) / W;                       // window height in source px
const cx = clamp(c.cx, c.w / 2, SW - c.w / 2);
const cy = clamp(c.cy, wh / 2 - MAX_BLEED, SH - wh / 2 + MAX_BLEED);
const k = W / c.w;                              // source px -> frame px

<AbsoluteFill style={{ background: APP_BG, overflow: "hidden" }}>
  <OffthreadVideo src={staticFile(src)} muted style={{
    position: "absolute",
    width: SW * k, height: SH * k,
    left: W / 2 - cx * k, top: H / 2 - cy * k,
  }} />
</AbsoluteFill>
```

## The clamp trap

**Do not** clamp the centre with a hard "stay inside the source" rule:

```tsx
const cy = wh <= SH ? clamp(c.cy, wh / 2, SH - wh / 2) : c.cy;   // WRONG
```

That range collapses to the single value `SH / 2` at the width where the window
height equals the source height. Any zoom crossing that width snaps the framing
in one frame. Measured on a real edit: a 100 source px jump, 85 output px, on a
single frame. The creator spotted it immediately.

Clamp against a fixed bleed allowance instead, which stays continuous:

```tsx
const MAX_BLEED = 400;
const cy = clamp(c.cy, wh / 2 - MAX_BLEED, SH - wh / 2 + MAX_BLEED);
```

## Check the path numerically

Before rendering, replay the keyframes and print the worst per-frame on-screen
displacement: `scripts/camera-check.py`. A lateral pan over fine UI text reads as
smooth at roughly **under 25 output px per frame**. A version that peaked at 52
was rejected as "a sharp jump"; the same move at 24 was accepted.

This check takes a second and catches both the clamp snap and a pan that is
simply too fast.

For a long move, ease the keyframe that ends it with a **sine** curve rather
than cubic: `Easing.inOut(Easing.sin)` peaks at roughly half a cubic's speed
over the same span, which is often the difference between a whip and a glide.

Also trim each clip so the thing being shown is already on screen on its first
frame. A clip that opens on the moment *before* a photo loads reads as a
flash of the wrong screen.

## Cutting the clips

Pre-cut every clip to the **exact frame count** its segment needs, at 30fps, in
native resolution:

```bash
ffmpeg -y -ss 0.90 -i "raw.mov" -frames:v 132 -an \
  -c:v libx264 -preset slow -crf 16 -pix_fmt yuv420p -r 30 clip.mp4
```

Prefer **one continuous take with one eased camera path** over several cut
ranges. Cutting a screen recording into pieces produces jumps that read as
jitter, and a stop-then-fast-move reads as a jerk even when each segment is
eased. If the source has dead air, choose a window that contains the beats
rather than stitching.

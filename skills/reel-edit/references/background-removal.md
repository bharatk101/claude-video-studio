# Graphics behind the speaker (optional)

Remotion alone can only put graphics in front of the speaker. A person matte
lets a graphic pass *behind* their head: a cap brim cutting across a folder,
lines that end at the silhouette instead of crossing the face.

HyperFrames ships a local human-segmentation model (no upload, no API key) that
works as a standalone preprocessing step. Nothing else about the Remotion
workflow changes.

```bash
npx hyperframes telemetry disable      # it collects usage data by default
npx hyperframes remove-background clip.mp4 -o clip-subject.mov --quality best
```

## Use the `.mov`, not the `.webm`

The WebM output is VP9 with its alpha stored as container side data. ffmpeg's
default decoder ignores it and Remotion's compositor renders it as fully
transparent. The **ProRes 4444 `.mov`** carries alpha in the pixel format
(`yuva444p12le`) and works directly:

```tsx
<AbsoluteFill>
  <OffthreadVideo src={staticFile("recordings/take.mp4")} />
</AbsoluteFill>
<Graphic />                                  {/* reads as behind the speaker */}
<AbsoluteFill>                               {/* the wrapper is required */}
  <OffthreadVideo src={staticFile("cutouts/clip-subject.mov")} transparent muted />
</AbsoluteFill>
```

## Costs and limits

- **Speed:** about 5-6 fps with CoreML on Apple silicon; a 50s take is ~5 min,
  once, as preprocessing.
- **Size:** ProRes 4444 is ~340 MB per 7s. Cut out only the stretches that
  need it, never the whole take.
- **The matte grabs whatever is behind and close in tone to the person,**
  typically a chair headrest, and includes it on some frames and drops it on
  others. Measure it: alpha coverage per frame, and flag frame-to-frame jumps
  over ~1 percentage point. The head, cap and hands stay stable; keep behind
  graphics interacting with those, and away from the shoulder band.

# Captions

Captions are where creators notice defects first, because they can hear the
mismatch. Treat timing as a measurement problem, not a formatting one.

## Style

**The caption treatment comes from the brand sheet** (`brand/BRAND.md`):
which style is the default, any emphasis-word option, and where the line sits
on that creator's framing. Without a sheet, use the outlined TikTok caption
below (`components/Caption.tsx`), which also suits brand deals.

Rules that hold whatever the style:

- 1 to 3 words, casual lowercase. A chunk appears and disappears with its
  words: no pop, no motion, no sound on captions.
- Pick the treatment per chunk by measuring the caption band
  (`scripts/caption-tone.py`), never by eye; one treatment per chunk.
- **Never on the chin**: a line over the chin sits too close to the mouth.
  Measure chin and mouth per take.
- On a talking head with a handheld or clip mic, the line sits on the fuzzy
  top of the windscreen (below). If the face sits high in the frame and that
  line runs over the overlays, drop it just below the mic instead; check where
  it falls against the overlays before choosing.
- Never re-derive the outlined look (a thicker HTML text-stroke, a smaller
  size, a lower spot). It is the TikTok caption, exactly as specified.

```tsx
<svg width={1080} height={1920} style={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
  <text
    x={540} y={CAPTION_Y} textAnchor="middle"
    fontFamily={fontFamily} fontWeight={800} fontSize={78} letterSpacing={-2}
    fill="#ffffff" stroke="#000000" strokeWidth={10}
    style={{ paintOrder: "stroke" }}
  >
    {line}
  </text>
</svg>
```

**Use SVG `stroke` with `paintOrder: "stroke"`. Never `WebkitTextStroke`**, which
fills the counters of letters like a and o with ink.

Casing is casual: everything lowercase except proper nouns and the pronoun "I".
Keep a small dictionary of exceptions rather than special-casing inline.

```tsx
const KEEP: Record<string, string> = { i: "I", "i'll": "I'll", ai: "AI", claude: "Claude" };
const casualCase = (w: Word): Word => {
  const core = w.text.replace(/[,.?!]+$/, "");
  const tail = w.text.slice(core.length);
  return { ...w, text: (KEEP[core.toLowerCase()] ?? core.toLowerCase()) + tail };
};
```

### Caption colour by background

When most of the background behind the caption is light (screen recordings,
white app UI, light motion graphics), white captions disappear. Switch per
chunk:

- **Dark ground:** white text, black outline (the default above).
- **Light ground:** black text (`fill="#000"`), **white** outline
  (`stroke="#fff"`), same 10px stroke and `paintOrder`.

Decide by measurement, not by segment: render the composition once with
captions hidden (a `hideCaptions` prop) at `--scale=0.25`, take the mean
luminance of the caption band (baseline -75 to +20, x150-930) per frame, save
it as JSON next to the assets, and give each chunk the colour of its average
(light above ~140 of 255). One colour per chunk, so a line never changes
colour while it is on screen. Re-measure whenever the layout or caption Y
moves.

## Placement

On a talking head the line sits **on the fuzzy top of the mic windscreen, just
under the chin**. Measure the windscreen in the take (it moves between setups)
and put the baseline about **40-50px below the highest position of its top
edge**, so the text overlaps the top of the fuzz. Clear above it reads too high;
under it reads too low. Measured on real takes:

| Windscreen top across shots | Baseline that landed |
| --- | --- |
| y1314-1385 | y1380 |
| y1340-1400 | y1392 |

Do not reuse a Y from a previous video.

Rules that come up constantly:

- Under a **full-screen graphic**, reposition the caption into whatever band the
  graphic leaves clear. Never drop it.
- Over a **screen recording**, drop it below the app content, but not so far that
  it leaves the 4:5 safe band without reason.
- In the **two-thirds split** (layout 4b), sit just above the panel edge
  (~35px above it), centred, with the colour rule above.
- In a **split screen**, sit just below the seam, around the speaker's head.
  If the graphic band above the seam is yours to fill, the line can sit just
  above the seam instead; lift the graphic so the two never overlap.

### Takes that change format

Many takes switch between a talking head, a green screen, b-roll, screenshots
and screen recordings. Treat each stretch as its own format:

1. Measure a caption line for every format: where it is readable and where it
   will not cover what matters in that shot. Busy backgrounds (a green-screen
   collage, a photo) get a heavier outline and a soft dark halo:
   `filter: drop-shadow(0 0 14px rgba(0,0,0,0.65))`.
2. **Never let a caption run across a format change.** Break the chunk at the
   boundary and clamp its end frame to it, or a line jumps position mid-read.
3. A word whisper places one or two frames **before** a cut belongs to the shot
   after it. Snap its start onto the cut, or it flashes for a frame in the
   wrong position.
4. **Exception: two adjacent shots that are one continuous thought** (b-roll of
   a laptop straight into a screenshot of the same post) should share **one**
   line so it never moves. Find the band that is clear in *both* shots, then
   measure the rendered caption's actual ink, outline included, against both
   edges by diffing the render against the source. If the band is shorter than
   a full line, drop the font a few px for that stretch (78 to 72 fitted an
   87px band with ~4px clearance each side).
5. Where the words are a list ("a cover image, detailed slides, and 17k
   views"), set the chunks by phrase, not by word count, so a comma never
   splits "cover image" from "detailed".

## Chunking

One to three words, at most about 17 characters.

```tsx
for (const w of words) {
  const candidate = [...cur, w].map((x) => x.text).join(" ");
  if (cur.length >= 3 || (cur.length > 0 && candidate.length > 17)) flush();
  cur.push(w);
  if (/[.?!]$/.test(w.text)) flush();
}
```

A line runs **from its first word's start to its last word's end**, plus about
3 frames, with each word's end capped at `startMs + 550ms`:

```tsx
chunks.push({
  from: toFrames(cur[0].startMs),
  to: toFrames(Math.min(last.endMs, last.startMs + 550)) + 3,
  text: cur.map((w) => w.text).join(" ").replace(/\.+$/, ""),
});
```

**Never hold a line until the next one starts.** It will linger through every
pause and that is exactly what gets flagged.

At playback, let the last matching chunk win, so overlapping lines resolve to
the newest:

```tsx
let cur = null;
for (const c of CHUNKS) if (frame >= c.from && frame < c.to) cur = c;
```

Kill a line at a cut only when the cut actually starts a new line. Compute that
rather than hardcoding it:

```tsx
const HARD_CUTS = CUTS.filter((c) => CHUNKS.some((ch) => ch.from >= c - 1 && ch.from <= c + 3));
for (const b of HARD_CUTS) if (cur.from < b && frame >= b) return null;
```

A mid-sentence cut, for example into b-roll, should let the line run through.

## Re-timing, when the creator says captions are behind

A single full-file whisper pass is not accurate enough. Inside a long stretch of
continuous speech the word timings drift late, by up to a second, and whisper
pads the last word of a sentence out to the start of the next one.

Use `scripts/retime-captions.py`. The method:

1. Cut the audio into **dense overlapping windows**, 6 seconds long stepping 2 to
   2.5 seconds.
2. Transcribe each with DTW token timestamps:
   `whisper-cli -m ggml-small.bin -f win.wav -ml 1 -sow -dtw small -oj`
3. From each window keep only the words whose start falls in its **accurate zone**,
   roughly `[start + 1.1s, start + 3.6s]`: past the lead-in, before the drift.
4. Align each window to the approved word list with
   `difflib.SequenceMatcher` on normalised words, and let every window **vote**.
   A word's time is the **median** of its votes.
5. Words with no votes, typically the ones a fix dictionary rewrites, get
   **interpolated between their matched neighbours**. Never leave them on their
   old value, which is the bug that makes a partial re-time look like it worked.

Then verify. Build the chunks and check each chunk's start against a 10ms RMS
voice envelope with a threshold of about `percentile20 + 8 dB`. Every start
should be inside voice or within about 4 frames before an onset. A chunk start
in the middle of silence is a real defect.

Finally, **re-derive any graphic cue that hangs off a word**. If the pill appears
when the URL is spoken, and the URL moved 9 frames, so does the pill.

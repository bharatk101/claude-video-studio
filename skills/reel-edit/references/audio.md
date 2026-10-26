# Audio

## Music beds

**Use the creator's original file and trim in code.** Never write trimmed or
loudnormed copies into the creator's music pack. `trimBefore`
plays the original from any point (verified on Remotion 4.0.475):

```tsx
<Audio src={staticFile("music pack/Original Song.mp3")}
  trimBefore={Math.round(START_S * 30)}                      // where in the track to start
  volume={(f) => GAIN * interpolate(f, [0, 5, DUR - 36, DUR - 1], [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" })} />
```

Choose where in the track to start by profiling it, not by starting at zero:

```bash
ffmpeg -v error -i track.mp3 -ac 1 -ar 8000 -f s16le - | python3 -c "...0.5s RMS envelope..."
```

Many tracks open with a sparse intro that vanishes under a voice. Starting on the
full-band downbeat usually serves a reel better; to land a drop on a cut,
`START_S = dropTime - cutFrame / 30`.

If the chosen window swings in level (one track moved 17 dB across 50 seconds),
even it out with the `volume` curve (keyframes from the measured envelope)
rather than a loudnormed copy.

**Target the bed at roughly 15 to 18 dB under the voice**, which lands around
-31 dB when the voice sits near -15 dB. Set the gain from the measured mean of the window you
use rather than guessing:

```
gain = 10 ** ((targetDb - measuredMeanDb) / 20)
```

## Sound effects

Every sound file carries silence before its hit. Fire each cue early by that
file's own lead so the hit lands on the frame:

```tsx
type Cue = { at: number; f: string; v: number };
const LEAD: Record<string, number> = { "pop.mp3": 6, "woosh 2.mp3": 3, "mouseclick.mp3": 2 };

const Sfx = () => (
  <>{CUES.map((c, i) => {
    const from = Math.max(0, c.at - (LEAD[c.f] ?? 0));
    return (
      <Sequence key={i} from={from} durationInFrames={DUR - from}>
        <Audio src={staticFile(`sound pack/${c.f}`)} volume={c.v} />
      </Sequence>
    );
  })}</>
);
```

Measure the lead off the waveform rather than trusting a table:

```python
pk = np.max(np.abs(a))
onset = np.argmax(np.abs(a) > pk * 0.12) / sr      # lead, in seconds
```

If a stock file is too quiet to carry its moment, make a louder copy rather than
pushing `volume` past 1:

```bash
ffmpeg -y -i quiet.mp3 -af "volume=14dB,alimiter=limit=0.89" -c:a libmp3lame -b:a 256k loud.mp3
```

Propose sound effects as a list with frames and let the creator prune. They
usually cut about a third, and crowding two cues within a second of each other
is the most common reason.

## Verification

Never assume a bed or a cue made it into the render. Subtract the source voice
out of the render and inspect the residual: `scripts/verify-audio.py`.

The method: find the encoder delay by correlating the first few seconds (AAC
typically 2048 samples, sometimes 2032), scale the source to best fit, subtract,
and what remains is everything you added.

What good looks like:

- **voice gain about 1.0.** Anything else means the voice was altered.
- **bed 15 to 18 dB below the voice**, steady across the video.
- **every cue visible as a peak** 9 to 20 dB above the bed, at its frame.
- **render mean within 0.1 dB of the source mean**, and no new clipping.

import React from "react";
import { AbsoluteFill, OffthreadVideo, Sequence, interpolate, staticFile } from "remotion";

// Jump cuts (scripts/jump-cuts.py): plays only the kept spans of a take, back to back, with an optional
// punch-in per span (scale) that hides the jump. Copy into src/shared/ when a video first needs it.
//
//   import jc from "../../public/recordings/take.jumpcuts.json";
//   import words from "../../public/recordings/take.cut.words.json";   // captions on the edited timeline
//   <JumpCut src="recordings/take.mp4" keep={jc.keep} />                // composition length: jc.outFrames
//
// Each span's audio fades over ~1 frame at both ends so cuts don't click. Graphics, captions and cues all
// live on the EDITED timeline: anchor them to take.cut.words.json, never to the original words.json.

export type KeepSpan = { from: number; to: number; outFrom: number; scale?: number };

const Span: React.FC<{ src: string; span: KeepSpan; originY: number }> = ({ src, span, originY }) => {
  const len = span.to - span.from;
  const fade = (f: number) =>
    interpolate(f, [0, 1, Math.max(1.5, len - 1), len], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const s = span.scale ?? 1;
  return (
    <AbsoluteFill style={{ transform: s !== 1 ? `scale(${s})` : undefined, transformOrigin: `50% ${originY}%` }}>
      <OffthreadVideo src={staticFile(src)} trimBefore={span.from} volume={(f) => fade(f)} />
    </AbsoluteFill>
  );
};

export const JumpCut: React.FC<{
  src: string;
  keep: KeepSpan[];
  /** where the punch-in zooms toward, as % of the frame height (the face: roughly the eye line / 1920) */
  originY?: number;
}> = ({ src, keep, originY = 40 }) => (
  <AbsoluteFill>
    {keep.map((k, i) => (
      <Sequence key={i} from={k.outFrom} durationInFrames={k.to - k.from}>
        <Span src={src} span={k} originY={originY} />
      </Sequence>
    ))}
  </AbsoluteFill>
);

/** Total length of the edit, for the composition's durationInFrames. */
export const jumpCutLength = (keep: KeepSpan[]) => keep.reduce((n, k) => Math.max(n, k.outFrom + k.to - k.from), 0);

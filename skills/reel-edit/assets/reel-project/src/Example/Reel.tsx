import React, { useMemo } from "react";
import { AbsoluteFill, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import { Caption } from "../shared/Caption";
import { TextHook } from "../shared/TextHook";
import { buildChunks, casualCase, chunkAt, cleanWords, hardCuts, type Word } from "../shared/captions";

// The starter reel: a talking-head take, a text hook from frame 0, and outlined captions timed to the transcript.
// Copy this folder per video (src/<Video>/) and register it in Root.tsx. With no `src` it renders a placeholder
// ground so the project works before you have footage.

export type ReelProps = {
  src?: string; //            e.g. "recordings/take.mp4" (transcode .mov/HEVC first; see the skill's Ingest step)
  words: Word[]; //           from scripts/transcribe.mjs
  cuts?: number[]; //         the take's own cut frames (scene detection, see the skill)
  captionY?: number; //       caption baseline, measured per take (on the mic windscreen / under the chin)
  hook?: { lines: string[]; widths: number[]; top: number; until: number };
};

const Placeholder: React.FC = () => {
  const f = useCurrentFrame();
  const a = interpolate(f, [0, 300], [0, 40]);
  return (
    <AbsoluteFill style={{ background: `linear-gradient(${160 + a}deg, #1b2330, #0d0f14 60%)` }}>
      <div style={{ position: "absolute", top: 860, width: "100%", textAlign: "center", color: "#ffffff55", fontFamily: "sans-serif", fontSize: 34 }}>
        put a take in public/recordings/ and set `src`
      </div>
    </AbsoluteFill>
  );
};

export const Reel: React.FC<ReelProps> = ({ src, words, cuts = [], captionY = 1380, hook }) => {
  const frame = useCurrentFrame();
  const chunks = useMemo(() => buildChunks(cleanWords(words).map((w) => casualCase(w)), { cuts }), [words, cuts]);
  const hard = useMemo(() => hardCuts(cuts, chunks), [cuts, chunks]);
  const cur = chunkAt(chunks, frame, hard);

  return (
    <AbsoluteFill style={{ background: "#000" }}>
      {src ? (
        <AbsoluteFill>
          <OffthreadVideo src={staticFile(src)} />
        </AbsoluteFill>
      ) : (
        <Placeholder />
      )}
      {hook ? (
        <Sequence from={0} durationInFrames={hook.until} layout="none">
          <TextHook lines={hook.lines} widths={hook.widths} top={hook.top} />
        </Sequence>
      ) : null}
      {cur ? <Caption words={cur.text.split(" ").map((text) => ({ text }))} y={captionY} /> : null}
    </AbsoluteFill>
  );
};

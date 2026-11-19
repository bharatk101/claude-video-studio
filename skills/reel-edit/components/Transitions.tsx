import React from "react";
import { AbsoluteFill, Easing, Freeze, OffthreadVideo, Sequence, interpolate, staticFile } from "remotion";
import { TransitionSeries, linearTiming, springTiming, type TransitionPresentation } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { slide } from "@remotion/transitions/slide";
import { wipe } from "@remotion/transitions/wipe";
import { flip } from "@remotion/transitions/flip";
import { clockWipe } from "@remotion/transitions/clock-wipe";
import { iris } from "@remotion/transitions/iris";
import { pushCut } from "@remotion/transitions/push-cut";
import type { PlannedClip, PlannedJoin, TransitionPlan } from "./transition-plan";

// Plays a take as clips/sections with Remotion transitions between them (@remotion/transitions, TransitionSeries).
// The timing comes from planTransitions() in transition-plan.ts; copy both into src/shared/ when a video needs them.
//
//   const plan = planTransitions([{ at: 412, type: "slide" }], takeFrames, { words });
//   <TakeWithTransitions src="recordings/reel.mp4" plan={plan} />            // composition length: plan.outFrames
//
// The starter Reel does this for you: pass `transitions` in its props and calculateReelMetadata plans them.

const W = 1080, H = 1920;

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function presentation(j: PlannedJoin): TransitionPresentation<any> {
  switch (j.type) {
    case "slide": return slide({ direction: j.direction });
    case "wipe": return wipe({ direction: j.direction });
    case "flip": return flip({ direction: j.direction });
    case "clock-wipe": return clockWipe({ width: W, height: H });
    case "iris": return iris({ width: W, height: H });
    case "push-cut": return pushCut();
    default: return fade();
  }
}

const timing = (j: PlannedJoin) =>
  j.timing === "spring"
    ? springTiming({ config: { damping: 200 }, durationInFrames: j.frames })
    : linearTiming({ durationInFrames: j.frames, easing: Easing.inOut(Easing.cubic) });

const Clip: React.FC<{ src: string; c: PlannedClip; volume: number }> = ({ src, c, volume }) => {
  const len = c.to - c.from;
  // Overlap joins crossfade the sound with the neighbour. Hold joins need nothing: the sound runs on unbroken
  // (a section join is the same continuous audio; assemble.py already de-clicked clip joins).
  const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
  const vol = (f: number) => {
    let v = volume;
    if (c.fadeIn) v *= interpolate(f, [0, c.fadeIn], [0, 1], clamp);
    if (c.fadeOut) v *= interpolate(f, [len - c.fadeOut, len], [1, 0], clamp);
    return v;
  };
  return (
    <AbsoluteFill>
      <Sequence durationInFrames={len} layout="none">
        <OffthreadVideo src={staticFile(src)} trimBefore={c.from} volume={vol} />
      </Sequence>
      {c.hold > 0 ? (
        <Sequence from={len} durationInFrames={c.hold} layout="none">
          <Freeze frame={len - 1}>
            <OffthreadVideo src={staticFile(src)} trimBefore={c.from} muted />
          </Freeze>
        </Sequence>
      ) : null}
    </AbsoluteFill>
  );
};

export const TakeWithTransitions: React.FC<{ src: string; plan: TransitionPlan; volume?: number }> = ({ src, plan, volume = 1 }) => {
  if (plan.problems.length) throw new Error("Transitions can't render as planned:\n  " + plan.problems.join("\n  "));
  return (
    <TransitionSeries>
      {plan.clips.map((c, i) => {
        const j = plan.joins[i];
        return (
          <React.Fragment key={i}>
            <TransitionSeries.Sequence durationInFrames={c.to - c.from + c.hold}>
              <Clip src={src} c={c} volume={volume} />
            </TransitionSeries.Sequence>
            {j && j.frames > 0 ? <TransitionSeries.Transition presentation={presentation(j)} timing={timing(j)} /> : null}
          </React.Fragment>
        );
      })}
    </TransitionSeries>
  );
};

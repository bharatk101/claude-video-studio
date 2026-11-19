// Transitions between clips and sections: the timing maths, kept apart from the drawing (Transitions.tsx) so it
// can be checked without a browser. Pure functions, no React. Copy into src/shared/ with Transitions.tsx.
//
// A join is a frame of the TAKE where one clip or section ends and the next begins: an assembled clip boundary
// (kind "clip" in <take>.cuts.json) or a pause between two points (pauseBefore(words, i)).
//
// Two modes, because talking-head reels and b-roll montages need different things:
//   "hold"    (default) the outgoing clip's last frame is held while the next clip plays in, live, with its
//             sound. Nothing is lost and nothing moves: the reel stays exactly as long as the take, and the
//             transcript, cuts and captions need no re-timing. Right for anyone speaking.
//   "overlap" Remotion's usual crossfade: both clips play during the transition and their sound crossfades,
//             so the reel gets shorter by the transition's length. Right for b-roll and music montages. Words
//             spoken during an overlap are flagged: they'd be talked over.

import type { Word } from "./captions";

export type TransitionType = "fade" | "slide" | "wipe" | "flip" | "clock-wipe" | "iris" | "push-cut" | "none";
export type TransitionMode = "hold" | "overlap";
export type Direction = "from-left" | "from-right" | "from-top" | "from-bottom";

export type Join = {
  at: number; //                  take frame where the next clip/section starts
  type?: TransitionType; //       default "fade"; "none" is a plain cut
  frames?: number; //             default 9 (0.3 s at 30 fps)
  mode?: TransitionMode; //       default "hold"
  direction?: Direction; //       slide / wipe / flip; default "from-right"
  timing?: "ease" | "spring"; //  default "ease"
};

export const TRANSITION_DEFAULTS = { type: "fade", frames: 9, mode: "hold", direction: "from-right", timing: "ease" } as const;

export type PlannedJoin = Required<Join> & { outAt: number }; // outAt: where the next clip starts in the reel
export type PlannedClip = { from: number; to: number; outFrom: number; hold: number; fadeIn: number; fadeOut: number };
export type TransitionPlan = {
  takeFrames: number;
  outFrames: number; //  the reel's length
  clips: PlannedClip[]; // from/to: take frames [from, to); outFrom: where it starts in the reel; hold: frozen frames
  joins: PlannedJoin[]; //   added after it; fadeIn/fadeOut: sound crossfade frames (overlap mode only)
  problems: string[]; // the plan can't render as asked: fix before rendering
  warnings: string[]; // it renders, but look at these
};

const fr = (ms: number, fps: number) => (ms / 1000) * fps;

export function planTransitions(joins: Join[], takeFrames: number, opts: { words?: Word[]; fps?: number } = {}): TransitionPlan {
  const fps = opts.fps ?? 30;
  const words = opts.words ?? [];
  const problems: string[] = [];
  const warnings: string[] = [];

  const sorted = [...joins].sort((a, b) => a.at - b.at);
  const js: Required<Join>[] = [];
  for (const j of sorted) {
    const at = Math.round(j.at);
    if (at <= 0 || at >= takeFrames) {
      problems.push(`join at f${j.at} is outside the take (1..${takeFrames - 1})`);
      continue;
    }
    if (js.length && js[js.length - 1].at === at) continue; // same join twice
    const type = j.type ?? TRANSITION_DEFAULTS.type;
    js.push({
      at,
      type,
      frames: type === "none" ? 0 : Math.max(0, Math.round(j.frames ?? TRANSITION_DEFAULTS.frames)),
      mode: j.mode ?? TRANSITION_DEFAULTS.mode,
      direction: j.direction ?? TRANSITION_DEFAULTS.direction,
      timing: j.timing ?? TRANSITION_DEFAULTS.timing,
    });
  }

  const bounds = [0, ...js.map((j) => j.at), takeFrames];
  const clips: PlannedClip[] = [];
  for (let i = 0; i + 1 < bounds.length; i++) clips.push({ from: bounds[i], to: bounds[i + 1], outFrom: 0, hold: 0, fadeIn: 0, fadeOut: 0 });

  js.forEach((j, k) => {
    const a = clips[k], b = clips[k + 1];
    if (j.mode === "hold") a.hold = j.frames;
    else { a.fadeOut = j.frames; b.fadeIn = j.frames; }
  });

  // Each clip must have room for what plays live in it: the incoming transition, plus the outgoing one when that
  // overlaps (a held transition runs on frozen frames added after the clip, so it needs no room).
  clips.forEach((c, i) => {
    const len = c.to - c.from;
    const enter = i > 0 ? js[i - 1].frames : 0;
    const exitLive = c.fadeOut;
    if (len < enter + exitLive + 1) {
      problems.push(`clip ${i + 1} (f${c.from}-f${c.to}, ${len} frames) is too short for its transitions ` +
        `(${enter} in + ${exitLive} out): shorten them or drop a join`);
    }
  });

  let t = 0;
  clips.forEach((c, i) => {
    c.outFrom = t;
    const overlapNext = i < js.length ? js[i].frames : 0; // every transition overlaps its two sequences
    t += c.to - c.from + c.hold - overlapNext;
  });
  const outFrames = t;
  const planned: PlannedJoin[] = js.map((j, k) => ({ ...j, outAt: clips[k + 1].outFrom }));

  // Words against the joins: a join inside a word, or speech under an overlap.
  words.forEach((w, i) => {
    const s = fr(w.startMs, fps), e = fr(w.endMs, fps);
    for (const j of js) {
      if (s < j.at && e > j.at) {
        warnings.push(`join f${j.at} falls inside word #${i} "${w.text}" (f${s.toFixed(1)}-f${e.toFixed(1)}): ` +
          `move it into a pause (pauseBefore)`);
      } else if (j.mode === "overlap" && j.frames > 0 && s < j.at + j.frames && e > j.at - j.frames) {
        warnings.push(`word #${i} "${w.text}" is spoken during the overlap at f${j.at} (±${j.frames}): ` +
          `it gets talked over; use mode "hold" or move the join`);
      }
    }
  });

  return { takeFrames, outFrames, clips, joins: planned, problems, warnings };
}

/** The transcript on the reel's timeline. In "hold" mode it's unchanged; overlaps shift later words earlier. */
export function retimeWords(words: Word[], plan: TransitionPlan, fps = 30): Word[] {
  return words.map((w) => {
    const f = fr(w.startMs, fps);
    const c = plan.clips.find((c) => f >= c.from && f < c.to) ?? plan.clips[plan.clips.length - 1];
    const shiftMs = ((c.outFrom - c.from) / fps) * 1000;
    return shiftMs ? { ...w, startMs: Math.round(w.startMs + shiftMs), endMs: Math.round(w.endMs + shiftMs) } : w;
  });
}

/** Where captions must break in the reel: every join (add these to the take's own cuts, re-timed). */
export const joinCuts = (plan: TransitionPlan) => plan.joins.map((j) => j.outAt);

/** A take frame re-timed onto the reel (for cuts.json frames, cues, graphics). */
export function retimeFrame(frame: number, plan: TransitionPlan): number {
  const c = plan.clips.find((c) => frame >= c.from && frame < c.to) ?? plan.clips[plan.clips.length - 1];
  return frame - c.from + c.outFrom;
}

/** The middle of the pause before word i (take frames): where a "next point" join belongs. */
export function pauseBefore(words: Word[], i: number, fps = 30): number {
  if (i <= 0 || i >= words.length) throw new Error(`pauseBefore: word ${i} has no word before it`);
  const gapStart = fr(words[i - 1].endMs, fps), gapEnd = fr(words[i].startMs, fps);
  return Math.round((gapStart + Math.max(gapStart, gapEnd)) / 2);
}

/** Joins at given take frames with one style, e.g. every assembled clip boundary:
 *  joinsAt(cuts.detail.filter((d) => d.kind === "clip").map((d) => d.frame), { type: "slide" }) */
export const joinsAt = (frames: number[], style: Omit<Join, "at"> = {}): Join[] => frames.map((at) => ({ ...style, at }));

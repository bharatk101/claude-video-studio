// Known answers for components/transition-plan.ts. Run by tests/run_tests.py:
//   node --experimental-strip-types tests/transition_plan_check.ts
import assert from "node:assert/strict";
import { joinsAt, pauseBefore, planTransitions, retimeFrame, retimeWords } from "../skills/reel-edit/components/transition-plan.ts";

const words = [
  { text: "one", startMs: 0, endMs: 900 }, //        f0-f27
  { text: "two", startMs: 1300, endMs: 1900 }, //    f39-f57, then a pause to f69
  { text: "three", startMs: 2300, endMs: 3000 }, //  f69-f90
  { text: "four", startMs: 3100, endMs: 3900 }, //   f93-f117
];

// hold (default): same length as the take, nothing re-timed, the next clip starts at the join
const hold = planTransitions([{ at: 63 }], 120, { words });
assert.deepEqual(hold.problems, []);
assert.deepEqual(hold.warnings, []);
assert.equal(hold.outFrames, 120);
assert.deepEqual(hold.clips.map((c) => [c.from, c.to, c.outFrom, c.hold]), [[0, 63, 0, 9], [63, 120, 63, 0]]);
assert.equal(hold.joins[0].outAt, 63);
assert.deepEqual(retimeWords(words, hold), words);

// overlap: shorter by each transition, later words and frames shift earlier, speech under an overlap is flagged
const ov = planTransitions([{ at: 63, mode: "overlap", frames: 10 }, { at: 92, mode: "overlap", frames: 6, type: "slide" }], 120, { words });
assert.deepEqual(ov.problems, []);
assert.equal(ov.outFrames, 120 - 16);
assert.deepEqual(ov.clips.map((c) => c.outFrom), [0, 53, 76]);
assert.deepEqual(ov.clips.map((c) => [c.fadeIn, c.fadeOut]), [[0, 10], [10, 6], [6, 0]]);
assert.deepEqual(retimeWords(words, ov).map((w) => w.startMs), [0, 1300, 2300 - 333, 3100 - 533]);
assert.equal(retimeFrame(100, ov), 100 - 16);
assert.ok(ov.warnings.some((w) => w.includes('"two"')), ov.warnings.join("\n")); //   f57 > 63-10
assert.ok(ov.warnings.some((w) => w.includes('"three"')), ov.warnings.join("\n")); // f69 < 63+10
assert.ok(ov.warnings.some((w) => w.includes('"four"') && w.includes("inside word")) === false);

// a join inside a word is flagged; pauseBefore puts it in the gap instead
const inside = planTransitions([{ at: 80 }], 120, { words });
assert.ok(inside.warnings[0].includes('inside word #2 "three"'), inside.warnings.join("\n"));
assert.equal(pauseBefore(words, 2), 63); // middle of f57..f69
assert.deepEqual(planTransitions(joinsAt([pauseBefore(words, 2)], { type: "wipe" }), 120, { words }).warnings, []);

// problems: outside the take, and a clip too short for its transitions
assert.ok(planTransitions([{ at: 0 }, { at: 130 }], 120).problems.length === 2);
const short = planTransitions([{ at: 60 }, { at: 64 }], 120);
assert.ok(short.problems.some((p) => p.startsWith("clip 2")), short.problems.join("\n"));

// "none" is a plain cut: zero frames, no hold
const cut = planTransitions([{ at: 60, type: "none" }], 120);
assert.equal(cut.outFrames, 120);
assert.equal(cut.clips[0].hold, 0);

console.log("transition plan ok");

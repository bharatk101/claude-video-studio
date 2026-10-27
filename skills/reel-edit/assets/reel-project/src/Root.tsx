import React from "react";
import { Composition } from "remotion";
import { Reel, calculateReelMetadata, type ReelProps } from "./Example/Reel";
import sample from "./Example/sample.words.json";
import type { Word } from "./shared/captions";
import { TextHook } from "./shared/TextHook";

// One composition per video: copy src/Example to src/<Video>/ and add a <Composition> here.
// Never edit a composition that's already approved to serve a new video; copy it or parameterise it.
const FPS = 30;
const words = sample as Word[];

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="Example"
      component={Reel}
      width={1080}
      height={1920}
      fps={FPS}
      durationInFrames={1} // placeholder: calculateReelMetadata sets the real length from the footage
      calculateMetadata={calculateReelMetadata}
      defaultProps={{
        words,
        captionY: 1380,
        hook: { lines: ["Edited in code,", "not in an editor"], widths: [586, 590], top: 300, until: 120 },
      } satisfies ReelProps}
    />
    {/* Tooling: draws each hook line as a white box so scripts/measure-hook.py can read its width.
        npx remotion still src/index.ts HookMeasure out/m.png --props='{"lines":["line one","line two"]}' */}
    <Composition
      id="HookMeasure"
      component={HookMeasure}
      width={1080}
      height={1920}
      fps={FPS}
      durationInFrames={1}
      defaultProps={{ lines: ["Edited in code,", "not in an editor"], top: 300 }}
    />
  </>
);

const HookMeasure: React.FC<{ lines: string[]; top: number }> = ({ lines, top }) => (
  <TextHook lines={lines} widths={lines.map(() => 0)} top={top} variant="measure" />
);

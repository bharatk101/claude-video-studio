import { continueRender, delayRender } from "remotion";
import { loadFont } from "@remotion/fonts";
import inter600 from "@fontsource/inter/files/inter-latin-600-normal.woff2";
import inter800 from "@fontsource/inter/files/inter-latin-800-normal.woff2";

// Inter, bundled from npm (@fontsource/inter) instead of fetched from Google Fonts at render time: renders work
// offline, never time out on font downloads, and look identical on every machine. Latin only; add other subsets'
// files here if your captions need them. Needs: npm i @remotion/fonts @fontsource/inter
export const INTER = "Inter";

const handle = delayRender("Loading Inter");
Promise.all([
  loadFont({ family: INTER, url: inter600, weight: "600" }),
  loadFont({ family: INTER, url: inter800, weight: "800" }),
])
  .then(() => continueRender(handle))
  .catch((e) => {
    console.error("Inter failed to load", e);
    continueRender(handle);
  });

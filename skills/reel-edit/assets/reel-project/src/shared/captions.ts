// Caption chunking and timing, as specified in the reel-edit skill (references/captions.md).
//
//   const chunks = buildChunks(words, { cuts: CUTS });
//   const cur = chunkAt(chunks, frame, HARD_CUTS);
//
// Words come from scripts/transcribe.mjs: [{ text, startMs, endMs }]. Any word fixes you apply must be keyed BY
// INDEX (fixWords), never by startMs: a fix keyed on a timestamp silently stops firing after a re-time.

export type Word = { text: string; startMs: number; endMs: number };
export type Chunk = { from: number; to: number; text: string; first: number; last: number };

export const FPS = 30;
export const toFrames = (ms: number, fps = FPS) => Math.round((ms / 1000) * fps);

/** Proper nouns and the pronoun I keep their case; everything else is casual lowercase. Extend per project. */
export const KEEP: Record<string, string> = { i: "I", "i'll": "I'll", "i'm": "I'm", "i've": "I've", "i'd": "I'd", ai: "AI", claude: "Claude", remotion: "Remotion", instagram: "Instagram", tiktok: "TikTok", youtube: "YouTube" };

export const casualCase = (w: Word, keep: Record<string, string> = KEEP): Word => {
  const core = w.text.replace(/[,.?!]+$/, "");
  const tail = w.text.slice(core.length);
  return { ...w, text: (keep[core.toLowerCase()] ?? core.toLowerCase()) + tail };
};

/** Whisper emits standalone punctuation as words: drop anything without a letter or digit. */
export const cleanWords = (words: Word[]) =>
  words.map((w) => ({ ...w, text: w.text.trim() })).filter((w) => /[\p{L}\p{N}]/u.test(w.text));

/** Replace words by index: { 12: "Claude", 40: "Remotion" }. */
export const fixWords = (words: Word[], fixes: Record<number, string>) =>
  words.map((w, i) => (fixes[i] != null ? { ...w, text: fixes[i] } : w));

/**
 * 1-3 words, at most ~17 characters, broken at sentence ends and never across a cut that starts new speech.
 * A chunk runs from its first word's start to its last word's end (capped at start + 550 ms) plus 3 frames:
 * never held until the next chunk starts.
 */
export function buildChunks(
  words: Word[],
  { cuts = [] as number[], maxWords = 3, maxChars = 17, fps = FPS, tailFrames = 3, capMs = 550 } = {},
): Chunk[] {
  const chunks: Chunk[] = [];
  let cur: { w: Word; i: number }[] = [];
  const flush = () => {
    if (!cur.length) return;
    const first = cur[0], last = cur[cur.length - 1];
    let to = toFrames(Math.min(last.w.endMs, last.w.startMs + capMs), fps) + tailFrames;
    const from = toFrames(first.w.startMs, fps);
    // never let a line run across a cut
    const cut = cuts.find((c) => c > from && c < to);
    if (cut != null) to = cut;
    chunks.push({ from, to, text: cur.map((x) => x.w.text).join(" ").replace(/\.+$/, ""), first: first.i, last: last.i });
    cur = [];
  };
  words.forEach((w, i) => {
    const f = toFrames(w.startMs, fps);
    const crossesCut = cur.length > 0 && cuts.some((c) => c > toFrames(cur[0].w.startMs, fps) && c <= f + 2);
    const candidate = [...cur.map((x) => x.w.text), w.text].join(" ");
    if (crossesCut || cur.length >= maxWords || (cur.length > 0 && candidate.length > maxChars)) flush();
    cur.push({ w, i });
    if (/[.?!]$/.test(w.text)) flush();
  });
  flush();
  return chunks;
}

/** Cuts that actually start a new line (a mid-sentence cut into b-roll lets the line run through). */
export const hardCuts = (cuts: number[], chunks: Chunk[]) =>
  cuts.filter((c) => chunks.some((ch) => ch.from >= c - 1 && ch.from <= c + 3));

/** The chunk on screen at `frame`: the last match wins, so overlapping lines resolve to the newest. */
export function chunkAt(chunks: Chunk[], frame: number, hard: number[] = []): Chunk | null {
  let cur: Chunk | null = null;
  for (const c of chunks) if (frame >= c.from && frame < c.to) cur = c;
  if (cur) for (const b of hard) if (cur.from < b && frame >= b) return null;
  return cur;
}

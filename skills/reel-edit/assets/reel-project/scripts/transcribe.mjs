#!/usr/bin/env node
// node scripts/transcribe.mjs <media> <out.words.json> [--model small] [--force]
// Thin wrapper so `npm run transcribe -- <media> <out>` works; the work is in transcribe.py.
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const py = process.env.PYTHON || (process.platform === "win32" ? "python" : "python3");
const r = spawnSync(py, [path.join(here, "transcribe.py"), ...process.argv.slice(2)], { stdio: "inherit" });
process.exit(r.status ?? 1);

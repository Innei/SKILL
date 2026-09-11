#!/usr/bin/env node
// Usage: instrument-entry.mjs <packaged entry.js> [--restore]
//   Prepends [boot] probes (uptime at entry / after the first chunk require /
//   app ready / browser-window-created) to a packaged main entry. Keeps
//   <entry>.bak; --restore puts it back. Requires an unpacked app (asar: false
//   or `npx @electron/asar extract`).
// Env at runtime:
//   LOBE_PROF=<file>   write an inspector CPU profile from entry to window creation
//   LOBE_CC=1          enable module.enableCompileCache() before anything loads
import { copyFileSync, existsSync, readFileSync, renameSync, writeFileSync } from 'node:fs';

const [entry, flag] = process.argv.slice(2);
if (!entry) {
  console.error('usage: instrument-entry.mjs <entry.js> [--restore]');
  process.exit(1);
}
const backup = `${entry}.bak`;

if (flag === '--restore') {
  if (existsSync(backup)) renameSync(backup, entry);
  process.exit(0);
}
if (!existsSync(backup)) copyFileSync(entry, backup);

const source = readFileSync(backup, 'utf8');
const firstRequire = source.match(/require\("\.\/[^"]+"\)/);
if (!firstRequire) {
  console.error('no chunk require found in entry; nothing to split');
  process.exit(1);
}

const probes = `
const __u = () => Math.round(process.uptime() * 1000);
console.error("[boot] entry", __u(), "wall", Date.now());
if (process.env.LOBE_CC) console.error("[boot] compileCache", JSON.stringify(require("node:module").enableCompileCache?.()));
let __sess;
if (process.env.LOBE_PROF) {
  const ins = require("node:inspector");
  __sess = new ins.Session(); __sess.connect();
  __sess.post("Profiler.enable"); __sess.post("Profiler.setSamplingInterval", { interval: 100 }); __sess.post("Profiler.start");
}
{
  const { app } = require("electron");
  app.once("ready", () => console.error("[boot] ready", __u()));
  app.once("browser-window-created", () => {
    console.error("[boot] window-created", __u());
    __sess?.post("Profiler.stop", (_e, { profile }) => {
      require("node:fs").writeFileSync(process.env.LOBE_PROF, JSON.stringify(profile));
      console.error("[boot] profile written", process.env.LOBE_PROF);
    });
  });
}
const __t0 = performance.now();
`;
const afterFirst = `;console.error("[boot] first-chunk loaded", __u(), "took", (performance.now() - __t0).toFixed(1));`;

const idx = source.indexOf(firstRequire[0]) + firstRequire[0].length;
// Split `const a=require(..),b=require(..)` so the probe lands right after the first chunk.
let head = source.slice(0, idx);
let tail = source.slice(idx);
if (tail.startsWith(',')) tail = `;const ${tail.slice(1)}`;
writeFileSync(entry, `${probes}${head}${afterFirst}${tail}`);
console.log(`instrumented ${entry} (backup: ${backup})`);

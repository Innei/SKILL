#!/usr/bin/env node
// Usage: scripts-summary.mjs <scripts.json> [topN=30]
// Sizes the scripts V8 parsed before the page started loading (from LOBE_SCRIPTS).
import { readFileSync, statSync } from 'node:fs';

const [file, topArg] = process.argv.slice(2);
const rows = JSON.parse(readFileSync(file, 'utf8')).map(([at, url]) => {
  const path = decodeURIComponent(url.replace('file://', ''));
  let size = 0;
  try {
    size = statSync(path).size;
  } catch {}
  return { at, path, size };
});
const total = rows.reduce((sum, r) => sum + r.size, 0);
console.log(`scripts ${rows.length}, total ${(total / 1e6).toFixed(1)}MB`);
rows
  .sort((a, b) => b.size - a.size)
  .slice(0, Number(topArg) || 30)
  .forEach((r) => console.log(`${(r.size / 1e3).toFixed(0).padStart(6)}KB ${String(r.at).padStart(5)}ms ${r.path.split('/').slice(-2).join('/')}`));

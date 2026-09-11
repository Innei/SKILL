#!/usr/bin/env node
// Usage: cpuprofile-summary.mjs <main.cpuprofile> [topN=25]
// Prints top self-time and top total-time frames, then the callees of the
// largest top-level module evaluation (what your bundle spends at load).
// Landmarks: wrapSafe = compile, dlopen = native addon, View = new BrowserWindow (native).
import { readFileSync } from 'node:fs';

const [file, topArg] = process.argv.slice(2);
const top = Number(topArg) || 25;
const p = JSON.parse(readFileSync(file, 'utf8'));
const byId = new Map(p.nodes.map((n) => [n.id, n]));
const parent = new Map();
for (const n of p.nodes) for (const c of n.children ?? []) parent.set(c, n.id);
const selfUs = new Map();
for (let i = 0; i < p.samples.length; i++) {
  selfUs.set(p.samples[i], (selfUs.get(p.samples[i]) ?? 0) + (p.timeDeltas[i] ?? 0));
}
const key = (n) => {
  const cf = n.callFrame;
  return `${cf.functionName || '(anon)'} @ ${cf.url.split('/').pop()}:${cf.lineNumber}`;
};
const totalUs = (id) => (selfUs.get(id) ?? 0) + (byId.get(id).children ?? []).reduce((s, c) => s + totalUs(c), 0);

const self = new Map();
const total = new Map();
for (const [id, us] of selfUs) {
  self.set(key(byId.get(id)), (self.get(key(byId.get(id))) ?? 0) + us);
  const seen = new Set();
  for (let cur = id; cur !== undefined && !seen.has(cur); cur = parent.get(cur)) {
    seen.add(cur);
    const k = key(byId.get(cur));
    total.set(k, (total.get(k) ?? 0) + us);
  }
}
const print = (title, map) => {
  console.log(`\n== ${title}`);
  [...map].sort((a, b) => b[1] - a[1]).slice(0, top).forEach(([k, v]) => console.log((v / 1000).toFixed(1).padStart(7), k));
};
console.log('profile ms:', (p.timeDeltas.reduce((a, b) => a + b, 0) / 1000).toFixed(1));
print('top self', self);
print('top total', total);

const moduleTops = p.nodes
  .filter((n) => n.callFrame.functionName === '' && n.callFrame.lineNumber === 0 && !n.callFrame.url.startsWith('node:'))
  .map((n) => [totalUs(n.id), n])
  .sort((a, b) => b[0] - a[0]);
for (const [us, node] of moduleTops.slice(0, 2)) {
  console.log(`\n== callees of module top-level ${node.callFrame.url.split('/').pop()} (${(us / 1000).toFixed(1)}ms)`);
  (node.children ?? [])
    .map((c) => [totalUs(c), byId.get(c)])
    .sort((a, b) => b[0] - a[0])
    .slice(0, top)
    .forEach(([t, n]) => console.log((t / 1000).toFixed(1).padStart(7), key(n)));
}

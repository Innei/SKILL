#!/usr/bin/env node
// Usage: trace-summary.mjs <startup-trace.json> [urlPrefix=app://]
// Capture with:
//   <app-binary> --trace-startup="blink,loading,devtools.timeline,v8,disabled-by-default-devtools.timeline,toplevel" \
//     --trace-startup-format=json --trace-startup-file=/tmp/startup-trace.json --trace-startup-duration=4
// Prints, for the renderer that painted first: commit → firstPaint / DOMContentLoaded / load,
// the first resource requests, and main-thread tasks > 3ms.
import { readFileSync } from 'node:fs';

const [file, urlPrefix = 'app://'] = process.argv.slice(2);
const ev = JSON.parse(readFileSync(file, 'utf8')).traceEvents;
const fp = ev.find((e) => e.name === 'firstPaint');
if (!fp) {
  console.log('no firstPaint event; categories present:', [...new Set(ev.map((e) => e.cat))].slice(0, 20).join(', '));
  process.exit(1);
}
const { pid, tid } = fp;
const commits = ev.filter((e) => e.name === 'DocumentLoader::CommitNavigation' && e.pid === pid).map((e) => e.ts).sort();
const t0 = commits.filter((c) => c < fp.ts).pop();
const ms = (ts) => ((ts - t0) / 1000).toFixed(1);
console.log(`renderer pid ${pid}; ${commits.length} commits; anchoring at the last commit before firstPaint`);
for (const n of ['firstPaint', 'firstContentfulPaint', 'MarkDOMContent', 'MarkLoad', 'firstMeaningfulPaint']) {
  const e = ev.find((x) => x.name === n && x.pid === pid && x.ts >= t0);
  if (e) console.log(n.padEnd(24), ms(e.ts).padStart(8), 'ms');
}

const byReq = {};
for (const e of ev.filter((x) => x.pid === pid && /^Resource(SendRequest|ReceiveResponse|Finish)$/.test(x.name))) {
  const d = e.args.data;
  const r = (byReq[d.requestId] ??= {});
  if (e.name === 'ResourceSendRequest') Object.assign(r, { url: d.url, s: e.ts });
  if (e.name === 'ResourceReceiveResponse') r.r = e.ts;
  if (e.name === 'ResourceFinish') r.f = e.ts;
}
const rows = Object.values(byReq).filter((r) => r.s && (r.url ?? '').startsWith(urlPrefix)).sort((a, b) => a.s - b.s);
console.log(`\n== resources (${rows.length}); first 12`);
rows.slice(0, 12).forEach((r) =>
  console.log(ms(r.s).padStart(8), '→resp', r.r ? ms(r.r) : '?', '→fin', r.f ? ms(r.f) : '?', (r.url ?? '').split('/').pop().slice(0, 60)),
);
if (rows.length) console.log('last finish', ms(Math.max(...rows.map((r) => r.f ?? 0))));

console.log('\n== main-thread slices > 3ms (outermost only)');
const slices = ev
  .filter((e) => e.pid === pid && e.tid === tid && e.ph === 'X' && e.ts >= t0 && e.dur > 3000 && !/RunTask|Receive mojo|BlinkScheduler/.test(e.name))
  .sort((a, b) => a.ts - b.ts);
let end = -1;
for (const e of slices) {
  if (e.ts < end) continue;
  end = e.ts + e.dur;
  const d = e.args?.data ?? e.args ?? {};
  console.log(ms(e.ts).padStart(8), (e.dur / 1000).toFixed(1).padStart(6), e.name, String(d.url ?? d.functionName ?? d.fileName ?? '').split('/').pop().slice(0, 60));
}

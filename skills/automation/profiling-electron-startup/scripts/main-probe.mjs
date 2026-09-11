// ESM entry wrapper. Copy next to the packaged entry, then set package.json
// "main" to this file. Env: LOBE_PROF=<file> (CPU profile entry→window),
// LOBE_SCRIPTS=<file> (scripts parsed before the page starts loading),
// LOBE_CC=1 (enableCompileCache before anything else loads).
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const uptime = () => Math.round(process.uptime() * 1000);
console.error('[boot] entry', uptime(), 'wall', Date.now());
if (process.env.LOBE_CC) console.error('[boot] compileCache', JSON.stringify(require('node:module').enableCompileCache?.()));

const { app } = require('electron');
let session;
const scripts = [];
if (process.env.LOBE_PROF || process.env.LOBE_SCRIPTS) {
  const inspector = require('node:inspector');
  session = new inspector.Session();
  session.connect();
  if (process.env.LOBE_SCRIPTS) {
    session.on('Debugger.scriptParsed', ({ params }) => {
      if (params.url.startsWith('file://')) scripts.push([uptime(), params.url]);
    });
    session.post('Debugger.enable');
  }
  if (process.env.LOBE_PROF) {
    session.post('Profiler.enable');
    session.post('Profiler.setSamplingInterval', { interval: 100 });
    session.post('Profiler.start');
  }
}

app.once('ready', () => console.error('[boot] ready', uptime()));
app.once('browser-window-created', (_event, win) => {
  console.error('[boot] window-created', uptime());
  win.webContents.once('did-start-loading', () => {
    console.error('[boot] load-start', uptime());
    if (process.env.LOBE_SCRIPTS) require('node:fs').writeFileSync(process.env.LOBE_SCRIPTS, JSON.stringify(scripts));
  });
  win.once('ready-to-show', () => console.error('[boot] ready-to-show', uptime()));
  win.webContents.once('did-finish-load', () => console.error('[boot] did-finish-load', uptime()));
  if (process.env.LOBE_PROF) {
    session.post('Profiler.stop', (_error, { profile }) => {
      require('node:fs').writeFileSync(process.env.LOBE_PROF, JSON.stringify(profile));
      console.error('[boot] profile written');
    });
  }
});

const started = performance.now();
await import('./main.mjs');
console.error('[boot] main loaded', uptime(), 'took', (performance.now() - started).toFixed(1));

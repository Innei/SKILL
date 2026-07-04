const ESCAPE_MAP = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ESCAPE_MAP[c]);

const KEY_RE = /^(\d{4})-(\d{2})-w(\d+)(-\d+)?\.html$/;

function parseKey(key) {
  const m = KEY_RE.exec(key);
  if (!m) return null;
  return {
    year: Number(m[1]),
    month: Number(m[2]),
    week: Number(m[3]),
    suffix: m[4] ? Number(m[4].slice(1)) : 0,
  };
}

function fmtSize(bytes) {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}K`;
  return `${(bytes / 1024 / 1024).toFixed(1)}M`;
}

const FAVICON_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="6" fill="#1a1a1a"/><text x="16" y="22" font-family="ui-monospace,monospace" font-size="18" font-weight="700" fill="#fafafa" text-anchor="middle">w</text></svg>`;

function renderIndex(objects) {
  const known = [];
  const misc = [];
  for (const o of objects) {
    const meta = parseKey(o.key);
    if (meta) known.push({ ...o, ...meta });
    else misc.push(o);
  }
  known.sort(
    (a, b) =>
      b.year - a.year ||
      b.week - a.week ||
      b.suffix - a.suffix ||
      a.key.localeCompare(b.key),
  );
  const row = (o) =>
    `<li><a href="/${esc(o.key)}">${esc(o.key)}</a><span class="size">${fmtSize(o.size)}</span><span class="ts">${(o.uploaded?.toISOString?.() ?? '').slice(0, 10)}</span></li>`;
  const knownRows = known.map(row).join('');
  const miscBlock = misc.length
    ? `<h2>misc</h2><ul class="reports">${misc.map(row).join('')}</ul>`
    : '';
  return `<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<title>Innei · weekly reports</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="icon" href="/favicon.svg">
<style>
:root { color-scheme: light dark; }
body { font: 14px/1.6 ui-monospace, SFMono-Regular, Menlo, monospace; max-width: 720px; margin: 4rem auto; padding: 0 1.5rem; }
h1 { font-size: 1rem; font-weight: 600; margin: 0 0 .25rem; }
.sub { color: color-mix(in srgb, currentColor 55%, transparent); margin: 0 0 2rem; }
ul.reports { list-style: none; padding: 0; margin: 0; }
ul.reports li { display: grid; grid-template-columns: 1fr auto auto; gap: 1rem; padding: .35rem 0; border-bottom: 1px solid color-mix(in srgb, currentColor 10%, transparent); }
ul.reports a { color: inherit; text-decoration: none; }
ul.reports a:hover { text-decoration: underline; }
.size, .ts { color: color-mix(in srgb, currentColor 55%, transparent); font-variant-numeric: tabular-nums; }
h2 { font-size: .8rem; text-transform: uppercase; color: color-mix(in srgb, currentColor 55%, transparent); margin: 2rem 0 .5rem; letter-spacing: .05em; }
</style>
</head><body>
<h1>Innei · weekly reports</h1>
<p class="sub">${known.length + misc.length} reports · latest first</p>
<ul class="reports">${knownRows}</ul>
${miscBlock}
</body></html>`;
}

export default {
  async fetch(req, env) {
    if (req.method !== 'GET' && req.method !== 'HEAD') {
      return new Response('method not allowed', { status: 405 });
    }
    const url = new URL(req.url);

    if (url.pathname === '/') {
      const list = await env.BUCKET.list({ limit: 1000 });
      return new Response(renderIndex(list.objects), {
        headers: {
          'content-type': 'text/html; charset=utf-8',
          'cache-control': 'no-store',
        },
      });
    }

    if (url.pathname === '/favicon.ico' || url.pathname === '/favicon.svg') {
      return new Response(FAVICON_SVG, {
        headers: {
          'content-type': 'image/svg+xml',
          'cache-control': 'public, max-age=86400',
        },
      });
    }

    const key = decodeURIComponent(url.pathname.slice(1));
    if (!key.endsWith('.html') || key.includes('/')) {
      return new Response('not found', { status: 404 });
    }
    const obj = await env.BUCKET.get(key);
    if (!obj) return new Response('not found', { status: 404 });
    return new Response(obj.body, {
      headers: {
        'content-type': 'text/html; charset=utf-8',
        'cache-control': 'public, max-age=300',
        etag: obj.httpEtag,
      },
    });
  },
};

import { readdir } from 'node:fs/promises';
import { join } from 'node:path';

// Executed with bun (see package.json); repo tsconfig has no bun types.
declare const Bun: any;

// STATIC_CDN_URL is the master switch: unset means assets stay same-origin
// (vite base / next assetPrefix key off it too), so there is nothing to
// upload. Set with credentials missing is a broken half-state — the HTML
// would reference a CDN nobody populated — so fail the build instead.
if (!process.env.STATIC_CDN_URL) {
  console.log('[upload-static] skipped: STATIC_CDN_URL unset');
  process.exit(0);
}

const REQUIRED = [
  'STATIC_S3_ACCESS_KEY_ID',
  'STATIC_S3_SECRET_ACCESS_KEY',
  'STATIC_S3_ENDPOINT',
  'STATIC_S3_BUCKET',
] as const;

const missing = REQUIRED.filter((name) => !process.env[name]);
if (missing.length > 0) {
  console.error(`[upload-static] STATIC_CDN_URL is set but ${missing.join(', ')} unset`);
  process.exit(1);
}

const [srcDir, destSubdir] = process.argv.slice(2);
if (!srcDir || !destSubdir) {
  console.error('usage: bun scripts/uploadStaticAssets.ts <srcDir> <destSubdir>');
  process.exit(1);
}

const withScheme = (value: string) => (/^https?:\/\//.test(value) ? value : `https://${value}`);

const prefix = new URL(withScheme(process.env.STATIC_CDN_URL!)).pathname.replaceAll(
  /^\/+|\/+$/g,
  '',
);

const client = new Bun.S3Client({
  accessKeyId: process.env.STATIC_S3_ACCESS_KEY_ID!,
  bucket: process.env.STATIC_S3_BUCKET!,
  endpoint: withScheme(process.env.STATIC_S3_ENDPOINT!),
  secretAccessKey: process.env.STATIC_S3_SECRET_ACCESS_KEY!,
});

// Bun.file() leaves some types empty or generic; ES modules and fonts break
// cross-origin unless the stored Content-Type is right.
const MIME_OVERRIDES: Record<string, string> = {
  '.avif': 'image/avif',
  '.css': 'text/css',
  '.js': 'text/javascript',
  '.map': 'application/json',
  '.mjs': 'text/javascript',
  '.svg': 'image/svg+xml',
  '.wasm': 'application/wasm',
  '.webp': 'image/webp',
  '.woff2': 'font/woff2',
};

const contentType = (path: string) => {
  const ext = path.slice(path.lastIndexOf('.')).toLowerCase();
  return MIME_OVERRIDES[ext] ?? Bun.file(path).type ?? 'application/octet-stream';
};

const entries = await readdir(srcDir, { recursive: true, withFileTypes: true });
const files = entries
  .filter((entry) => entry.isFile())
  .map((entry) => join(entry.parentPath, entry.name));

const CONCURRENCY = 16;
const started = Date.now();
let uploadedBytes = 0;
let cursor = 0;

const worker = async () => {
  while (cursor < files.length) {
    const path = files[cursor++]!;
    const rel = path.slice(srcDir.length).replaceAll(/^\/+/g, '');
    const key = [prefix, destSubdir, rel].filter(Boolean).join('/');
    const file = Bun.file(path);
    await client.write(key, file, { type: contentType(path) });
    uploadedBytes += file.size;
  }
};

await Promise.all(Array.from({ length: CONCURRENCY }, worker));

console.log(
  `[upload-static] uploaded ${files.length} files (${(uploadedBytes / 1024 / 1024).toFixed(1)} MiB) ` +
    `to ${process.env.STATIC_S3_BUCKET}/${[prefix, destSubdir].filter(Boolean).join('/')} ` +
    `in ${((Date.now() - started) / 1000).toFixed(1)}s`,
);

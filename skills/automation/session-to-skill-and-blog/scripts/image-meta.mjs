#!/usr/bin/env node
// Compute the width/height/thumbhash that a LiteXML <img> node must carry.
//
// The mx-core server only enriches NON-lexical posts (post.service.ts guards
// image-dimension extraction behind `!isLexical(doc)`). Blog posts authored as
// LiteXML are stored as Lexical, so the server never backfills dimensions or a
// thumbhash — the reader gets no aspect-ratio box (CLS) and no blur placeholder
// unless the <img> node already carries them. This script produces the values
// to inline, byte-compatible with the editor's own computeImageMeta and the
// server's ImageService (resize longest side to 100, RGBA, thumbhash → base64).
//
// Usage:
//   node image-meta.mjs <path-or-url> [<path-or-url> ...]
//   node image-meta.mjs --xml <path-or-url>   # emit a ready <img .../> tag
//
// Requires `sharp` and `thumbhash` on the module resolution path (run it from a
// project that has them, e.g. mx-core, or `pnpm add sharp thumbhash` first).

import { readFile } from 'node:fs/promises'
import { createRequire } from 'node:module'
import { pathToFileURL } from 'node:url'

const MAX_DIM = 100

// Resolve deps from the current working directory's node_modules (this script
// lives in the SKILL repo, which has none — run it from mx-core or any project
// that already depends on sharp + thumbhash).
const requireFromCwd = createRequire(pathToFileURL(`${process.cwd()}/`))
let sharp
let rgbaToThumbHash
try {
  sharp = (await import(pathToFileURL(requireFromCwd.resolve('sharp')).href))
    .default
  ;({ rgbaToThumbHash } = await import(
    pathToFileURL(requireFromCwd.resolve('thumbhash')).href
  ))
} catch {
  console.error(
    'image-meta: missing deps. Run from a project whose node_modules has `sharp` + `thumbhash` (e.g. mx-core), or `pnpm add sharp thumbhash`.',
  )
  process.exit(3)
}

async function loadBytes(src) {
  if (/^https?:\/\//.test(src)) {
    const res = await fetch(src)
    if (!res.ok) throw new Error(`fetch ${src} → ${res.status}`)
    return Buffer.from(await res.arrayBuffer())
  }
  return readFile(src)
}

async function computeMeta(src) {
  const input = sharp(await loadBytes(src))
  const { width, height } = await input.metadata()
  const scale = Math.min(MAX_DIM / width, MAX_DIM / height, 1)
  const sw = Math.max(1, Math.round(width * scale))
  const sh = Math.max(1, Math.round(height * scale))
  const { data, info } = await input
    .clone()
    .resize(sw, sh, { fit: 'fill' })
    .ensureAlpha()
    .raw()
    .toBuffer({ resolveWithObject: true })
  const thumbhash = Buffer.from(
    rgbaToThumbHash(info.width, info.height, data),
  ).toString('base64')
  return { src, width, height, thumbhash }
}

const args = process.argv.slice(2)
const asXml = args[0] === '--xml'
const targets = asXml ? args.slice(1) : args

if (targets.length === 0) {
  console.error('usage: image-meta.mjs [--xml] <path-or-url> ...')
  process.exit(2)
}

for (const src of targets) {
  const meta = await computeMeta(src)
  if (asXml) {
    console.log(
      `<img src="${meta.src}" width="${meta.width}" height="${meta.height}" thumbhash="${meta.thumbhash}" />`,
    )
  } else {
    console.log(JSON.stringify(meta))
  }
}

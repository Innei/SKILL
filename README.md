# Personal Skills Repository

This repository stores personal Codex / Claude Code skills in a scalable directory layout.

## Layout

```text
SKILL/
├── README.md
├── skills/
│   ├── automation/
│   ├── content/
│   ├── infrastructure/
│   ├── research/
│   └── writing/
│       └── <skill-name>/
│           ├── SKILL.md
│           ├── references/   (optional)
│           ├── scripts/      (optional)
│           └── assets/       (optional)
└── templates/
    ├── SKILL.template.md
    └── SKILL.with-references.template.md
```

## Conventions

- Place real skills only under `skills/`.
- Group skills by a stable domain: `automation`, `content`, `infrastructure`, `research`, or `writing`.
- Each skill lives in its own directory with a required `SKILL.md` plus optional `agents/`, `references/`, `scripts/`, or `assets/`.
- Keep `templates/` for reusable skeletons only — they are not active skills.
- Avoid credentials, tokens, or machine-specific secrets in skill files.
- One skill per directory, even when the first version is only a single `SKILL.md`.
- Domain folders are stable classification buckets; do not encode transient project names at the domain level.

## Skills

### Automation

> Repeated shell workflows, CLI procedures, scripting playbooks.

| Skill | Purpose |
| ----- | ------- |
| [`session-handoff`](skills/automation/session-handoff/SKILL.md) | Produce a self-contained handoff prompt for another agent when delegating continued work |
| [`session-to-skill-and-blog`](skills/automation/session-to-skill-and-blog/SKILL.md) | Classify a completed engineering session into a narrative blog, zero or more reusable skills, and project-local documentation |
| [`working-summary`](skills/automation/working-summary/SKILL.md) | Work summary / 周报 from GitHub PRs/commits and optional Linear trackers; markdown for notes (e.g. Obsidian) |

### Content

> Media generation, character assets, site SEO imagery.

| Skill | Purpose |
| ----- | ------- |
| [`acg-character-settei`](skills/content/acg-character-settei/SKILL.md) | Generate ACG character settei sheet (multi-view + expression + callouts) from a reference image via Gemini |
| [`app-store-listing`](skills/content/app-store-listing/SKILL.md) | One-shot App Store listing: copy, official-bezel screenshots, and Connect questionnaires |
| [`chibi-sticker-sheet`](skills/content/chibi-sticker-sheet/SKILL.md) | Generate a 4×8 chibi sticker sheet from a character reference via Gemini, with alpha keying and 1:1 cell slicing |
| [`gemini-image-generation`](skills/content/gemini-image-generation/SKILL.md) | Gemini text-to-image and image-to-image — style transfer, character consistency, watermark removal |
| [`gemini-seo-image-assets`](skills/content/gemini-seo-image-assets/SKILL.md) | Generate favicon/OG artwork via Gemini, export icon variants, and wire SEO metadata |
| [`product-visuals`](skills/content/product-visuals/SKILL.md) | Compose product marketing visuals from real macOS/iOS screenshots in official device bezels |

### Infrastructure

> Deployment, servers, databases, containers, networking, observability.

| Skill | Purpose |
| ----- | ------- |
| [`capture-output-via-sidechannel`](skills/infrastructure/capture-output-via-sidechannel/SKILL.md) | Capture stdout/stderr from runners/CI/containers when log retrieval is unavailable, by persisting output to a readable store |
| [`ci-smoke-needs-real-deps`](skills/infrastructure/ci-smoke-needs-real-deps/SKILL.md) | Fix CI release smoke tests that fail after a stack migration by aligning service containers and env vars with `ci.yml` |
| [`cloudflare-r2-upload`](skills/infrastructure/cloudflare-r2-upload/SKILL.md) | Upload files/batches to Cloudflare R2 via `wrangler`, resolve multi-account context, set MIME, and verify public URLs |
| [`dokploy-api-cli`](skills/infrastructure/dokploy-api-cli/SKILL.md) | Operate Dokploy deployments via REST API — create/update/deploy services, switch sources, script redeploys |
| [`dokploy-internal-oneshot`](skills/infrastructure/dokploy-internal-oneshot/SKILL.md) | Run ephemeral one-shot tasks inside a Dokploy project's internal network without exposing services publicly |
| [`dokploy-traefik-traffic-split`](skills/infrastructure/dokploy-traefik-traffic-split/SKILL.md) | Canary two backends on one Dokploy domain with path-aware weighted+sticky Traefik routing; covers SPA asset trap and rollback |
| [`edge-canary-split`](skills/infrastructure/edge-canary-split/SKILL.md) | Cookie-sticky canary rollout between two Vercel apps via a Cloudflare Worker, with hashed assets offloaded to R2 so they never traverse the worker |
| [`electron-native-lib-extraction`](skills/infrastructure/electron-native-lib-extraction/SKILL.md) | Extract an in-app Electron native-module integration into a standalone source-distributed npm library with its release toolchain |
| [`mx-space-remote-db-access`](skills/infrastructure/mx-space-remote-db-access/SKILL.md) | Remote `mx-space` PostgreSQL inspection and guarded updates via `ssh → docker exec → psql` |
| [`mx-space-remote-translation-audit`](skills/infrastructure/mx-space-remote-translation-audit/SKILL.md) | Remote translation auditing — coverage checks, hash freshness, and route-level verification |
| [`nextjs-rsc-to-react-router-v8-migration`](skills/infrastructure/nextjs-rsc-to-react-router-v8-migration/SKILL.md) | Migrate a Next.js App-Router / RSC site to React Router v8 for CDN-cacheable SSR under multi-locale cost pressure |
| [`vless-reality-aws-lightsail`](skills/infrastructure/vless-reality-aws-lightsail/SKILL.md) | End-to-end VLESS+Reality+Vision on AWS Lightsail, with Alpine LXC SOCKS5 bridge for LAN and Surge wiring |

### Research

> Data analysis, report generation, conversation mining.

| Skill | Purpose |
| ----- | ------- |
| [`chat-export-report`](skills/research/chat-export-report/SKILL.md) | Analyze exported chat logs (WeChat / Telegram / iMessage / QQ) into layered, drill-down reports grounded in original quotes |
| [`codebase-value-audit`](skills/research/codebase-value-audit/SKILL.md) | Audit whether a codebase's size is justified: strict LOC accounting, product-surface inventory, per-sub-product line attribution and worth verdicts |

### Writing

> Structured writing, design docs, editorial judgment.

| Skill | Purpose |
| ----- | ------- |
| [`generate-design-md`](skills/writing/generate-design-md/SKILL.md) | Produce `DESIGN.md` for a brand/site from live CSS and tokens (awesome-design-md format) |
| [`holding-analytical-judgment`](skills/writing/holding-analytical-judgment/SKILL.md) | Keep analysis grounded in evidence; do not flip conclusions for mood alone (code review, diagnosis, post-mortems) |

## Agent Integration

Skills are loaded by Copilot CLI (`.agent/`) and Claude Code (`.claude/`) via **flat symlinks** under their respective `skills/` directories. Each agent expects skills exactly one level deep: `.agent/skills/<skill-name>/SKILL.md`.

```text
.agent/skills/
└── <skill-name> -> ../../skills/<domain>/<skill-name>
.claude/skills/
└── <skill-name> -> ../../skills/<domain>/<skill-name>
```

> [!WARNING]
> Do **not** symlink the entire `skills/` directory — agents will not discover nested domain subdirectories.

## Adding a New Skill

1. Create a directory under `skills/<domain>/<skill-name>/`.
2. Copy `templates/SKILL.template.md` into that directory as `SKILL.md`.
3. Fill in the frontmatter and keep the body concise.
4. Add optional `references/`, `scripts/`, or `assets/` only when they improve reuse.
5. Add a row to the matching domain table in this README.
6. Create flat symlinks in both agent skill roots:

```bash
ln -sf ../../skills/<domain>/<skill-name> .agent/skills/<skill-name>
ln -sf ../../skills/<domain>/<skill-name> .claude/skills/<skill-name>
```

## Naming Guidance

- Directory names: lowercase kebab-case.
- Skill `name` values: stable and descriptive.
- Prefer names that state both target and action, e.g. `mx-space-remote-db-access` or `article-publish-checklist`.

## Repository Hooks

A pre-commit hook in `.githooks/pre-commit` enforces the rules above: every skill under `skills/<domain>/<name>/SKILL.md` must have a README entry and matching flat symlinks under `.agent/skills/` and `.claude/skills/`. Orphan symlinks fail the hook too.

Enable it once per clone:

```bash
git config core.hooksPath .githooks
```

If you must bypass it for a non-skill commit, use `git commit --no-verify`.

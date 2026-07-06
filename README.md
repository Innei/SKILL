# Personal Skills Repository

This repository stores personal Codex skills in a scalable directory layout.

## Layout

```text
SKILL/
├── README.md
├── skills/
│   ├── infrastructure/
│   ├── automation/
│   ├── writing/
│   ├── research/
│   └── content/
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
- Group skills by a stable domain such as `infrastructure`, `writing`, `research`, or `automation`.
- Each skill should live in its own directory and contain a single required `SKILL.md` file plus optional `agents/`, `references/`, `scripts/`, or `assets/` subdirectories.
- Keep `templates/` for reusable skeletons only. Files in this directory are not treated as active skills.
- Avoid storing credentials, tokens, or machine-specific secrets in skill files.
- Prefer one skill per directory, even when the first version is only a single `SKILL.md`.
- Use domain folders only as stable classification buckets; do not encode transient project names into the domain level.

## Skills

### Automation

> Repeated shell workflows, CLI procedures, scripting playbooks.

| Skill | Purpose |
| ----- | ------- |
| [`session-handoff`](skills/automation/session-handoff/SKILL.md) | Produce a self-contained handoff prompt for another agent when the user wants to delegate continued work |
| [`session-to-skill-and-blog`](skills/automation/session-to-skill-and-blog/SKILL.md) | Productize a completed engineering session as a paired skill (in this repo) and a published blog post that links to it |
| [`working-summary`](skills/automation/working-summary/SKILL.md) | Work summary / 周报 from GitHub PRs/commits and optional Linear trackers; markdown output for notes (e.g. Obsidian) |

### Writing

> Structured writing, publishing, editorial workflows.

| Skill | Purpose |
| ----- | ------- |
| [`generate-design-md`](skills/writing/generate-design-md/SKILL.md) | Produce `DESIGN.md` for a brand/site from live CSS and tokens (awesome-design-md format) |
| [`holding-analytical-judgment`](skills/writing/holding-analytical-judgment/SKILL.md) | Keep analysis grounded in evidence; do not flip conclusions for mood alone (code review, diagnosis, post-mortems) |

### Infrastructure

> Deployment, servers, databases, containers, observability.

| Skill | Purpose |
| ----- | ------- |

### Research

> Data analysis, report generation, conversation mining.

| Skill | Purpose |
| ----- | ------- |

### Content

> Site-specific publishing, content operations, media handling.

| Skill | Purpose |
| ----- | ------- |

## Agent Integration

Skills are loaded by Copilot CLI (`.agent/`) and Claude Code (`.claude/`) via **flat symlinks** directly under their respective `skills/` directories. Each agent expects skills at exactly one level deep: `.agent/skills/<skill-name>/SKILL.md`.

```text
.agent/skills/
└── <skill-name> -> ../../skills/<domain>/<skill-name>   ← flat symlink
.claude/skills/
└── <skill-name> -> ../../skills/<domain>/<skill-name>   ← flat symlink
```

> ⚠️ Do **not** symlink the entire `skills/` directory — agents will not discover nested subdirectories.

## Adding a New Skill

1. Create a new directory under `skills/<domain>/<skill-name>/`.
2. Copy `templates/SKILL.template.md` into that directory as `SKILL.md`.
3. Fill in the frontmatter and keep the body concise.
4. Add optional `references/`, `scripts/`, or `assets/` only when they materially improve reuse.
5. Add an entry to the corresponding domain table in this README.
6. Create flat symlinks in both `.agent/skills/` and `.claude/skills/`:
   ```bash
   ln -sf ../../skills/<domain>/<skill-name> .agent/skills/<skill-name>
   ln -sf ../../skills/<domain>/<skill-name> .claude/skills/<skill-name>
   ```

## Naming Guidance

- Directory names should use lowercase kebab-case.
- Skill `name` values should be stable and descriptive.
- Prefer names that state both target and action, such as `mx-space-remote-db-access` or `article-publish-checklist`.

## Repository Hooks

A pre-commit hook in `.githooks/pre-commit` enforces the rules above: every skill under `skills/<domain>/<name>/SKILL.md` must have a README entry and matching flat symlinks under `.agent/skills/` and `.claude/skills/`. Orphan symlinks fail the hook too.

Enable it once per clone:

```bash
git config core.hooksPath .githooks
```

If you must bypass it for a non-skill commit, use `git commit --no-verify`.
| [`acg-character-settei`](skills/content/acg-character-settei/SKILL.md) | Generate ACG character settei sheet (multi-view + expression + callouts) from a reference image via Gemini |
| [`capture-output-via-sidechannel`](skills/infrastructure/capture-output-via-sidechannel/SKILL.md) | Capture stdout/stderr from runners/CI/containers when log retrieval is unavailable, by persisting output to a readable data store |
| [`chat-export-report`](skills/research/chat-export-report/SKILL.md) | Analyze massive exported chat logs (WeChat / Telegram / iMessage / QQ) and produce layered, drill-downable reports grounded in original quotes |
| [`chibi-sticker-sheet`](skills/content/chibi-sticker-sheet/SKILL.md) | Generate a 4×8 chibi sticker sheet from a character reference via Gemini, with alpha keying and 1:1 cell slicing |
| [`ci-smoke-needs-real-deps`](skills/infrastructure/ci-smoke-needs-real-deps/SKILL.md) | Fix CI release smoke tests that fail after a stack migration by aligning service containers and env vars with ci.yml |
| [`cloudflare-r2-upload`](skills/infrastructure/cloudflare-r2-upload/SKILL.md) | Upload files/batches to Cloudflare R2 via `wrangler`, resolve multi-account context, set MIME, and verify public URLs |
| [`dokploy-api-cli`](skills/infrastructure/dokploy-api-cli/SKILL.md) | Operate Dokploy deployments via REST API — create/update/deploy services, switch sources, script redeploys |
| [`dokploy-internal-oneshot`](skills/infrastructure/dokploy-internal-oneshot/SKILL.md) | Run ephemeral one-shot tasks inside a Dokploy project's internal network without exposing services publicly |
| [`dokploy-traefik-traffic-split`](skills/infrastructure/dokploy-traefik-traffic-split/SKILL.md) | Canary two backends on one Dokploy domain with path-aware weighted+sticky Traefik routing; covers SPA asset trap, dry-run on canary host, and instant rollback |
| [`gemini-image-generation`](skills/content/gemini-image-generation/SKILL.md) | Gemini text-to-image and image-to-image generation — style transfer, character consistency, watermark removal |
| [`gemini-seo-image-assets`](skills/content/gemini-seo-image-assets/SKILL.md) | Generate favicon/OG artwork via Gemini, export icon variants, and wire SEO metadata |
| [`mx-space-remote-db-access`](skills/infrastructure/mx-space-remote-db-access/SKILL.md) | Remote `mx-space` MongoDB inspection, guarded updates, and verification through `ssh → docker exec → mongosh` |
| [`mx-space-remote-translation-audit`](skills/infrastructure/mx-space-remote-translation-audit/SKILL.md) | Remote translation auditing — coverage checks, freshness interpretation, and route-level verification |
| [`nextjs-rsc-to-react-router-v8-migration`](skills/infrastructure/nextjs-rsc-to-react-router-v8-migration/SKILL.md) | Migrate a Next.js App-Router / RSC site to React Router v8 for CDN-cacheable SSR under multi-locale cost pressure. |
| [`vless-reality-aws-lightsail`](skills/infrastructure/vless-reality-aws-lightsail/SKILL.md) | End-to-end VLESS+Reality+Vision on AWS Lightsail: Xray server with publicly-trusted SNI selection, Alpine LXC sing-box SOCKS5 bridge for LAN clients, and Surge proxy/policy-group wiring |

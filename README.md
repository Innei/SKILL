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

## Current Skills


| Domain           | Skill                                                                 | Purpose                                                                                                                                                            |
| ---------------- | --------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `automation`     | [`session-handoff`](skills/automation/session-handoff/SKILL.md)       | Produce a self-contained handoff prompt for another agent when the user wants to delegate continued work                                                          |
| `automation`     | [`working-summary`](skills/automation/working-summary/SKILL.md)       | Work summary / 周报 from GitHub PRs/commits and optional Linear (or similar) trackers; markdown output for notes (e.g. Obsidian)                                   |
| `writing`        | [`generate-design-md`](skills/writing/generate-design-md/SKILL.md)   | Produce `DESIGN.md` for a brand/site from live CSS and tokens (awesome-design-md format)                                                                           |
| `infrastructure` | [`mx-space-remote-db-access`](skills/infrastructure/mx-space-remote-db-access/SKILL.md) | Remote `mx-space` MongoDB inspection, guarded updates, and verification through `ssh -> docker exec -> mongosh`                                                    |
| `infrastructure` | [`mx-space-remote-translation-audit`](skills/infrastructure/mx-space-remote-translation-audit/SKILL.md) | Remote `translation_entries` and `ai_translations` auditing, including coverage checks, runtime freshness interpretation, and route-level translation verification |
| `infrastructure` | [`cloudflare-r2-upload`](skills/infrastructure/cloudflare-r2-upload/SKILL.md) | Upload single files or batches to a Cloudflare R2 bucket via `wrangler` (OAuth or API token), resolve the correct multi-account context, set explicit MIME, and verify public URLs through a bound custom domain |
| `content`        | [`gemini-seo-image-assets`](skills/content/gemini-seo-image-assets/SKILL.md) | Gemini or Google AI Studio generated favicon and OG base artwork, exported icon variants, and matching SEO metadata wiring                                       |
| `content`        | [`acg-character-settei`](skills/content/acg-character-settei/SKILL.md) | Generate ACG character settei sheet (multi-view + expression + callouts) from a template image plus a single character reference, via Gemini image-to-image      |
| `content`        | [`chibi-sticker-sheet`](skills/content/chibi-sticker-sheet/SKILL.md) | Generate a LINE/WeChat-style 4×8 chibi sticker sheet (32 stickers) from a character reference via Gemini, with cross-sheet consistency control, edge flood-fill alpha keying and 1:1 cell slicing |


## Suggested Domains


| Domain           | Typical Content                                                       |
| ---------------- | --------------------------------------------------------------------- |
| `infrastructure` | deployment, servers, databases, containers, observability             |
| `automation`     | repeated shell workflows, CLI procedures, scripting playbooks         |
| `writing`        | structured writing, publishing, editorial workflows                   |
| `research`       | investigation methods, source-gathering patterns, analysis frameworks |
| `content`        | site-specific publishing, content operations, media handling          |


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
5. Create flat symlinks in both `.agent/skills/` and `.claude/skills/`:
   ```bash
   ln -sf ../../skills/<domain>/<skill-name> .agent/skills/<skill-name>
   ln -sf ../../skills/<domain>/<skill-name> .claude/skills/<skill-name>
   ```

## Naming Guidance

- Directory names should use lowercase kebab-case.
- Skill `name` values should be stable and descriptive.
- Prefer names that state both target and action, such as `mx-space-remote-db-access` or `article-publish-checklist`.


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

| Domain | Skill | Purpose |
|---|---|---|
| `infrastructure` | `mx-space-remote-db-access` | Remote `mx-space` MongoDB inspection, guarded updates, and verification through `ssh -> docker exec -> mongosh` |

## Suggested Domains

| Domain | Typical Content |
|---|---|
| `infrastructure` | deployment, servers, databases, containers, observability |
| `automation` | repeated shell workflows, CLI procedures, scripting playbooks |
| `writing` | structured writing, publishing, editorial workflows |
| `research` | investigation methods, source-gathering patterns, analysis frameworks |
| `content` | site-specific publishing, content operations, media handling |

## Adding a New Skill

1. Create a new directory under `skills/<domain>/<skill-name>/`.
2. Copy `templates/SKILL.template.md` into that directory as `SKILL.md`.
3. Fill in the frontmatter and keep the body concise.
4. Add optional `references/`, `scripts/`, or `assets/` only when they materially improve reuse.

## Naming Guidance

- Directory names should use lowercase kebab-case.
- Skill `name` values should be stable and descriptive.
- Prefer names that state both target and action, such as `mx-space-remote-db-access` or `article-publish-checklist`.

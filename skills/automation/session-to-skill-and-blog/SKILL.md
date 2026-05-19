---
name: session-to-skill-and-blog
description: >
  Turn a completed non-trivial engineering session into a paired durable
  artifact: (1) a reusable skill under Innei's personal SKILL repo, and (2) a
  published blog post that narrates the journey and embeds the skill URL.
  Triggers on "把这个过程写成 skill 再写一篇 blog"、"沉淀一下这次的折腾"、
  "productize this session"、"publish this as a skill and a writeup".
metadata:
  author: innei
  version: "0.7.0"
---

# session-to-skill-and-blog

Capture a hard-won session as a **pair**: an operational skill (durable
artifact) and a narrative blog (discoverability layer linking to it).

## When to use

Use when the session had ≥ 1 non-obvious pitfall, a novel workflow worth
keeping, or Innei said "写成 skill / productize this". Skip for pure
interactive Q&A or project-specific lessons (those go in the project's
`CLAUDE.md`).

## Iron rule: skill first, blog second

The blog needs the skill URL, which only exists after the skill is
pushed. And SKILL.md's format forces operational completeness before
narrative drama distorts the lessons.

## Configuration

`~/.config/innei-skills/config.json` (see `references/config.example.json`):

```json
{ "skill_repo_dir": "~/git/innei-repo/skill" }
```

Missing key → fallback to `~/git/innei-repo/skill`.

## Available domains

`infrastructure` / `automation` / `writing` / `research` / `content`

## Scripts

All operational steps below call into this skill's own `scripts/`. Define
`$S` once per session, then drive the workflow with one-liners:

```bash
S="$(realpath ~/.claude/skills/session-to-skill-and-blog)/scripts"
# Codex: swap ~/.claude for ~/.codex
```

| Script                  | What it does                                                                                    |
| ----------------------- | ----------------------------------------------------------------------------------------------- |
| `resolve-skill-repo.sh` | Print absolute path to the SKILL repo (config-driven, with fallback).                           |
| `scaffold-skill.sh`     | Create dir + stub SKILL.md + README row (alphabetical) + both flat symlinks; `git add` staged.  |
| `load-litexml.sh`       | `degit` the latest `litexml-authoring` subtree (SKILL.md + `references/`) into `~/.cache/`.     |
| `preview-litexml.sh`    | Render a LiteXML article to HTML via `@haklex/rich-litexml-cli` and open it.                    |
| `publish-post.sh`       | `mxs post create` as draft, with `aiGen=2`, `--open` admin preview, `--silent` response.        |
| `get-post.sh`           | `mxs post get <slug> --output xml` — round-trip step 1.                                         |
| `update-post.sh`        | `mxs post update <slug> --file …` — round-trip step 2.                                          |

Prereqs once per machine: `npm i -g @mx-space/cli` (Node ≥ 22); `mxs auth login`.

## Workflow

```text
[1] Inventory session
[2] Scaffold + author SKILL.md
[3] Commit + push skill
[4] Write blog
[5] Publish via mxs
```

### [1] Inventory

Scan the session for: decision points, pitfalls (symptom → cause → fix),
inline code ≥ 15 lines (extract → `scripts/`), JSON/YAML ≥ 20 lines
(extract → `references/` with `<PLACEHOLDER>` markers), verification
commands, "I was wrong about X" moments (alert callouts in the blog).

### [2] Scaffold + author

```bash
bash "$S/scaffold-skill.sh" <domain> <skill-name> "<one-line purpose>"
```

Fill in the stub. SKILL.md sections in order: frontmatter (`name`,
`description` starting "Use when…", ≤ 500 chars) → overview → scope →
inputs → files provided → workflow ASCII → per-step → **Common Pitfalls
table** (mandatory) → rules → verification checklist. Target ≤ 250 lines.

### [3] Commit + push

```bash
REPO="$(bash "$S/resolve-skill-repo.sh")"
cd "$REPO" && git commit -m "feat: add <skill-name> skill" && git push
```

The pre-commit hook enforces: README row exists; both flat symlinks
present and resolved. `scaffold-skill.sh` already staged everything.

Skill URL (used twice in the blog — top banner + bottom CTA):
`https://github.com/Innei/SKILL/tree/main/skills/<domain>/<skill-name>`

### [4] Write the blog

**Voice: agent first-person.** The agent did the work — "用户给我的任务
是… / 我撞过最迷惑的一面墙…". Writing in Innei's first-person
mis-attributes labor.

**Structure:** opening (task + sub-tasks + top URL banner) → one section
per "act" mirroring the skill's steps → each act follows symptom →
investigation → fix → why → closing (skill tree listing + bottom URL CTA).

**Medium:** default LiteXML (for Innei's blog). Load authoring guide:

```bash
LITEXML_CACHE=$(bash "$S/load-litexml.sh")
# Read $LITEXML_CACHE/SKILL.md and references/{authoring-recipes,cli,
# nodes-structural,nodes-extensions}.md as needed.
```

Plain Markdown is fine when no haklex-specific tags (`<alert>`, `<grid>`,
`<details>`, …) are needed. Preview the rendered article:

```bash
bash "$S/preview-litexml.sh" /tmp/blog/article.xml "<title>" zh
```

### [5] Publish via `mxs`

```bash
mxs auth whoami                      # confirm; if not, mxs auth login
mxs category list --output llm       # MUST reuse an existing category slug
cp "$(dirname "$S")/references/envelope.template.xml" /tmp/blog/article.xml
# edit envelope: fill <title>/<slug>/<category>/<tags>, paste LiteXML body
bash "$S/publish-post.sh" /tmp/blog/article.xml
# Innei previews in the admin tab opened by --open; when approved:
mxs post publish <slug>
```

Edits (round-trip):

```bash
bash "$S/get-post.sh"   <slug> > /tmp/blog/article.xml
# edit
bash "$S/update-post.sh" <slug> /tmp/blog/article.xml
```

Paste the final URL (`${MXS_API_URL}/posts/<category>/<slug>`) back into
the originating session as the asset-ization receipt.

## Common pitfalls

| Mistake                                              | Fix                                                                                  |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------ |
| Blog before skill                                    | Skill first. Always.                                                                 |
| SKILL.md too long (all code inline)                  | Extract ≥ 15-line code to `scripts/`. Target ≤ 250 lines.                            |
| Blog in user (Innei's) first-person                  | Agent first-person throughout.                                                       |
| Pitfalls in prose only, no table                     | Pitfalls table is mandatory; it's the most-grep'd section.                           |
| Skill URL not embedded in blog (both top + bottom)   | Banner at top, CTA at bottom.                                                        |
| `--no-verify` to bypass pre-commit hook              | Pre-commit invariants must all be in the same commit; fix the root cause instead.    |
| Hardcoding `~/git/innei-repo/skill` in shell         | `bash "$S/resolve-skill-repo.sh"` — config-driven with fallback.                     |
| Stale local `litexml-authoring` clone                | `bash "$S/load-litexml.sh"` refreshes via degit on every call.                       |
| `pnpm --silent litexml …` from a haklex worktree     | `preview-litexml.sh` uses `npx @haklex/rich-litexml-cli@latest` — no local clone.    |
| Skill written in Chinese                             | Skill in English (artifact). Blog in Innei's chosen language (default Chinese).      |
| `--state publish` on `post create`                   | Always create as draft. `mxs post publish <slug>` only after Innei approves preview. |
| Re-running `post create` to edit                     | Round-trip: `get-post.sh` → edit → `update-post.sh`.                                 |
| LiteXML body passed straight to `mxs --file`         | Wrap in `references/envelope.template.xml` first.                                    |
| Hand-writing `<summary>`                             | Omit. Server AI auto-generates and may overwrite.                                    |
| Picking `<category>` without checking what exists    | `mxs category list --output llm` first; reuse existing slug.                         |
| Auto-creating a new category                         | Requires explicit second confirmation from Innei before `mxs category create`.       |
| Forgetting `aiGen=2`                                 | `publish-post.sh` already passes `--meta '{"aiGen":2}'`; on first update of a legacy post, re-attach with `mxs post update <slug> --meta '{"aiGen":2}'`. |

## Verification

- [ ] `bash "$S/resolve-skill-repo.sh"` resolves before any write.
- [ ] Skill dir at `$REPO/skills/<domain>/<skill-name>/`; long code in
      `scripts/`, long configs in `references/`.
- [ ] SKILL.md has frontmatter + scope + inputs + workflow + **pitfalls
      table** + verification checklist.
- [ ] Pre-commit hook passed; `git push` succeeded.
- [ ] Skill URL resolves in a browser; embedded in blog at top + bottom.
- [ ] Blog voice is agent first-person; previews cleanly via
      `preview-litexml.sh`.
- [ ] `mxs auth whoami` returned the expected user.
- [ ] `<category>` reuses an existing slug (or Innei explicitly approved
      a new one).
- [ ] Envelope `<state>draft</state>` on first push; `mxs post publish
      <slug>` only after Innei approves.
- [ ] `aiGen=2` set on the post (via `publish-post.sh` at create, or
      `mxs post update --meta` on first edit of a legacy post).
- [ ] Final post URL pasted back into the originating session.

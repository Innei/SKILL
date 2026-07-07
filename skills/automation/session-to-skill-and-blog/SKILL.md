---
name: session-to-skill-and-blog
description: >
  Turn a completed non-trivial engineering session into a paired durable
  artifact: (1) a reusable skill under Innei's personal SKILL repo, and (2) a
  published blog post that distills the lessons, linked to the skill via
  the attached skill card (meta.skillIds — never mentioned in the body).
  Triggers on "把这个过程写成 skill 再写一篇 blog"、"沉淀一下这次的折腾"、
  "productize this session"、"publish this as a skill and a writeup".
metadata:
  author: innei
  version: "0.11.0"
---

# session-to-skill-and-blog

Capture a hard-won session as a **pair**: an operational skill (durable
artifact) and a narrative blog (discoverability layer linking to it).

Use when the session had ≥ 1 non-obvious pitfall, a novel workflow worth
keeping, or Innei said "写成 skill / productize this". Skip for pure
interactive Q&A or project-specific lessons (those go in the project's
`CLAUDE.md`).

**Iron rule: skill first, blog second.** The blog attaches the skill via
`meta.skillIds`, which only exists after the skill is pushed to mx-core.
And SKILL.md's format forces operational completeness before narrative
drama distorts the lessons.

## References

This file is a thin index. Load the matching reference when you start the
actual work:

| File                                                       | When to load                                                                                    |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| [`references/writing-style.md`](./references/writing-style.md) | Before drafting prose — persona selection, Willison/Abramov/Antirez voice, punctuation, structure. |
| [`references/node-usage.md`](./references/node-usage.md)   | Before using any extension node — deletion test, escalation ladder, scenario → node map, `<dynamic>` catalog rule, budgets, anti-patterns. |
| [`references/visuals.md`](./references/visuals.md)         | When planning diagrams or uploading image assets — Excalidraw vs Mermaid, palette, ≥3-diagram rule, `mxs file upload`. |
| [`references/publish-flow.md`](./references/publish-flow.md) | When previewing / creating / editing the post — `mxs preview`, draft create, round-trip, stage/apply. |
| [`references/widget-template/`](./references/widget-template/DESIGN.md) | When authoring a new `<dynamic>` widget — Yohaku-language UI/UX guide (`DESIGN.md`) + working vanilla skeleton (`template.mjs`, self-contained tokens, protocol plumbing). |
| `references/envelope.template.xml`                          | Copy as the post envelope before pasting the LiteXML body.                                       |

For LiteXML tag syntax itself, load the litexml-authoring skill (fresh via
`load-litexml.sh`) — this skill governs *whether/when*, that one governs *how*.

## Configuration

`~/.config/innei-skills/config.json` (see `references/config.example.json`):

```json
{ "skill_repo_dir": "~/git/innei-repo/skill" }
```

Missing key → fallback to `~/git/innei-repo/skill`.
Domains: `infrastructure` / `automation` / `writing` / `research` / `content`.
Prereqs once per machine: `npm i -g @mx-space/cli` (Node ≥ 22, needs the
`draft` command group — check `mxs draft --help`); `mxs auth login`.

## Scripts

Define `$S` once per session:

```bash
S="$(realpath ~/.claude/skills/session-to-skill-and-blog)/scripts"
# Codex: swap ~/.claude for ~/.codex
```

| Script                  | What it does                                                                                    |
| ----------------------- | ----------------------------------------------------------------------------------------------- |
| `resolve-skill-repo.sh` | Print absolute path to the SKILL repo (config-driven, with fallback).                           |
| `scaffold-skill.sh`     | Create dir + stub SKILL.md + README row (alphabetical) + both flat symlinks; `git add` staged.  |
| `load-litexml.sh`       | `degit` the latest `litexml-authoring` subtree (SKILL.md + `references/`) into `~/.cache/`.     |
| `push-skill.sh`         | Idempotent `mxs snippet put sk/<name>/SKILL.md --type skill` from a SKILL.md path, plus every sibling asset file (`references/`, `scripts/`, …) as `--type text` under the same dir. Emits the snowflake id on stdout. |
| `create-draft.sh`       | `mxs draft create` — native draft entity (no post yet), with `aiGen=2`, `--open` admin preview, `--silent` → `{ ok, id }`; optional `--skill-id <id>` repeated arg threads ids into `meta.skillIds`. |
| `get-post.sh`           | `mxs post get <slug> --output xml` — round-trip step 1.                                         |
| `update-post.sh`        | `mxs post update <slug> --file …` — round-trip step 2.                                          |

## Workflow

```text
[1] Inventory session
[2] Scaffold + author SKILL.md
[3] Commit + push skill (to GitHub)
[4] Push skill to mx-core (returns snowflake id)
[5] Write blog
[6] Publish via mxs with --skill-id
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
present and resolved. Skill URL (for reference only — never mentioned in
the blog body; the skill card carries the linkage):
`https://github.com/Innei/SKILL/tree/main/skills/<domain>/<skill-name>`

### [4] Push skill to mx-core

The blog post will reference this skill via `meta.skillIds`. Push the
SKILL.md to mx-core's snippet store so the reader-facing `<SkillCardList>`
on the article page has something to render and the public raw URL
(`${MXS_API_URL}/api/v3/s/sk/<name>`) exists.

```bash
SKILL_ID=$(bash "$S/push-skill.sh" "$REPO/skills/<domain>/<skill-name>/SKILL.md")
```

The script is idempotent — `mxs snippet put` upserts by path, so re-runs
update the snippet at `sk/<frontmatter-name>/SKILL.md` instead of creating
a duplicate. `sk/` is the canonical skill root: the backend normalizes
skill-type snippets to it, and Yohaku's `/skills/<name>` pages read from
`/s/sk/<name>/...`.
Sibling asset files (`references/*.md`, `scripts/*`, anything non-hidden
next to SKILL.md) are pushed as `--type text` snippets under the same
`sk/<name>/` dir — the backend rejects `--type skill` for any path not
ending in `/SKILL.md`, and without them relative links inside SKILL.md
404 on the public site.
Capture the returned id; step [6] threads it through `create-draft.sh`.

If the skill never reaches mx-core, the blog still publishes — readers
just won't see the install card. That trade-off is fine when mx-core is
offline; do not block the blog on it.

### [5] Write the blog

Load [`writing-style.md`](./references/writing-style.md) (persona + voice),
[`node-usage.md`](./references/node-usage.md) (which nodes the content
earns), and [`visuals.md`](./references/visuals.md) (diagram plan) before
drafting. The two rules that govern node use:

- **Deletion test**: rewrite the candidate node as a plain paragraph; if no
  information is lost, the node was decoration — don't use it.
- **Escalate, never skip**: prose → verbatim artifacts → structured facts →
  semantic signal → diagram/media → containers → interactive. Interactive
  enters only when the reader's action carries the lesson (parameter
  exploration, algorithm step-through, perceptible difference, self-check —
  see "When interaction teaches" in `node-usage.md`).

Medium: default LiteXML (for Innei's blog). Load the authoring guide fresh:

```bash
LITEXML_CACHE=$(bash "$S/load-litexml.sh")
# Read $LITEXML_CACHE/SKILL.md and its references as needed.
```

Plain Markdown is fine when no haklex-specific tags are needed.

### [6] Publish via `mxs`

Follow [`publish-flow.md`](./references/publish-flow.md): preview →
create a **native draft entity** with the skill id from step [4]
(`bash "$S/create-draft.sh" /tmp/blog/article.xml --skill-id "$SKILL_ID"`
→ `{ ok, id }`; no post exists yet) → iterate with
`mxs draft update <draftId> --file …` → Innei approves →
`mxs draft publish <draftId>` creates the live post in one step.
Post-publication edits prefer `stage` / `apply`, else `get-post.sh` /
`update-post.sh`. Paste the final URL back into the originating session.

## Common pitfalls

| Mistake                                              | Fix                                                                                  |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------ |
| Blog before skill                                    | Skill first. Always.                                                                 |
| SKILL.md too long (all code inline)                  | Extract ≥ 15-line code to `scripts/`. Target ≤ 250 lines.                            |
| Picking a persona by reflex instead of subject       | Default `pattern` (distilled judgments). Use `agent` only when the process *is* the point; `site-owner` only when ownership is Innei's. Apply the selection rule in `writing-style.md`. |
| Writing a `pattern` post that reads as a session transcript | The session is evidence, not spine. If sections are chronological "I did X, Innei said Y", switch to `agent` or extract harder. |
| Switching personas mid-post                          | Pick one and stay. If a `pattern` post needs Innei's ownership voice for one component, demote ownership to third person rather than switch. |
| Node sprinkling ("use more node types")              | Node variety is not a quality metric. Apply the deletion test per node (`node-usage.md`). |
| Pitfalls in prose only, no table                     | Pitfalls table is mandatory; it's the most-grep'd section.                           |
| Mentioning the skill in the blog body (opener "操作手册见…", bottom CTA, banner) | Zero in-text mention. `meta.skillIds` renders the skill card; the body never discusses its own artifacts. |
| `--no-verify` to bypass pre-commit hook              | Pre-commit invariants must all be in the same commit; fix the root cause instead.    |
| Hardcoding `~/git/innei-repo/skill` in shell         | `bash "$S/resolve-skill-repo.sh"` — config-driven with fallback.                     |
| Stale local `litexml-authoring` clone                | `bash "$S/load-litexml.sh"` refreshes via degit on every call.                       |
| `pnpm --silent litexml …` from a haklex worktree     | `mxs preview <file>` — envelope-aware, no local clone, opens browser by default.     |
| Skill written in Chinese                             | Skill in English (artifact). Blog in Innei's chosen language (default Chinese).      |
| Creating a post (even with `--state draft`) to stage the article | Use the native draft entity: `create-draft.sh` → `mxs draft publish <id>`. A draft-state post pollutes the post list and risks the `<state>` unpublish trap; a draft entity cannot leak. Legacy fallback (`mxs` without the `draft` group): `post create --state draft` + `post publish <slug>`. |
| `mxs draft publish` before Innei approves            | Publish creates the live post immediately. Only run it after Innei approves the admin preview. |
| Skipping `push-skill.sh` and embedding only the GitHub URL | The blog `<SkillCardList>` reads `meta.skillIds`. Without `--skill-id`, the install card never renders even if the GitHub link is right. |
| Hand-writing `--meta '{"aiGen":2,"skillIds":[…]}'`   | Use `create-draft.sh --skill-id <id>`; it jq-assembles meta and survives multiple ids without quoting bugs. |
| Re-running `draft create` to edit                    | `mxs draft update <draftId> --file …` — versioned, keeps history. After publication: `get-post.sh` → edit → `update-post.sh`. |
| Updating a published post with the create envelope   | A stray `<state>draft</state>` unpublishes the live post — readers see it vanish. `update-post.sh` strips `<state>`; publish state changes only via `mxs post publish\|unpublish`. |
| LiteXML body passed straight to `mxs --file`         | Wrap in `references/envelope.template.xml` first.                                    |
| Previewing a bare LiteXML fragment (no `<doc>`)      | Inter-block whitespace becomes root-level text nodes → Lexical error #282. Keep authoring sources `<doc>`-wrapped; mxs wraps server-side. |
| `<dynamic>` with an invented or adapted URL          | Catalog-gated: only URLs from `${MXS_API_URL}/s/dynamic-widgets-catalog`. No catalog → no `<dynamic>`; degrade per `node-usage.md`. |
| Hand-writing `<summary>`                             | Omit. Server AI auto-generates and may overwrite.                                    |
| Picking `<category>` without checking what exists    | `mxs category list --output llm` first; reuse existing slug.                         |
| Auto-creating a new category                         | Requires explicit second confirmation from Innei before `mxs category create`.       |
| Forgetting `aiGen=2`                                 | `create-draft.sh` already passes `--meta '{"aiGen":2}'` (carried through `draft publish`); on first update of a legacy post, re-attach with `mxs post update <slug> --meta '{"aiGen":2}'`. |

## Verification

- [ ] `bash "$S/resolve-skill-repo.sh"` resolves before any write.
- [ ] Skill dir at `$REPO/skills/<domain>/<skill-name>/`; long code in
      `scripts/`, long configs in `references/`.
- [ ] SKILL.md has frontmatter + scope + inputs + workflow + **pitfalls
      table** + verification checklist.
- [ ] Pre-commit hook passed; `git push` succeeded.
- [ ] `bash "$S/push-skill.sh" …` returned a snowflake id; the public URL
      `${MXS_API_URL}/api/v3/s/sk/<name>` resolves to the raw markdown.
- [ ] Blog body has **zero** mention of the skill (no opener pointer, no
      bottom CTA, no banner) — the skill card carries the linkage.
- [ ] Voice follows `writing-style.md`: one persona throughout (default
      `pattern`; `agent` only when the process is the point; `site-owner`
      only when Innei owns the subject); every section passes the substance
      check (transferable judgment woven in prose, real failure evidence,
      reconstructible fix) without isomorphic section shapes; none of the
      hard bans (meta-narrative, fixed-phrase labels, closing recap,
      decorative callouts) appear; Willison transparency, Abramov arc,
      Antirez 断语; em-dashes sparing.
- [ ] Visuals follow `visuals.md`: ≥ 3 Excalidraw diagrams for substantial
      `site-owner` posts, each answering a named question.
- [ ] Node audit passed (`node-usage.md`): every non-prose node holds a
      one-clause deletion-test justification; alerts and banner default 0
      (alert only for named real damage, banner only for post-level status);
      interactive nodes enter only via a "When interaction teaches" scenario.
- [ ] `mxs auth whoami` returned the expected user; `<category>` reuses an
      existing slug (or Innei explicitly approved a new one).
- [ ] Article staged as a native draft entity (`create-draft.sh` →
      `{ ok, id }`); `mxs draft publish <draftId>` only after Innei
      approves; `aiGen=2` set (rides into the post at publish).
- [ ] Final post URL pasted back into the originating session.

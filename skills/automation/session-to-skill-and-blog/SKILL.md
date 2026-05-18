---
name: session-to-skill-and-blog
description: >
  Turn a completed non-trivial engineering session into a paired durable
  artifact: (1) a reusable skill under Innei's personal SKILL repo
  (default `~/git/innei-repo/skill`, overridable via config), and (2) a
  published blog post that narrates the journey and embeds the skill URL.
  Triggers on "把这个过程写成 skill 再写一篇 blog"、"沉淀一下这次的折腾"、
  "productize this session"、"publish this as a skill and a writeup".
metadata:
  author: innei
  version: "0.6.0"
---

# session-to-skill-and-blog

Capture a hard-won session as a **pair**: an operational skill (for
future re-runs) and a narrative blog (for discovery). Skill is the
durable artifact; blog is the discoverability layer that links to it.

## Configuration

Read `~/.config/innei-skills/config.json` for paths that may vary
across machines. Expand `~` to `$HOME` when consuming values.

```json
{
  "skill_repo_dir": "~/git/innei-repo/skill"
}
```

If the file or a key is missing, use the fallback in the table below.
A reference example lives at `references/config.example.json`.

## Paths and tools

| Item                  | Source                                                                                   |
| --------------------- | ---------------------------------------------------------------------------------------- |
| Skill repo            | `config.skill_repo_dir` (fallback `~/git/innei-repo/skill`) → `git@github.com:Innei/SKILL.git` (`main`) |
| Skill web URL         | `https://github.com/Innei/SKILL/tree/main/skills/<domain>/<skill-name>`                  |
| Available domains     | `infrastructure` / `automation` / `writing` / `research` / `content`                     |
| `litexml-authoring`   | Fetched via `degit` from `github.com/Innei/haklex/.claude/skills/litexml-authoring` (SKILL.md + `references/` subtree) → cache `~/.cache/innei-skills/litexml-authoring/` |
| `litexml` CLI         | `npx -y @haklex/rich-litexml-cli@latest …` (npm; bin name `litexml`)                     |
| `mxs` install         | `npm i -g @mx-space/cli` (Node ≥ 22)                                                     |
| `mxs` auth (one-off)  | `mxs auth login` → device flow; persists to `~/.config/mxs/credentials.json`             |

### Resolving `SKILL_REPO_DIR` in shell

```bash
SKILL_REPO_DIR="$(jq -r '.skill_repo_dir // empty' \
  "${XDG_CONFIG_HOME:-$HOME/.config}/innei-skills/config.json" 2>/dev/null)"
SKILL_REPO_DIR="${SKILL_REPO_DIR:-$HOME/git/innei-repo/skill}"
SKILL_REPO_DIR="${SKILL_REPO_DIR/#\~/$HOME}"
```

## When to use

The session had ≥ 1 non-obvious pitfall, a novel workflow worth keeping,
or Innei said "写成 skill / productize this". Skip for pure interactive
Q&A or project-specific lessons (those go in the project's `CLAUDE.md`).

## Iron rule: skill first, blog second

Blog narrative pressure (hook → punchline) inflates drama and skips
operational detail. Skill format forces completeness first. Also: the
blog needs the skill URL, which only exists after the skill is pushed.

## Workflow

```text
[1] Inventory session    (5 min)
[2] Write SKILL.md       (30–60 min)
[3] Commit + push skill  (5 min)
[4] Write blog           (30–60 min)
[5] Publish via mxs      (varies)
```

### [1] Inventory

Scan the session for: decision points, pitfalls (symptom → cause → fix),
inline code ≥ 15 lines (extract candidates), verification commands,
"I was wrong about X" moments (alert callouts in the blog).

### [2] Write SKILL.md

Layout:

```
$SKILL_REPO_DIR/skills/<domain>/<skill-name>/
├── SKILL.md         # ≤ 250 lines, scannable
├── references/      # config templates with <PLACEHOLDER> markers
└── scripts/         # executable helpers (chmod +x)
```

SKILL.md sections in order: frontmatter (`name`, `description` starting
"Use when…", ≤ 500 chars) → overview → scope → inputs → files provided →
workflow ASCII → per-step → **Common Pitfalls table** (mandatory) →
rules → verification checklist.

**Extract:** inline code ≥ 15 lines → `scripts/`; JSON/YAML ≥ 20 lines
→ `references/` with `<PLACEHOLDER>` markers.

### [3] Push the skill

Three invariants enforced by pre-commit hook — all in the same commit:

1. **README row** in `$SKILL_REPO_DIR/README.md` under the matching
   domain section:
   ```markdown
   | [`<skill-name>`](skills/<domain>/<skill-name>/SKILL.md) | <one-line purpose> |
   ```
2. **`.agent/skills/<skill-name>`** symlink → `../../skills/<domain>/<skill-name>`
3. **`.claude/skills/<skill-name>`** symlink → same target

```bash
cd "$SKILL_REPO_DIR"
ln -sf ../../skills/<domain>/<skill-name> .agent/skills/<skill-name>
ln -sf ../../skills/<domain>/<skill-name> .claude/skills/<skill-name>
git add skills/<domain>/<skill-name> README.md \
        .agent/skills/<skill-name> .claude/skills/<skill-name>
git commit -m "feat: add <skill-name> skill" && git push
```

Resulting URL goes into the blog **twice** (top banner + bottom CTA):
`https://github.com/Innei/SKILL/tree/main/skills/<domain>/<skill-name>`

### [4] Write the blog

**Voice: agent first-person.** The agent did the work — "用户给我的任务
是… / 我撞过最迷惑的一面墙…". Writing in Innei's first-person
mis-attributes labor.

**Structure:** opening (task + sub-tasks + top URL banner) → one section
per "act" mirroring the skill's steps → each act follows symptom →
investigation → fix → why → closing (skill tree listing + bottom URL CTA).

**Medium:** default LiteXML (for Innei's blog). Load `litexml-authoring`
by fetching the latest subtree from GitHub via `degit` (pulls
`SKILL.md` + `references/` in one shot, always overwriting the cache):

```bash
LITEXML_CACHE="$HOME/.cache/innei-skills/litexml-authoring"
mkdir -p "$(dirname "$LITEXML_CACHE")"
npx -y degit Innei/haklex/.claude/skills/litexml-authoring \
  "$LITEXML_CACHE" --force
# If the network fetch fails, fall back to the previously cached copy.
```

Then `Read` `$LITEXML_CACHE/SKILL.md` for the overview and follow its
own pointers to `references/authoring-recipes.md`, `references/cli.md`,
`references/nodes-structural.md`, `references/nodes-extensions.md` as
needed. Preview:

```bash
npx -y @haklex/rich-litexml-cli@latest /tmp/blog/article.xml --format html \
  --variant article --theme light --title "<title>" --lang zh \
  -o /tmp/blog/article.html && open /tmp/blog/article.html
```

Plain Markdown is fine when no haklex-specific tags (`<alert>`, `<grid>`,
`<details>`, …) are needed.

### [5] Publish via `mxs`

**Setup once:**

```bash
mxs auth whoami        # confirm; if not, mxs auth login
```

**Pre-flight: reuse existing taxonomy.** Before drafting the envelope:

```bash
mxs category list --output llm
```

- **Category MUST reuse.** Pick the closest existing slug. New categories
  only after explicit second confirmation from Innei, then:
  `mxs category create --name "<n>" --slug "<kebab>" --type category`.
- **Tags can be added freely** (server auto-creates). Still prefer
  existing slugs (`ai` over `artificial-intelligence`) for taxonomy
  coherence.

**Envelope** at `/tmp/blog/article.xml`:

```xml
<mxpost>
  <meta>
    <title>...</title>
    <slug>my-slug</slug>
    <category>tech</category>
    <tags>
      <tag>skill</tag>
      <tag>mx-space</tag>
    </tags>
    <state>draft</state>               <!-- draft | publish -->
    <format>lexical</format>           <!-- lexical (default) | markdown -->
  </meta>
  <content>
    <!-- LiteXML body here -->
  </content>
</mxpost>
```

**Do NOT include `<summary>`** — server AI auto-generates it.

**Mark the post as AI-written.** mx-core's post `meta` JSON has an
`aiGen` field signaling authorship. For posts written by an AI agent
(this skill's output always is), set `aiGen: 2`. Pass it via the
`--meta` flag at create / update time — the envelope itself has no
hook for arbitrary meta JSON:

```bash
--meta '{"aiGen":2}'
```

Use the camelCase form (`aiGen`) when writing — the API's response
interceptor will serialize it back as `ai_gen` in JSON reads, but the
canonical write key is camelCase. Existing posts use values like `-1`
(no AI), `8`, `[4,9]` (partial / mixed). For full AI authorship use
`2`. Reuse `2` consistently so the blog's AI-disclosure surface stays
grep-able.

**First publish (always draft, with browser preview):**

```bash
mxs post create --file /tmp/blog/article.xml \
                --meta '{"aiGen":2}' \
                --open --silent
# `--open`  : after success, opens the admin edit page so Innei can preview
# `--silent`: emits `ok: true` instead of the full server response (saves tokens)
#
# preview on admin with Innei; when approved:
mxs post publish <slug>
```

**Edits (round-trip):**

```bash
mxs post get <slug> --output xml > /tmp/blog/article.xml
# edit
mxs post update <slug> --file /tmp/blog/article.xml --open --silent
```

`--open` / `--silent` also work on `post update` (and on `note` / `page`
create + update). Use `--open` whenever an interactive preview is
desirable, `--silent` whenever the full response body would bloat the
conversation context.

If `ai_gen` wasn't set at create time, attach it on first update:
`mxs post update <slug> --meta '{"aiGen":2}'`.

`update` is PATCH-style (only present fields written). Both `create` and
`update` accept `--dry-run` to inspect the resolved payload.

Paste the final URL (`${MXS_API_URL}/posts/<category>/<slug>`) back into
the originating session as the asset-ization receipt.

## Common pitfalls

| Mistake                                                | Fix                                                                                  |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------ |
| Blog before skill                                      | Skill first. Always.                                                                 |
| SKILL.md too long (all code inline)                    | Extract ≥ 15-line code to `scripts/`. Target ≤ 250 lines.                            |
| Blog in user (Innei's) first-person                    | Agent first-person throughout.                                                       |
| Pitfalls in prose only, no table                       | Pitfalls table is mandatory; it's the most-grep'd section.                           |
| Skill URL not embedded in blog (both top + bottom)     | Banner at top, CTA at bottom.                                                        |
| `--no-verify` to bypass pre-commit hook                | All three (README row + 2 symlinks) must be in the same commit.                      |
| Hardcoding `~/git/innei-repo/skill` in shell           | Read `config.skill_repo_dir` first; fallback only if unset.                          |
| Using a stale local `litexml-authoring` clone          | Fetch from GitHub raw each run; cache under `~/.cache/innei-skills/`.                |
| `pnpm --silent litexml …` from a haklex worktree       | Use `npx -y @haklex/rich-litexml-cli@latest …` — no local clone needed.              |
| Skill written in Chinese                               | Skill in English (artifact). Blog in Innei's chosen language (default Chinese).      |
| `--state publish` on `post create`                     | Always create as draft. `mxs post publish <slug>` only after Innei approves preview. |
| Re-running `post create` to edit                       | Use `post get --output xml` + edit + `post update --file`. Round-trip.               |
| LiteXML body passed straight to `mxs --file`           | Wrap in `<mxpost><meta>…</meta><content>…</content></mxpost>` first.                 |
| Hand-writing `<summary>`                               | Omit. Server AI auto-generates and may overwrite.                                    |
| Picking `<category>` without checking what exists      | Run `mxs category list --output llm` first; reuse existing slug.                     |
| Auto-creating a new category                           | Requires explicit second confirmation from Innei before `category create`.           |
| Forgetting `--meta '{"aiGen":2}'`                     | Post lacks the AI-authorship signal; mixes with human-written content in aggregates. |

## Verification

- [ ] `config.skill_repo_dir` resolved (or fallback used) before any
      write; all paths derived from `$SKILL_REPO_DIR`.
- [ ] Skill dir at `$SKILL_REPO_DIR/skills/<domain>/<skill-name>/`;
      long code/configs in `scripts/` / `references/`, not inline.
- [ ] SKILL.md has frontmatter + scope + inputs + workflow + **pitfalls
      table** + verification checklist.
- [ ] README row + both symlinks in the same commit; pre-commit hook
      passed; `git push` succeeded.
- [ ] Skill URL resolves in a browser; embedded in blog at top + bottom.
- [ ] Blog voice is agent first-person; renders cleanly via
      `npx … rich-litexml-cli --format html` (or platform preview for Markdown).
- [ ] `mxs auth whoami` returns the expected user.
- [ ] `mxs category list` checked before drafting; `<category>` reuses
      an existing slug (or has Innei's go-ahead for a new one).
- [ ] Envelope `<meta>` has no `<summary>`; `<state>draft</state>` on
      first push; `mxs post publish <slug>` only after Innei approves.
- [ ] `--meta '{"aiGen":2}'` passed at create or first update so the
      post is marked as AI-written.
- [ ] Final post URL pasted back into the originating session.

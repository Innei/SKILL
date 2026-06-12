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
  version: "0.8.0"
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

**Voice: pick one of two personas.** Decide by what the blog is actually
about: the *process* or the *thing*.

| Persona                   | Use when                                                                                                            | "I" refers to |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------- | ------------- |
| `agent` first-person      | The blog narrates a session/dogfood run — symptom → investigation → fix → why (e.g. the nextjs → react-router post) | the agent     |
| `site-owner` first-person | The blog is about a tool, workflow, format, or system that Innei designed and owns                                  | Innei         |

Selection rule: if the main subject is a *process the agent went through*,
use `agent`. If the main subject is a *thing Innei built* (CLI, format,
workflow, infra), use `site-owner`. Writing in agent voice when the
ownership is Innei's misattributes the design labor to the executor.

When the post needs both (Innei's design intent plus a dogfood run that
exposed an issue), stay in `site-owner` voice and refer to the agent in
third person, e.g. "an agent run surfaced X, so I fixed Y". Do not switch
personas mid-post.

#### `site-owner` style — Willison + Abramov + Antirez

When writing in `site-owner` persona, combine three reference styles. Each
contributes a distinct property; together they keep the prose honest,
structured, and assertive.

- **Willison transparency.** Show your work. Quote real error output, commit
  hashes, exact version numbers, the actual file path you edited. No mystery,
  no hand-waving. Link to source liberally. When something failed, say so —
  including which approach you tried first and why it didn't work.
- **Abramov arc.** Each section has setup → tension → payoff. Open with an
  observation, a constraint, or a question. Build the reader's expectation.
  Then resolve. Use concrete examples to drive abstract points, not the other
  way around. The reader should feel they're discovering something *with*
  you, not being lectured at.
- **Antirez 断语.** Short, declarative sentences for conclusions. No
  hedging. "X is wrong." "Y works." "Don't do Z." Stand-alone lines that
  carry the weight of a decision. Use them at section breaks and at the end
  of paragraphs that earn them.

#### Punctuation

- **Em-dashes (——) sparingly.** The default punctuation is `。` `，` `：` `；`
  or parentheses. Reserve `——` for genuine asides, mid-sentence
  interruptions, or true em-dash thought-jumps. A row of em-dashes in close
  succession reads as lazy structure.
- Prefer two short sentences over one long sentence joined by an em-dash.
- Use `：` to introduce a list, example, or definition.
- Use `（）` for parenthetical asides that are tightly bound to the surrounding
  sentence.
- Quote tag names and code identifiers in `<code>...</code>`, not `「...」`.

#### Visuals

Prefer Excalidraw over Mermaid in `site-owner` posts. The hand-drawn feel
matches the personal voice, and Excalidraw is more flexible for the kinds
of diagrams `site-owner` posts tend to need:

| Diagram type                       | Use         | Why                                                            |
| ---------------------------------- | ----------- | -------------------------------------------------------------- |
| Decision tree / branching choice   | Excalidraw  | Diamond + labeled branches reads cleaner than Mermaid          |
| Architecture lanes (named columns) | Excalidraw  | Lane backgrounds with title + bullet body are highly readable  |
| Timeline / event chain             | Excalidraw  | Vertical spine + color-coded entries beats a Mermaid gantt     |
| Pipeline (linear N-step flow)      | Excalidraw  | Boxes + arrows in a row, hand-drawn rectangles feel right      |
| Strict sequence diagram            | Mermaid     | When precise actor lifelines + ordered messages are required   |
| Dense flowchart with many edges    | Mermaid     | Auto-routing handles edge crossings better                     |

Embed Excalidraw inline as `<excalidraw><![CDATA[{...scene JSON...}]]></excalidraw>`.
Use the canonical color palette (light blue / light purple / light yellow /
light green / light pink). Position text elements explicitly; do not rely
on auto-centering across blog renderers.

For `site-owner` posts of any substance, **aim for at least three Excalidraw
diagrams** — one for the high-level pipeline, one for the architecture
overview, one for the most important decision or chain narrated in prose.
More is fine. Use Mermaid only when the diagram type column above says so.

#### Interactive embeds (`<dynamic>`)

Since haklex v0.25.1 a post can embed an interactive ESM widget (quiz,
parameter explorer, step-through demo) via the `<dynamic>` tag. It is
**catalog-gated**: the URL executes code in readers' browsers, so only
components listed in the blog's catalog may be referenced. Check first:

```bash
curl -fsS "${MXS_API_URL}/objects/file/dynamic-widgets-catalog.json"
```

- Catalog resolves → pick a matching entry, use its exact `url` and
  recommended `initial-height`, validate props against its `propsSchema`.
  Full tag rules live in the litexml-authoring reference
  (`nodes-extensions.md` → "Embedded interactive components").
- 404 / empty → the blog has no widgets deployed yet. Do **not** emit
  `<dynamic>`; fall back to `<poll>` (votes), `<excalidraw>` (diagrams),
  or `<video>` (demos), and mention the gap to Innei.

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
mxs preview /tmp/blog/article.xml
```

`mxs preview` is envelope-aware: it strips the `<mxpost>` / `<mxnote>`
wrapper, auto-detects `--variant`, and opens the HTML in the system
browser by default. Pass `--print` to dump to stdout, `--save <path>` to
write a file without opening.

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

Editing an already-published post: prefer stage/apply when the installed
`mxs` supports it (`mxs post stage --help`) — the live post stays untouched
until Innei confirms:

```bash
mxs post stage <slug> --file /tmp/blog/article.xml   # readers see nothing
# Innei reviews (local preview / admin), then approves:
mxs post apply <slug>                                # the confirm step
```

Fallback on older `mxs`: `update-post.sh` (it strips `<state>` so the post
at least never unpublishes, but changes go live immediately).

### Images and Excalidraw attachments

When the installed `mxs` has the `file` command group (`mxs file --help`),
upload assets instead of inlining or hot-linking:

```bash
mxs file upload ./shot.png --type image --silent   # → { url, name }
mxs file upload ./diagram.excalidraw --type file --silent
```

- Images: reference the returned URL via `<img src="..." />`.
- Excalidraw: the `<excalidraw>` body accepts a bare URL (remote snapshot) —
  `<excalidraw>https://…/diagram.excalidraw</excalidraw>` — instead of inline
  CDATA JSON. Prefer remote for large scenes; keep small scenes inline so the
  article stays self-contained.
- Manage assets with `mxs file list|delete|rename [--type <t>]`.

Paste the final URL (`${MXS_API_URL}/posts/<category>/<slug>`) back into
the originating session as the asset-ization receipt.

## Common pitfalls

| Mistake                                              | Fix                                                                                  |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------ |
| Blog before skill                                    | Skill first. Always.                                                                 |
| SKILL.md too long (all code inline)                  | Extract ≥ 15-line code to `scripts/`. Target ≤ 250 lines.                            |
| Picking a persona by reflex instead of subject       | Process narrative → `agent`. Owned tool/format/workflow → `site-owner`. Apply the selection rule. |
| Switching personas mid-post                          | Pick one and stay. If both are needed, keep `site-owner` voice and refer to the agent in third person. |
| Pitfalls in prose only, no table                     | Pitfalls table is mandatory; it's the most-grep'd section.                           |
| Skill URL not embedded in blog (both top + bottom)   | Banner at top, CTA at bottom.                                                        |
| `--no-verify` to bypass pre-commit hook              | Pre-commit invariants must all be in the same commit; fix the root cause instead.    |
| Hardcoding `~/git/innei-repo/skill` in shell         | `bash "$S/resolve-skill-repo.sh"` — config-driven with fallback.                     |
| Stale local `litexml-authoring` clone                | `bash "$S/load-litexml.sh"` refreshes via degit on every call.                       |
| `pnpm --silent litexml …` from a haklex worktree     | `mxs preview <file>` — envelope-aware, no local clone, opens browser by default.     |
| Skill written in Chinese                             | Skill in English (artifact). Blog in Innei's chosen language (default Chinese).      |
| `--state publish` on `post create`                   | Always create as draft. `mxs post publish <slug>` only after Innei approves preview. |
| Re-running `post create` to edit                     | Round-trip: `get-post.sh` → edit → `update-post.sh`.                                 |
| Updating a published post with the create envelope   | Its `<state>draft</state>` unpublishes the live post — readers see it vanish. `update-post.sh` now strips `<state>` before sending; publish state changes only via `mxs post publish\|unpublish`. |
| LiteXML body passed straight to `mxs --file`         | Wrap in `references/envelope.template.xml` first.                                    |
| Previewing a bare LiteXML fragment (no `<doc>`)      | Inter-block whitespace becomes root-level text nodes → Lexical error #282 in the rendered HTML. Keep authoring sources `<doc>`-wrapped. mxs wraps server-side, so the published post is unaffected. |
| `<dynamic>` with an invented or adapted URL          | Catalog-gated: only URLs from `${MXS_API_URL}/objects/file/dynamic-widgets-catalog.json`. No catalog → no `<dynamic>`; degrade to `<poll>`/`<excalidraw>`/`<video>`. |
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
- [ ] Blog voice picks `agent` or `site-owner` per the selection rule and
      stays in that persona throughout; previews cleanly via `mxs preview`.
- [ ] For `site-owner` posts: Willison transparency (real errors / commits /
      paths quoted), Abramov arc (setup → tension → payoff per section),
      Antirez 断语 (short declarative conclusions). Em-dashes used sparingly.
      At least three Excalidraw diagrams.
- [ ] `mxs auth whoami` returned the expected user.
- [ ] `<category>` reuses an existing slug (or Innei explicitly approved
      a new one).
- [ ] Envelope `<state>draft</state>` on first push; `mxs post publish
      <slug>` only after Innei approves.
- [ ] `aiGen=2` set on the post (via `publish-post.sh` at create, or
      `mxs post update --meta` on first edit of a legacy post).
- [ ] Final post URL pasted back into the originating session.

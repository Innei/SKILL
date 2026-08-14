---
name: session-to-skill-and-blog
description: >
  Convert a completed engineering session into a narrative blog and zero or
  more reusable operational skills. Use when Innei explicitly asks to
  productize, document, or publish a finished session ("写成 skill 再写一篇
  blog", "沉淀一下这次的折腾", "productize this session", or "publish this as
  a skill and a writeup"). Classify project-local facts separately.
---

# session-to-skill-and-blog

Turn session evidence into the appropriate durable outputs:

- a blog that explains the experience, reasoning, and conclusion;
- zero or more skills that let a future agent execute reusable capabilities;
- project documentation for facts and conventions that remain local.

Do not force a one-to-one pair. One blog may attach no skill, one skill, or
several skills; one skill may support several later blogs. The outputs share
evidence, not structure.

**Classify first. For every accepted skill candidate, author and push the
skill before writing the blog.** This preserves the operational contract
before narrative compression. If no candidate passes the skill gate, write
the blog without inventing a skill.

## References

This file is a thin index. Load the matching reference when you start the
actual work:

| File | When to load |
| ---- | ------------ |
| [`references/writing-style.md`](./references/writing-style.md) | Before drafting prose — reading contract, title and slug, sections, narrative, argument, narrator, and anti-slop editing. |
| [`references/node-usage.md`](./references/node-usage.md) | Before using any extension node — deletion test, escalation ladder, catalog rule. |
| [`references/visuals.md`](./references/visuals.md) | When prose creates a visual-explanation question, or when uploading image assets. |
| [`references/editorial-models.md`](./references/editorial-models.md) | Only when revising the editorial policy — primary-source research and derived principles. |
| [`references/publish-flow.md`](./references/publish-flow.md) | When previewing / creating / editing / publishing the post. |
| [`references/widget-template/`](./references/widget-template/DESIGN.md) | When authoring a new `<dynamic>` widget. |
| `references/envelope.template.xml` | Copy as the post envelope before pasting the LiteXML body. |
| `no-ai-slop` (via `load-no-ai-slop.sh`) | After the draft is written, before publishing — detect candidates, revise manually, rerun. |

For LiteXML tag syntax itself, load the litexml-authoring skill (fresh via
`load-litexml.sh`) — this skill governs *whether/when*, that one governs *how*.

## Configuration

`~/.config/innei-skills/config.json` (see `references/config.example.json`):

```json
{ "skill_repo_dir": "~/git/innei-repo/SKILL" }
```

Missing key → fallback to `~/git/innei-repo/SKILL`.
Domains: `infrastructure` / `automation` / `writing` / `research` / `content`.
Prereqs once per machine: `npm i -g @mx-space/cli` (Node ≥ 22, needs the
`draft` command group — check `mxs draft --help`); `mxs auth login`.

## Scripts

Define `$S` once per session. Search known locations; the first that
contains `resolve-skill-repo.sh` wins:

```bash
S=""
for cand in \
  "$HOME/.claude/skills/session-to-skill-and-blog/scripts" \
  "$HOME/.codex/skills/session-to-skill-and-blog/scripts" \
  "$HOME/.agents/skills/session-to-skill-and-blog/scripts" \
  "$(git rev-parse --show-toplevel 2>/dev/null)/.claude/skills/session-to-skill-and-blog/scripts" \
  "$(git rev-parse --show-toplevel 2>/dev/null)/.agent/skills/session-to-skill-and-blog/scripts" \
  "$(git rev-parse --show-toplevel 2>/dev/null)/skills/automation/session-to-skill-and-blog/scripts"
do
  [ -n "$cand" ] && [ -f "$cand/resolve-skill-repo.sh" ] && {
    S="$(cd "$cand" && pwd)"; break
  }
done
[ -n "$S" ] || { echo "error: cannot locate session-to-skill-and-blog/scripts" >&2; exit 1; }
REPO="$(bash "$S/resolve-skill-repo.sh")"
```

| Script | What it does |
| ------ | ------------ |
| `resolve-skill-repo.sh` | Print absolute path to the SKILL repo (config-driven, with fallback). |
| `scaffold-skill.sh` | Create dir + stub SKILL.md + README row (alphabetical, domain-scoped) + both flat symlinks; `git add` staged. |
| `load-litexml.sh` | `degit` the latest `litexml-authoring` subtree into `~/.cache/`. |
| `load-no-ai-slop.sh` | `degit` the latest `no-ai-slop` skill into `~/.cache/`. If unavailable, report it and continue with the internal hard-ban sweep. |
| `push-skill.sh` | Idempotent `mxs snippet put sk/<name>/SKILL.md --type skill`, plus sibling assets as `--type text`. Emits the snowflake id on stdout. |
| `create-draft.sh` | `mxs draft create` with `aiGen=2`, `--open`, `--silent` → `{ ok, id }`; `--skill-id <id>` (repeatable) threads ids into `meta.skillIds`. |
| `get-post.sh` | `mxs post get <slug> --output xml` — round-trip step 1. |
| `update-post.sh` | `mxs post update <slug> --file …` — strips `<state>`, then updates. |
| `image-meta.mjs` | Emit `width` / `height` / `thumbhash` for a LiteXML `<img>`. Run from a project that has `sharp` + `thumbhash` (e.g. mx-core). |

## Workflow

```text
[1] Inventory and classify session evidence
[2] State and evaluate each capability thesis
       rejected ──> blog or project documentation
       accepted ──> one coherent skill
[3] Scaffold, author, validate, commit, and push accepted skills
[4] Push accepted skills to mx-core and collect their ids
[5] Write the blog from the narrative evidence
[6] Publish via mxs with zero or more --skill-id arguments
```

### [1] Inventory and classify

Collect decision points, failed assumptions, symptom-to-cause evidence,
commands, reusable procedures, safety boundaries, verification results, and
project-local facts. Classify each item by its future function:

| Destination | Include | Exclude |
| ----------- | ------- | ------- |
| Blog | Context, chronology, argument, representative failures, and interpretation | Exhaustive operating instructions |
| Skill | Repeatable action, decision boundary, non-obvious constraint, and observable proof | Session chronology and personal reflection |
| Project documentation | Repository-specific ownership, commands, architecture, and persistent local conventions | General reusable workflow |

Treat code or configuration length only as a resource-planning signal. It is
not evidence that a skill should exist.

### [2] State and evaluate the capability thesis

Write this sentence before scaffolding a candidate:

> This skill helps an agent **[action] [target]** when **[trigger]**, while
> preserving **[constraint]**, and verifies success through **[observable
> outcome]**.

Reject or redirect the candidate unless every gate passes:

| Gate | Pass condition | If it fails |
| ---- | -------------- | ----------- |
| Triggerability | A concrete future user request can activate it. | Keep the material in the blog. |
| Repeatability | The action or decision is likely to recur. | Use the blog or project documentation. |
| Knowledge delta | It teaches non-obvious procedure, local integration, or a hard-won failure boundary. | Do not create a skill. |
| Coherence | It has one trigger family, one operational target, and one primary outcome. | Split independent capabilities. |
| Verifiability | Success is externally observable. | Treat it as analysis or reference material. |
| Stability | The core method survives routine version changes. | Move volatile facts to references or project documentation. |
| Boundary clarity | It states exclusions and stopping conditions. | Narrow the capability. |

Name accepted skills with a concise, verb-led target and action. Prefer
`split-dokploy-traffic-safely` over `traefik-notes`, and
`migrate-nextjs-rsc-under-cdn-constraints` over `nextjs-migration`.

Keep one capability thesis per skill. Split candidates when their triggers,
targets, or completion criteria can vary independently. Place cross-project
capabilities in this repository; place facts that only future work in one
repository needs in that repository's agent or project documentation.

Plan bundled resources by function, not by arbitrary line count:

| Resource | Add when |
| -------- | -------- |
| `scripts/` | An operation is deterministic, fragile, or repeatedly rewritten. |
| `references/` | Schemas, protocols, detailed examples, or volatile facts would obscure the operational core. |
| `assets/` | The skill must copy or transform an output resource. |

Do not create empty resource directories.

### [3] Scaffold, author, and push accepted skills

```bash
bash "$S/scaffold-skill.sh" <domain> <skill-name> "<one-line purpose>"
```

Use the scaffold once for each accepted capability. Author the skill as an
execution interface for a future agent, not as a compressed version of the
blog.

Every generated skill requires this contract:

| Required element | Standard |
| ---------------- | -------- |
| Frontmatter | Include only `name` and `description`. Put both capability and all trigger conditions in `description`; do not repeat a body-level "When to use" section. |
| Capability boundary | State the outcome, prerequisites, exclusions, and stopping conditions. |
| Operational core | Give the shortest sufficient procedure or decision path in dependency order. Use imperative instructions. |
| Verification | Prove the externally meaningful outcome, including safety checks where relevant. |

Add the following sections only when they carry real operational information:

| Conditional element | Add when |
| ------------------- | -------- |
| Decision table | Multiple conditions select different actions. |
| Flow or architecture diagram | Ownership, sequence, or data flow is difficult to understand linearly. |
| Pitfalls | Observed failures have recognizable symptoms and actionable fixes. |
| Rollback | The procedure changes external or difficult-to-recover state. |
| Examples | An example materially clarifies input, output, or a decision boundary. |

Do not emit empty sections to satisfy a template. Do not repeat generic
technical knowledge. Keep the main file below 500 lines and use progressive
disclosure for details.

Validate each folder with the available skill validator before committing.
Then commit and push the accepted skill:

```bash
cd "$REPO" && git add "skills/<domain>/<skill-name>" && git commit -m "feat: add <skill-name> skill" && git push
```

The pre-commit hook enforces: README row exists **inside the matching
domain table**; both flat symlinks present and resolved. Skill URL (for
reference only — never mentioned in the blog body; the skill card carries
the linkage):
`https://github.com/Innei/SKILL/tree/main/skills/<domain>/<skill-name>`

### [4] Push accepted skills to mx-core

For every accepted skill, push its SKILL.md to mx-core's snippet store so the
reader-facing `<SkillCardList>` can render it and the public raw URL
(`${MXS_API_URL}/api/v3/s/sk/<name>`) exists.

```bash
SKILL_ID=$(bash "$S/push-skill.sh" "$REPO/skills/<domain>/<skill-name>/SKILL.md")
```

Run the command once per skill and retain every returned id. The script is
idempotent — `mxs snippet put` upserts by path.
Sibling asset files are pushed as `--type text` under `sk/<name>/` —
the backend rejects `--type skill` for any path not ending in `/SKILL.md`,
and without them relative links inside SKILL.md 404 on the public site.
Capture the returned id; step [6] threads it through `create-draft.sh`.

If a skill never reaches mx-core, the blog may still publish without that
install card. If no skill candidate passed the gate, skip this step entirely.

### [5] Write the blog

Load [`writing-style.md`](./references/writing-style.md),
[`node-usage.md`](./references/node-usage.md), and
[`visuals.md`](./references/visuals.md) before drafting. Do not restate
those rules here.

After choosing the reader contract and article spine, derive a working title
and stable slug. Finalize the title after the draft proves its central claim;
do not allow a sharper generalization to erase the defining technology or
system from the title.

Once the draft is complete:

```bash
SLOP_CACHE=$(bash "$S/load-no-ai-slop.sh") || {
  echo "no-ai-slop unavailable; continue with the internal hard-ban sweep"
}
# Read $SLOP_CACHE/SKILL.md. Detect candidates only; revise them by hand,
# rerun the sweep, and leave no unresolved finding. Never auto-rewrite.
```

Medium: default LiteXML (for Innei's blog).

```bash
LITEXML_CACHE=$(bash "$S/load-litexml.sh")
# Read $LITEXML_CACHE/SKILL.md and its references as needed.
```

Plain Markdown is fine when no haklex-specific tags are needed.

Do not convert the skill body into article sections. Reconstruct the blog from
the narrative evidence: establish the problem, expose the consequential
decisions, support claims with concrete evidence, and state the resulting
view. A rejected skill candidate may still supply valuable narrative material.

### [6] Publish via `mxs`

Follow [`publish-flow.md`](./references/publish-flow.md) end to end —
including the post-`--file` metadata re-attach and the post-publish metadata
verification. Pass zero or more `--skill-id` arguments according to the
accepted and successfully pushed skills. Paste the final URL back into the
originating session.

## Failure boundaries

Only mistakes that happen **before** the reference files are loaded.
Publish, voice, and node rules live in those files.

| Mistake | Fix |
| ------- | --- |
| Forcing every blog to have exactly one skill | Apply the semantic gate; allow zero, one, or several skills. |
| Deriving the skill scope from the blog title | Define a future trigger, action, boundary, and observable outcome. |
| Creating a skill because the session contains long code | Require repeatability and a non-obvious knowledge delta first. |
| Combining independent triggers in one skill | Split by trigger family, target, and completion criterion. |
| Copying the blog chronology into SKILL.md | Preserve only the executable method and decision boundaries. |
| Adding empty workflow, pitfalls, or diagram sections | Include conditional sections only when they improve execution. |
| Repeating trigger rules in a body-level "When to use" section | Put all triggering information in the frontmatter description. |
| Blog before an accepted skill | Finish and push every accepted skill before drafting the blog. |
| SKILL.md contains large deterministic procedures inline | Move repeated or fragile operations to `scripts/`; move detailed supporting material to `references/`. |
| Mentioning the skill in the blog body | Zero in-text mention. `meta.skillIds` renders the skill card. |
| `--no-verify` to bypass the pre-commit hook | Fix the root cause. The hook now requires the README row inside the matching domain table. |
| Hardcoding the SKILL repo path in shell | `bash "$S/resolve-skill-repo.sh"`. |
| Locating `$S` via `~/.claude/skills/...` only | Use the search loop above. |
| Stale local `litexml-authoring` / `no-ai-slop` clone | `load-litexml.sh` / `load-no-ai-slop.sh` refresh via degit. If no-ai-slop cannot load, skip and say so. |
| Skill written in Chinese | Skill in English. Blog in Innei's chosen language (default Chinese). |
| Skipping `push-skill.sh` and embedding only the GitHub URL | The install card reads `meta.skillIds`. Without `--skill-id`, it never renders. |
| Form / narrator / voice / slop mistakes | `writing-style.md`. |
| Title states a lesson but drops the defining technology | Restore the identity anchor, then qualify it with the earned claim. |
| Node sprinkling, invented `<dynamic>` URLs | `node-usage.md`. |
| Draft/meta/`<state>` / category / publish mistakes | `publish-flow.md`. |

## Verification

- [ ] `$S` resolved via the search loop; `bash "$S/resolve-skill-repo.sh"` points at a real directory before any write.
- [ ] Session evidence was classified among blog, reusable skill, and project documentation.
- [ ] Every skill has a capability thesis and passes all seven semantic gates.
- [ ] Every skill has one trigger family, one operational target, and one primary observable outcome.
- [ ] Frontmatter contains only `name` and `description`; the description carries all trigger conditions.
- [ ] The body contains the capability boundary, operational core, and verification without empty conditional sections.
- [ ] Scripts, references, and assets exist only when they improve deterministic reuse or progressive disclosure.
- [ ] Every accepted skill passed validation and the repository pre-commit hook; `git push` succeeded.
- [ ] Every successfully published skill returned a snowflake id and its `${MXS_API_URL}/api/v3/s/sk/<name>` URL resolves.
- [ ] Blog body has **zero** mention of the skill — the skill card carries the linkage.
- [ ] Voice, node, and visual checks in `writing-style.md` / `node-usage.md` / `visuals.md` passed.
- [ ] Final title preserves the technical identity anchor and makes no claim broader than the evidence; slug uses stable searchable terms.
- [ ] `no-ai-slop` detect sweep rerun after manual edits with no unresolved finding; if the loader failed, the internal hard-ban sweep still passed and the failure was reported.
- [ ] `meta.skillIds` contains exactly the successfully pushed skills; it is absent or empty when no skill passed the gate.
- [ ] Publish checklist in `publish-flow.md` passed; final post URL pasted back into the originating session.

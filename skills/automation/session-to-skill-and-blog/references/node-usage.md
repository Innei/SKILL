# Node usage doctrine — when an article earns a node

The haklex editor ships dozens of node types. This is a menu, not a quota.
The doctrine below decides *whether* a piece of content earns a node at all;
the litexml-authoring skill (loaded via `load-litexml.sh`) covers *how* to
write each tag once the decision is made.

## First principle: content earns nodes; nodes never decorate

**The deletion test.** For any candidate non-prose node, rewrite it mentally
as a plain paragraph. If no information is lost, the node was decoration —
don't use it. If something is lost (exactness, structure, the ability to
interact), name that loss in one clause; that clause is the node's
justification.

Prose is the default medium. Headings, paragraphs, lists, links, and inline
code cover the large majority of an engineering post. A post with zero
extension nodes can be excellent; a post with one node per paragraph is
almost certainly worse than its plain-prose version.

## The escalation ladder

Escalate only when the current level demonstrably fails. Never skip levels
"for richness".

```text
1 prose                 paragraphs, headings, lists, links, inline code
2 verbatim artifacts    codeblock / code-snippet — exactness required
3 structured facts      table / grid — shape carries the meaning
4 semantic signal       alert / banner — reader must not miss this
5 diagram & media       excalidraw / mermaid / img / gallery / video / embed
6 containers            details / nested-doc — flow control for evidence
7 interactive           poll / chat / dynamic — the reader's action carries
                        the lesson (see "When interaction teaches")
```

## Scenario → node map (engineering-session posts)

| Scenario in the session | Right node | Tempting but wrong |
| --- | --- | --- |
| Exact command, error output, diff hunk, version string | `<codeblock>` — always verbatim (Willison rule: never paraphrase output in prose) | Prose paraphrase; screenshot of text |
| A change spanning files that must be read together | `<code-snippet>` (one `<file>` each) | Several disconnected codeblocks |
| "I was wrong about X" correction; a hazard that costs the reader real damage | `<alert type="warning|caution">` | Alert as a highlighter for any point you like |
| Genuinely useful aside that most readers can skip | `<alert type="tip|note">`, sparingly | Tip-alert every few paragraphs |
| Page-wide precondition, deprecation, or status notice | `<banner>` (max 1 per post, at top) | Banner mid-article as a section divider |
| Comparing enumerable facts, ≥ 2 rows × 2 cols of short cells | `<table>` | Table with one column, or prose stuffed into cells |
| Two short alternatives viewed side-by-side | `<grid cols="2">` | Grid for content that reads sequentially |
| Architecture, pipeline, decision tree, timeline | `<excalidraw>` (see the visuals table in SKILL.md) | ASCII art in a codeblock |
| Strict sequence diagram; dense auto-routed flowchart | `<mermaid>` | Excalidraw with 30 hand-placed arrows |
| Full log / full config that supports the argument but would break the arc | `<details>` (collapsed evidence) | Hiding the main narrative inside details |
| Reproducing a real conversation (agent transcript, support thread) | `<chat>` | Chat to dramatize content that was never a dialogue |
| A question whose aggregated answers you will actually read and use | `<poll>` | Poll as engagement garnish |
| The lesson lives in a parameter space, a steppable process, or a perceptible difference (see "When interaction teaches") | `<dynamic>` (catalog rule below) | Dynamic for anything a static figure shows equally well |
| Citation, source link, tangential footnote | `<footnote>` + `<footnote-section>` | Inline parenthetical pile-ups |
| ≥ 3 related images forming one visual point | `<gallery>` | Gallery of 1–2 images (use `<img>`) |
| A standalone reference URL worth a visual card | `<link-card>` | Card for every inline citation (use `<a>`) |

## When interaction teaches — the positive case for interactive nodes

Interaction is not garnish, but it is also not rare by nature — technical
writing has a whole tradition of *explorable explanations* (Bret Victor,
distill.pub) where a widget teaches what prose cannot. The litmus test:

> **The reader's action must change what they see, and that change must
> carry the lesson.** If 2–3 static figures could enumerate every
> interesting state, use figures. If the interesting states form a space
> or a process the reader should *traverse themselves*, interaction earns
> its place.

Scenarios where a `<dynamic>` widget (or `<poll>`/`<chat>`) genuinely
teaches in a technical post:

| Scenario | Example | Why static fails |
| --- | --- | --- |
| Parameter exploration | Easing-curve playground; hash-distribution visualizer; rate-limiter window slider | The lesson IS the shape of the parameter space; figures show points, not the space |
| Algorithm step-through | Diff algorithm states; consensus rounds; GC phases, advanced step by step | Reader needs to run the state machine at their own pace to internalize transitions |
| Perceptible difference | Debounce vs throttle side-by-side; CLS with/without height floor; font hinting toggle | The difference is felt, not described — perception beats prose |
| Self-check after a dense section | A 3-option quiz on the one distinction the section hinged on | Retrieval practice; also signals to the reader what mattered |
| The post's subject demonstrating itself | A post about the dynamic node embedding a dynamic node | Dogfooding is the strongest possible evidence |
| Reader-supplied numbers | Memory-estimate calculator; pricing/quota converter | Each reader's input differs; a table can't cover them |

Discipline still applies: one widget that nails the core lesson beats three
gimmicks; every widget must come from the catalog (below); and a widget
that merely *displays* without meaningful input is a figure wearing a
costume — use `<img>`/`<excalidraw>` instead. When the catalog lacks the
right widget for a scenario above, say so to Innei — that is the signal to
commission a new cataloged component, not to force a static workaround
silently.

## Interactive embeds (`<dynamic>`) — catalog-gated

A post can embed an interactive ESM widget (quiz, parameter explorer,
step-through demo) via the `<dynamic>` tag (haklex ≥ 0.25.1). The URL
executes code in readers' browsers, so only components listed in the blog's
catalog may be referenced. Check first:

```bash
curl -fsS "${MXS_API_URL}/s/dynamic-widgets-catalog?_t=$(date +%s)"
```

- Catalog resolves → pick a matching entry, use its exact `url` and
  recommended `initial-height`, validate props against its `propsSchema`.
  Full tag rules: litexml-authoring reference `nodes-extensions.md` →
  "Embedded interactive components".
- 404 / empty → no widgets deployed. Do **not** emit `<dynamic>`; fall back
  to `<poll>` (votes), `<excalidraw>` (diagrams), or `<video>` (demos), and
  mention the gap to Innei.
- Never invent, guess, or adapt a component URL.

## Quantity discipline

- **Alerts**: at most ~1 per major section. More than 3 in a post means the
  structure is failing — restructure instead of shouting.
- **Banner**: 0 or 1.
- **Interactive nodes** (`poll` / `chat` / `dynamic`): zero is a fine
  number; one that nails the core lesson is excellent; several per post
  almost always means gimmickry. Enter only through a scenario in "When
  interaction teaches" — never as engagement garnish.
- **Diagram floor** (≥ 3 Excalidraw for substantial `site-owner` posts) is a
  floor on *thinking*, not a license to pad: each diagram must answer a
  question the prose struggled to answer.
- Node variety is **not** a quality metric. The metric is information
  density. A reviewer should never be able to guess "the author wanted to
  show off the editor" from the node mix.

## Anti-patterns

| Smell | Why it is wrong | Fix |
| --- | --- | --- |
| Alert wrapping an ordinary opinion | Devalues real warnings; readers learn to skip alerts | Plain prose; use an Antirez 断语 for emphasis |
| Main argument inside `<details>` | Reader must click to follow the story | Inline it; details holds evidence, not narrative |
| Table as layout (single column, long prose cells) | Tables encode comparisons, not paragraphs | List or prose |
| `<nested-doc>` as a fancy section | It signals a separable sub-document, which a section is not | `<h2>`/`<h3>` |
| Quiz/poll bolted onto static content "for engagement" | Interaction without consequence is friction | Cut it |
| Codeblock containing prose or pseudo-output | Verbatim container for non-verbatim content erodes trust | Prose, or get the real output |
| One node type per section to "cover the ecosystem" | Quota thinking; the post is not a demo page | Apply the deletion test per node |

## Pre-publish node audit

Walk every non-prose node in the draft and write (mentally) the one-clause
justification from the deletion test. Three outcomes:

1. Clause names a real loss (exactness / structure / interaction) → keep.
2. Clause is "it looks better" / "variety" → delete, demote to prose.
3. Can't produce a clause at all → delete without hesitation.

Then check the budgets: alerts ≤ 3, banner ≤ 1, interactive usually 0,
diagrams each answering a named question.

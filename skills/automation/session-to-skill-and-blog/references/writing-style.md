# Writing style — persona, voice, punctuation, structure

## Voice: pick a persona

Decide by what the blog is actually about: distilled *patterns*, a
*process*, or an owned *thing*.

| Persona                   | Use when                                                                                                            | "I" refers to |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------- | ------------- |
| `pattern` first-person    | The blog distills one or more reusable engineering patterns / boundary judgments out of a concrete experience       | the agent     |
| `agent` first-person      | The blog narrates a session/dogfood run — symptom → investigation → fix → why (e.g. the nextjs → react-router post) | the agent     |
| `site-owner` first-person | The blog is about a tool, workflow, format, or system that Innei designed and owns                                  | Innei         |

Selection rule (default → fall-through):

1. **Default `pattern`.** If at least one boundary judgment, anti-pattern,
   or design rule can be lifted out of the session and stated so that another
   engineer could apply it to a different codebase, write `pattern`. The
   concrete session retreats into evidence (real errors, commits, numbers);
   the article's spine is the reusable lesson.
2. **`agent` only when the process *is* the point.** Use `agent` when the
   value to the reader is the investigation rhythm itself (debugging a
   library upgrade, dogfooding a tool, narrating a unique chase that has no
   transferable principle). If you catch yourself writing a chronological
   "Innei said X, I said Y" transcript inside a `pattern` post, you picked
   the wrong persona — or you have not yet extracted the pattern.
3. **`site-owner` when ownership is Innei's.** Use `site-owner` when the
   subject is a thing Innei built (CLI, format, workflow, infra). Writing in
   agent voice when ownership is Innei's misattributes the design labor.

When the post needs both ownership and a dogfood run that exposed the
issue, stay in `site-owner` voice and refer to the agent in third person —
"an agent run surfaced X, so I fixed Y". Do not switch personas mid-post.

## `site-owner` style — Willison + Abramov + Antirez

Combine three reference styles. Each contributes a distinct property;
together they keep the prose honest, structured, and assertive.

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

## `pattern` style — distilled judgments, evidence underneath

`pattern` inherits Willison transparency, Abramov arc and Antirez 断语
verbatim from `site-owner`. What differs is the structural commitment: the
session is evidence, not spine.

The reader's takeaway must be transferable to a *different* codebase. If
the post collapses to "this is what happened to me on Tuesday", it is the
wrong persona — switch to `agent`, or stay in `pattern` and extract harder.

### Section template

Each major section is one pattern / boundary / anti-pattern, written in
four tight blocks:

1. **Pattern** — name and state the rule in one paragraph. The reader knows
   what is being claimed before any example.
2. **Failure mode** — show what breaks when the pattern is violated. This
   is where verbatim artifacts earn their place: real error stack, the
   specific symptom, a minimal code shape that demonstrates the trap. This
   is where Willison transparency lives.
3. **Fix** — the actual reshape. Concrete code with `path="..."` on the
   `<codeblock>` when it comes from a real file; minimal abstract shape
   when it does not. Name the reshape so it can be referenced later
   (`register()` function, `appReady` gate, stable-window metric).
4. **Takeaway (可带走的判断)** — one or two sentences in the abstract,
   phrased as a question the reader can ask their own code. This is the
   row that goes into the reader's mental checklist.

### Closing template

Replace the session-style recap with one of two transferable forms:

- **Self-audit table.** A `<table>` whose columns are "Question to ask /
  Red flag / Section". One row per pattern in the post. The reader runs
  the table over their own project the moment they finish reading.
- **A short rule list.** Three to five Antirez 断语, each one a takeaway
  promoted to standalone status. No prose around them.

Either form is acceptable; both is overkill.

### What `pattern` deliberately removes

- Chronological "Innei said X, I said Y" exchanges. Quote at most a single
  short line of someone else's pushback when the quote *is* the pattern
  (e.g. "为什么要 await？" landing the "等待 ≠ 串行" judgment). One per
  section is already a lot.
- "Session recap" or "what I learned" sections. The takeaways are already
  distributed across each section's fourth block.
- First-person "I was wrong about X" anecdotes that do not generalize. Keep
  them only when the mistake encodes a teachable cognitive trap (`await`
  conflated with serial, lazy import conflated with ownership). One or two
  per article, not one per section.

### Evidence budget

Real commit hashes, error stacks, file paths, version numbers, and
benchmark numbers stay — they buy the article's transparency. The
difference is that they appear as inline citations *inside* a pattern's
failure mode or fix block, not as the article's narrative arc. If the
session evidence forms more than ~30% of the body, the patterns are too
thin or the persona is wrong.

## Punctuation

- **Em-dashes (——) sparingly.** The default punctuation is `。` `，` `：` `；`
  or parentheses. Reserve `——` for genuine asides, mid-sentence
  interruptions, or true em-dash thought-jumps. A row of em-dashes in close
  succession reads as lazy structure.
- Prefer two short sentences over one long sentence joined by an em-dash.
- Use `：` to introduce a list, example, or definition.
- Use `（）` for parenthetical asides that are tightly bound to the surrounding
  sentence.
- Quote tag names and code identifiers in `<code>...</code>`, not `「...」`.

## Structure

The skill URL appears twice in every persona: banner at top, CTA at bottom.
The body in between differs:

- **`pattern`** — opening (the recurring problem this distills + top URL
  banner) → one section per pattern, each running the four-block template
  above → closing (self-audit table or rule list + bottom URL CTA). The
  skill's own steps do not dictate the section order; the patterns do.
- **`agent`** — opening (task + sub-tasks + top URL banner) → one section
  per "act" mirroring the skill's steps → each act follows symptom →
  investigation → fix → why → closing (skill tree listing + bottom URL CTA).
- **`site-owner`** — opening (what was built + why + top URL banner) → one
  section per major design decision or component → each section explains
  intent before mechanism → closing (positioning + bottom URL CTA).

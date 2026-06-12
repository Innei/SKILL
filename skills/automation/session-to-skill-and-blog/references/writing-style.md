# Writing style — persona, voice, punctuation, structure

## Voice: pick one of two personas

Decide by what the blog is actually about: the *process* or the *thing*.

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

Opening (task + sub-tasks + top URL banner) → one section per "act"
mirroring the skill's steps → each act follows symptom → investigation →
fix → why → closing (skill tree listing + bottom URL CTA).

The skill URL appears twice: banner at top, CTA at bottom.

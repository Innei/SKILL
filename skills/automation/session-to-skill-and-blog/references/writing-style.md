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

### Section substance check (not a template)

There is no prescribed block order, no numbered "模式一/二/三" heading
formula, no fixed section shape. Form follows content, judged by one
criterion: does this shape help a *human reader* scan and absorb? Headings,
ordering, and rhythm may differ per post and per section.

What is checked instead, after writing, per major section:

- Does it carry at least one **transferable judgment** a reader could apply
  to a different codebase? The judgment must be woven into the prose (an
  opening 断语, a sentence that lands as the fix resolves) — never under a
  fixed label.
- Does its claim stand on **real failure evidence** (verbatim log, error,
  code shape) rather than assertion?
- Could a reader **reconstruct the fix** concretely, not just nod along?

A section can pass these checks in many shapes. Three consecutive sections
passing them in the *same* shape is a machine fingerprint — vary or merge.

### Endings

The post ends where the last point lands. No closing section of any kind:
no self-audit table, no rule recap, no "总结/回顾", no CTA paragraph. If
the final section's last sentence doesn't feel like an ending, the fix is
to rewrite that sentence, not to append a wrap-up.

### What `pattern` deliberately removes

- Chronological "Innei said X, I said Y" exchanges. Quote at most a single
  short line of someone else's pushback when the quote *is* the pattern
  (e.g. "为什么要 await？" landing the "等待 ≠ 串行" judgment). One per
  section is already a lot.
- "Session recap" or "what I learned" sections. The takeaways are already
  woven into each section's prose.
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

## Skill linkage: zero in-text mention

The attached skill is carried entirely by the skill card
(`meta.skillIds` → the article page renders an install card up front).
The body text never mentions it: no "操作手册见…" opener, no bottom CTA,
no banner pointing at it. The article is an article; the artifact is UI.

## Hard bans — the AI-tell list (all personas)

These are the strongest machine-writing fingerprints. Each is banned
outright; none is a budget to spend.

1. **Meta-narrative.** The body never discusses the post itself: no
   "本文将…", no "如前所述", no "见文末", no skill/manual pointers, no
   tour-guide transitions.
2. **Fixed-phrase labels.** "可带走的判断：", "小结：", "值得注意的是",
   "简单来说" and kin. If a sentence needs a label to be recognized as
   important, the sentence is not written well enough.
3. **Closing recap sections.** Self-audit tables, rule lists, "总结",
   final CTAs. The last point's landing is the ending (see Endings).
4. **Isomorphic sections.** Consecutive sections with block-for-block
   identical internal structure. Vary the shape or merge the sections.
5. **Decorative callouts.** `<alert>`/`<banner>` for nuance, intros, or
   pointers (budgets in node-usage.md: default zero for both).

## Extended sweep — `no-ai-slop`

The five hard bans are the ones this workflow keeps re-committing. For the
wider surface, run the finished draft through
[`no-ai-slop`](https://github.com/petergyang/no-ai-slop) in **detect mode**
("audit this draft, name each pattern, quote the line, don't rewrite")
before publishing. Detect, not edit: an auto-rewrite flattens Innei's
voice, which is exactly what the persona rules are protecting.

Its em-dash budget and its ban on summary-recap endings restate rules
already stated above. Everything else is additive. The patterns that
survive translation into Chinese technical prose:

| Pattern                  | Chinese shape to catch                                    | Fix                                     |
| ------------------------ | --------------------------------------------------------- | --------------------------------------- |
| Binary contrasts         | 「这不是 X，而是 Y」「问题不在 X，在 Y」                   | 直接说 Y                                |
| Faux-insight setups      | 「大多数人不知道的是」「很少有人提到」                     | 删掉铺垫，让判断自己站住                |
| Colon reveals            | 「真正让它跑起来的细节：一个独立的 agent 打分」            | 写成完整句子；冒号留给列表和引用        |
| Superficial `-ing`       | 「……，体现了 / 彰显了 / 反映出对 X 的重视」                | 换成具体后果                            |
| Importance puffery       | 「标志着一个重要节点」「起到了关键作用」                   | 陈述事实，让读者判断它重不重要          |
| Weasel attribution       | 「业界普遍认为」「有研究表明」                             | 指名来源，否则删掉这句                  |
| Synonym cycling          | 同一个东西轮着叫 agent / 助手 / 工具                       | 认准一个词，重复用                      |
| Negative listing         | 「不是 A。不是 B。是 C。」                                 | 只说 C                                  |
| Dramatic fragmentation   | 「就这样。就这么简单。」                                   | 完整句子                                |
| Fake-profound kicker     | 结尾拔高成比喻或金句                                       | 删掉，停在最后一个具体句子上            |
| Formatting slop          | 标题带 emoji、句中随手加粗、两句话就开一个小标题           | 格式跟着内容走                          |

The banned-word list is English (`delve`, `leverage`, `robust`,
`transformative`…); the Chinese equivalents are 「赋能」「抓手」「闭环」
「深度赋予」这类词。Same rule: cut them.

## Structure

The body differs by persona; within each, section shape is free (see
"Section substance check"):

- **`pattern`** — opening states the recurring problem this distills →
  one section per pattern → the last pattern's landing is the ending. The
  skill's own steps do not dictate the section order; the patterns do.
- **`agent`** — opening (task + sub-tasks) → one section per "act"
  mirroring the skill's steps → each act covers symptom → investigation →
  fix → why, in whatever shape the material demands.
- **`site-owner`** — opening (what was built + why) → one section per
  major design decision or component → each section explains intent
  before mechanism.

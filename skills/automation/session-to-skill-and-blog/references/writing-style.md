# Writing style — form, titles, sections, narrative, argument, voice

## Contents

- [Editorial standard](#editorial-standard-remove-ai-slop)
- [Reader and reading contract](#define-the-reader-and-the-reading-contract)
- [Article spine](#choose-the-article-spine)
- [Title and slug](#derive-the-title-and-slug-from-the-reading-contract)
- [Narrator](#choose-the-narrator)
- [Section design](#build-sections-from-changes-in-the-readers-question)
- [Narrative movement](#choose-a-narrative-movement)
- [Technical viewpoints](#state-and-defend-technical-viewpoints)
- [Visual planning](#plan-visual-explanations-with-the-prose)
- [Spine-specific rules](#pattern-spine--distilled-judgments-evidence-underneath)
- [Endings and punctuation](#endings)
- [Skill linkage and anti-slop sweep](#skill-linkage-zero-in-text-mention)
- [Research basis](#research-basis)

## Editorial standard: remove AI slop

Keep a sentence only when it contributes at least one of these: an observed
fact, evidence, causal reasoning, a constraint or trade-off, a decision, a
reproducible action, or a concrete consequence. Delete sentences whose only
job is to announce the topic, inflate importance, manufacture surprise,
smooth a transition, or repeat a conclusion.

Preserve the factual proposition while removing its rhetorical wrapper. Do
not replace a banned phrase with a synonym.

| Slop | Edited prose |
| ---- | ------------ |
| 本文将深入探讨这次迁移中一个值得注意的问题。 | 迁移到 React Router 后，HTML 可以缓存，loader 数据仍按请求生成。 |
| 真正关键的细节：草稿更新会覆盖 meta。 | `mxs draft update --file` 会覆盖 `meta`；最后一次文件更新后必须重新附加 `skillIds`。 |
| 这一改动显著提升了稳定性。 | 失败请求不再无限重试；第三次失败后，任务进入 dead-letter queue。 |
| 这个方案可能在某些情况下更合适。 | 需要跨重启恢复写入时，使用持久队列。进程内队列不满足这一条件。 |

Treat these examples as editing operations, not sentence templates.

### Chinese prose target

- Open a paragraph with an observation, constraint, action, or result. Do not
  announce the paragraph's topic.
- Let one paragraph complete one movement of thought. Vary its length when
  the material requires it; do not alternate mechanically between setup and
  conclusion.
- Prefer ordinary verbs over abstract nouns. Keep established technical terms
  stable instead of rotating synonyms.
- Use first person only for actions performed by the selected narrator.
- End a paragraph on its concrete consequence or scoped judgment. Do not add
  a second sentence merely to make the ending sound emphatic.

| Function | Chinese example |
| -------- | --------------- |
| Observation → evidence | 修改共享渲染器后，文档任务的哈希没有变化。dry-run 输出确认 Turbo 没有把该文件计入输入。 |
| Cause → consequence | 草稿文件更新会覆盖 `meta`，因此最后一次更新后必须重新附加 `skillIds`。 |
| Scoped judgment | 在 `mxs` 0.14.0 的 draft publish 路径中，这个字段会变成 `skill_ids`；其他版本需要重新验证。 |

Use the relationships demonstrated by these examples, not their sentence
shapes.

## Define the reader and the reading contract

Before outlining, write two private planning lines:

1. **Reader:** the narrowest plausible reader, including what they already
   know and the decision or task they face.
2. **Contract:** what the article will enable that reader to understand,
   decide, reproduce, or challenge.

Keep assumptions consistent. Do not explain a basic term in one section and
silently require advanced knowledge in the next. Introduce one load-bearing
concept at a time; defer secondary detail to a footnote, collapsed artifact,
or linked source when it would interrupt the reasoning.

Choose the form that matches the size and certainty of the material. Do not
inflate a narrow finding into an essay.

| Form | Reader contract | Appropriate shape |
| ---- | --------------- | ----------------- |
| `note` / TIL | Learn one bounded fact, command, or failure mode | State the finding, show the smallest sufficient example, name its scope, stop |
| `project record` | Understand what changed in a real system and why | Consequence or constraint → evidence → decisions → verified result |
| `guide` / mental model | Build enough understanding to predict or perform | Prerequisite floor → concrete example → trace → principle → harder case |
| `argument` / design analysis | Evaluate a technical position | Criteria → competing models → counterexample or evidence → trade-off → scoped claim |

Choose by the outcome the reader needs, not by the origin of the material. A
real project session can support a note, guide, or argument; it becomes a
`project record` only when understanding that system's change and decisions is
the reader's objective.

A long guide may state its assumed audience, scope, and route near the top
when those facts change how the reader should use it. A note normally needs
none of these. This is a reader contract, not ceremonial narration about the
article.

## Choose the article spine

Choose the article's structural spine independently from its form and
narrator identity. The form defines the promise; the spine determines what
holds the body together.

| Spine | Use when | Organize around |
| ----- | -------- | --------------- |
| `pattern` | The session yields reusable boundary judgments or design rules | One transferable judgment per core section; session details serve as evidence |
| `process` | The investigation sequence itself teaches the reader something | Decisions that changed the next action: symptom → evidence → fix → why |
| `system` | The subject is a tool, workflow, format, or system Innei owns | Design intent, major decisions, components, and operational consequences |

Selection rule:

1. **Default `pattern`.** If at least one boundary judgment, anti-pattern,
   or design rule can be lifted out of the session and stated so that another
   engineer could apply it to a different codebase, choose `pattern`. The
   concrete session retreats into evidence (real errors, commits, numbers);
   the article's spine is the reusable lesson.
2. **Choose `process` only when the process is the point.** Use it when the
   value to the reader is the investigation rhythm itself (debugging a
   library upgrade, dogfooding a tool, narrating a unique chase that has no
   transferable principle). If you catch yourself writing a chronological
   transcript inside a `pattern` post, choose `process` or extract the pattern.
3. **Choose `system` when design ownership is the point.** Use it when the
   reader needs to understand why an Innei-owned system has its present shape.

## Derive the title and slug from the reading contract

Use the title to select the right reader and compress the article's actual
promise. Do not treat it as packaging added during publication.

Create a working title after choosing the reader contract and spine. Finalize
it only after the draft establishes which claim the evidence can support:

```text
reader contract → form and spine → working title → draft → final title audit
```

Build the title from three semantic roles, without forcing a fixed sentence
shape:

| Role | Requirement |
| ---- | ----------- |
| Identity anchor | Preserve the product, framework, protocol, library, or system that makes this article distinct. |
| Action or scenario | Name the migration, failure, design decision, or operating condition under examination. |
| Earned claim | State the consequence, boundary, or mechanism that the article actually proves. |

The identity anchor has priority. Do not remove `Sparkle` from an article
about extracting an Electron Sparkle updater merely to make its general
boundary lesson sound sharper. Keep one or two defining technical names;
secondary implementation details belong in the body.

Generate candidates around genuinely different centers rather than synonym
rotation: a concrete result, a mechanism or constraint, or an evaluable
judgment. Select the center that matches the article's spine. A process post
may foreground the investigation only when the investigation itself is the
reader contract.

Audit the final title:

| Check | Question |
| ----- | -------- |
| Identity | Would a target reader recognize the defining technology or system? |
| Contract | Does the title reveal what the reader will understand, decide, or reproduce? |
| Evidence | Does the body support every consequence and number in the title? |
| Scope | Is the claim no broader than the tested version, system, or environment? |
| Distinction | Could the same title fit a hundred unrelated technical posts? |
| Retrieval | Does it retain the terms a future reader would search for? |
| Cadence | Does it avoid repeating the title shape used by adjacent posts? |

Prefer a plain specific title over generic wrappers such as `实践`, `实录`,
`踩坑记录`, `一些思考`, `最佳实践`, or `全链路部署`. Avoid unearned
clickbait such as `一文搞懂`, `终极指南`, `你可能不知道`, and claims that a
subject is more difficult, important, or surprising than expected. A colon is
useful only when it separates a stable identity or scenario from an earned
claim; do not make it a house template.

Derive the slug from stable identity and subject terms, not from the title's
rhetorical surface. Use lowercase ASCII kebab-case. Preserve defining names
such as `sparkle`, `react-router`, or `cloudflare`; omit dates, transient
adjectives, and authoring provenance such as `ai-agent-perspective` or
`agent-log`. A later title refinement should not require a slug change unless
the old slug misidentifies the article.

When changing an existing slug, follow `publish-flow.md`: address the mutation
by immutable post id, check that the new slug is unoccupied, and verify both
the new lookup and the old public-path redirect.

## Choose the narrator

If the session intake already recorded `agent`, `site-owner`, or `neutral`,
use that narrator. Otherwise choose one grammatical narrator after choosing
the spine. Do not change what "I" refers to inside the post.

| Narrator | Use when | Attribution rule |
| -------- | -------- | ---------------- |
| `agent` first-person | The agent performed the investigation and its decisions are central | "I" means the agent; name Innei's requests and design decisions explicitly |
| `site-owner` first-person | Innei owns the system or made the design decisions | "I" means Innei; describe agent activity as "an agent run" or in third person |
| `neutral` | A pattern matters more than personal chronology | Avoid "I"; name the actor only when ownership affects the claim |

The spine and narrator are independent. A `pattern` post may use any of the
three narrators. A `process` post normally uses agent first-person, while a
`system` post normally uses site-owner first-person. Use neutral narration
when either first-person choice would obscure ownership.

## Build sections from changes in the reader's question

Outline the article as a question ladder before writing prose. A new section
is justified when the reader's active question, evidence type, or level of
abstraction changes. Page length alone does not justify a heading.

| Cognitive move | Section earns its place when it… |
| -------------- | --------------------------------- |
| Establish the problem | Shows an observable mismatch and its consequence for the named reader |
| Build the model | Introduces a mechanism required to predict later behavior |
| Test the model | Uses a trace, example, measurement, or counterexample to make the model falsifiable |
| Compare alternatives | Evaluates live options against the same constraints |
| Apply the result | Converts the explanation into a decision, fix, or reproducible procedure |
| Bound the claim | Names a limitation, version boundary, or unresolved condition that changes use |

Use as few sections as the argument permits and as many as selective reading
requires. Narrative essays can carry several movements under one heading;
long guides need more signposts. Omit a conventional section such as
“Background” or “Conclusion” when it has no independent work to do.

Headings should name the question or claim specific to that section. Avoid
generic labels such as “Details”, “Implementation”, and “Other
considerations” unless the material truly functions as reference. A table of
contents or route map is appropriate only when a long article supports
non-linear reading.

Audit each section with the questions that apply:

- Is the reader's current observation or belief clear enough to interpret the
  new material?
- Is every new concept or artifact necessary to resolve this section's
  question?
- Does the section earn a scoped answer, or is it only accumulating detail?
- If another section follows, does a real remaining question require it?

A section need not answer all four audit questions in visible prose. They are
diagnostic prompts, not a sequence or paragraph template.

## Choose a narrative movement

Do not default to either chronology or dramatic storytelling. Select the
order that produces the shortest sound route from the reader's current model
to the target model.

- **Consequence first:** open on a concrete failure, changed behavior, or
  design constraint; backfill only the context needed to interpret it.
- **Decision chronology:** retain an event only when it changed the working
  hypothesis or next action. This is the default for a `process` spine.
- **Model ladder:** reuse one concrete example, ask what should happen, trace
  what does happen, state the governing principle, then vary one condition.
  This is the default for a guide.
- **Competing models:** make each alternative credible under its own
  constraints, expose where each fails, then state the synthesis or choice.
  This is often the strongest movement for an argument.

Use tension only when it exists in the evidence: a failed assumption,
incompatible requirement, surprising measurement, or meaningful trade-off.
Never add a false mystery, delayed reveal, or hero narrative to make routine
work appear consequential. A small note can begin with the fact itself.

## State and defend technical viewpoints

Treat a viewpoint as an evaluable claim, not a tone of confidence.

1. State the properties, constraints, or reader consequences that define a
   good outcome before recommending an option.
2. Present the strongest live alternative under the same criteria. Do not
   weaken it for rhetorical convenience.
3. Show the decisive evidence: a failure trace, measurement, source, concrete
   example, or operational consequence.
4. Separate **fact**, **inference**, **preference**, and **unknown**. Mark
   uncertainty where it exists and remove the hedge when evidence resolves it.
5. Scope the conclusion by version, workload, ownership boundary, or failure
   model. Do not universalize a local result.

Ask “what changes for the reader if this claim is true?” until the answer is
a concrete decision or consequence. If the answer remains “this is
interesting”, the viewpoint is not yet developed.

## Plan visual explanations with the prose

During outlining, name any relationship the reader would otherwise need to
simulate mentally: topology, execution order, state transition, causal
comparison, or quantitative behavior. Record the precise reader question
beside it. Then follow [`visuals.md`](./visuals.md) to select and construct the
medium. Do not reserve a diagram slot and search for content to fill it.

## Shared voice — transparent, structured, decisive

- **Show the work.** Quote real error output, commit
  hashes, exact version numbers, the actual file path you edited. No mystery,
  no hand-waving. Link to source liberally. When something failed, say so —
  including which approach you tried first and why it didn't work.
- **Use an earned arc.** When the material contains a real failed assumption,
  constraint, or competing decision, present its setup → tension → payoff.
  Otherwise state the observation and consequence directly. Never manufacture
  conflict to satisfy a section shape.
- **Conclude decisively.** Use short declarative conclusions when warranted. No
  empty hedging or ceremonial emphasis. Retain every condition, version
  boundary, and uncertainty required for correctness. Use a stand-alone
  conclusion only after the preceding evidence has earned it.

## `pattern` spine — distilled judgments, evidence underneath

The session is evidence, not spine. Make the takeaway transferable to a
different codebase. If the post collapses to "this is what happened on
Tuesday", choose `process` or extract a stronger pattern.

### Section substance check

There is no prescribed block order, no numbered "Pattern 1/2/3" heading
formula, no fixed section shape. Form follows content, judged by one
criterion: does this shape help a *human reader* scan and absorb? Headings,
ordering, and rhythm may differ per post and per section.

What is checked instead, after writing, per pattern-bearing section:

- Does it carry at least one **transferable judgment** a reader could apply
  to a different codebase? The judgment must be woven into the prose (an
  opening aphorism, a sentence that lands as the fix resolves) — never under a
  fixed label.
- Does its claim stand on **real failure evidence** (verbatim log, error,
  code shape) rather than assertion?
- Could a reader **reconstruct the fix** concretely, not just nod along?

A supporting section may establish context, constraints, trade-offs, or
verification without carrying a separate pattern. Three consecutive sections
using the *same* internal shape are a machine fingerprint — vary or merge.

### What `pattern` deliberately removes

- Chronological "Innei said X, I said Y" exchanges. Quote at most a single
  short line of someone else's pushback when the quote *is* the pattern
  (e.g. "why await?" landing the "waiting is not serial" judgment). One per
  section is already a lot.
- "Session recap" or "what I learned" sections. The takeaways are already
  woven into each section's prose.
- First-person "I was wrong about X" anecdotes that do not generalize. Keep
  them only when the mistake encodes a teachable cognitive trap (`await`
  conflated with serial, lazy import conflated with ownership). One or two
  per article, not one per section.

### Evidence selection

Real commit hashes, error stacks, file paths, version numbers, and
benchmark numbers stay when they support a claim or let the reader reconstruct
the fix. Cut chronology that only records activity. If session details obscure
the transferable judgment, reduce them or choose the `process` spine. If the
judgment cannot be verified from the remaining evidence, restore the required
artifact or narrow the claim.

## `process` spine — decisions, not a transcript

Keep chronology only when one observation changed the next action. Each act
should expose the evidence available at the time, the resulting decision, the
fix, and why the earlier assumption failed. Remove status updates, conversational
turn-taking, and failed attempts that did not alter the method.

In agent first-person, begin sentences with concrete actions or observations:
`我对比了两次任务哈希` carries an action; `我很兴奋地发现` carries only
reaction. Preserve uncertainty that existed during the investigation, then
state the final boundary with its evidence.

## `system` spine — intent before mechanism

Open with the system's concrete purpose and constraint. Organize the body by
major design decisions or components. Explain intent before mechanism, then
show the operational consequence. Attribute Innei's design work to Innei even
when an agent run supplied the failure evidence.

## Endings

End when the final technical point lands. Do not append a generic recap, rule
list, CTA, metaphor, or universal lesson. A short closing section is allowed
only when it adds an unresolved trade-off, limitation, or operational next
condition that the body has not already stated. Delete it if the article loses
no information without it.

A long guide may end with a compact retrieval aid—a decision table, mental
model, or verification checklist—when it compresses the article into a form
the reader can use later. It must add retrieval value rather than repeat the
section conclusions in new words.

## Punctuation

Default blog language is Chinese; use Chinese punctuation there. English
drafts use `.` `,` `:` `;` and parentheses instead.

- **Em-dashes sparingly** (`——` in Chinese, `—` in English). The default is
  sentence punctuation or parentheses. Reserve the em-dash for genuine
  asides, mid-sentence interruptions, or true thought-jumps. A row of
  em-dashes in close succession reads as lazy structure.
- Prefer two short sentences over one long sentence joined by an em-dash.
- Use a colon to introduce a list, example, or definition.
- Use parentheses for asides that are tightly bound to the surrounding
  sentence.
- Quote tag names and code identifiers in `<code>...</code>`, not `「」`,
  `『』`, or `《》`.

## Skill linkage: zero in-text mention

The attached skill is carried entirely by the skill card
(`meta.skillIds` → the article page renders an install card up front).
The body text never mentions it: no "see the playbook at…" opener, no
bottom CTA, no banner pointing at it. The article is an article; the
artifact is UI.

## Hard bans — AI slop

Use the editorial deletion test above. Treat this list as a search index over
authorial prose; preserve verbatim source material when it is evidence.

1. **Ceremonial meta-narrative.** Delete "this article will…", "as mentioned
   above", "see the end", skill/manual pointers, and tour-guide transitions.
   Delete `本文将…`, `如前所述`, and `见文末` for the same reason. Retain a
   concise audience, prerequisite, scope, or route statement only when it
   changes how a reader should approach a long guide.
2. **Throat-clearing and labels.** Delete "takeaway:", "in short:", "it is
   worth noting", "simply put", `可带走的判断：`, `小结：`, `值得注意的是`,
   and `简单来说`. State the proposition directly.
3. **Manufactured insight or importance.** Delete claims that a fact is
   surprising, overlooked, important, robust, transformative, or critical
   unless the article supplies a measurement or named consequence.
4. **Empty contrast and negative staging.** Replace "not X but Y" and
   "not A, not B, only C" with the verified cause or decision. Retain a
   contrast only when two live alternatives must be distinguished; name the
   evidence that excludes one of them.
5. **Vague authority and abstract consequences.** Name the source behind
   "research shows" or "the industry agrees". Replace "demonstrates a focus
   on" and "marks a milestone" with the observable result.
6. **Mechanical cadence.** Remove synonym cycling, repeated paragraph
   lengths, block-for-block section templates, dramatic fragments, and
   consecutive one-line conclusions.
7. **Closing recap or borrowed profundity.** Do not add a generic summary,
   CTA, metaphor, proverb, or universal life lesson after the final technical
   point. A long guide's retrieval aid must compress the material into a
   usable model or checklist rather than restate it.
8. **Decorative formatting.** Do not use emoji headings, random bold text,
   headings every two sentences, or `<alert>`/`<banner>` nodes that fail the
   deletion test in `node-usage.md`.

## External sweep — `no-ai-slop`

Apply the internal hard bans even when the external detector is unavailable.
For the wider surface, load `no-ai-slop` via `scripts/load-no-ai-slop.sh`
and use it only to identify candidates. Never give it authority to rewrite
the draft.

For every finding, apply the editorial standard at the top of this file.
Delete a line with no factual proposition. Rewrite a proposition hidden by a
rhetorical wrapper. Retain a flagged line only when removal would erase a
necessary technical distinction, and record that reason outside the article.
Run the detector again after manual edits; leave no unresolved finding.

If the loader fails and no cache exists, report the failure and complete the
internal sweep. Do not skip the anti-slop pass.

Search Chinese drafts explicitly for `本文将`, `值得注意`, `简单来说`,
`大多数人不知道`, `这不是`, `问题不在`, `真正关键的是`, `体现了`,
`彰显了`, `标志着`, `起到了关键作用`, `业界普遍认为`, `有研究表明`,
`赋能`, `抓手`, and `闭环`. Delete the wrapper or replace it with evidence,
a named source, a scoped decision, or a concrete consequence.

## Research basis

These rules derive from recurring techniques in primary essays by technical
authors; they do not authorize imitation of an author's catchphrases,
persona, cadence, or signature structure. Consult
[`editorial-models.md`](./editorial-models.md) only when revising this policy,
not during routine blog drafting.

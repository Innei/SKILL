# Editorial models — primary-source research

Use this reference to revise `writing-style.md` and `visuals.md`. Do not load
it during routine blog drafting. The objective is to extract general editorial
methods, not to imitate an author's persona, signature phrases, cadence, or
visual identity.

## Comparative findings

| Author | Primary material | Transferable method |
| ------ | ---------------- | ------------------- |
| Simon Willison | [What to blog about](https://simonwillison.net/2022/Nov/6/what-to-blog-about/) | Match the promise to the material: a TIL can record one bounded discovery, while a project write-up derives authority from actual construction and preserved evidence. |
| Julia Evans | [Patterns in confusing explanations](https://jvns.ca/blog/confusing-explanations/), [How I write useful programming comics](https://jvns.ca/blog/2020/12/05/how-i-write-useful-programming-comics/), [Some blogging myths](https://jvns.ca/blog/2023/06/05/some-blogging-myths/) | Choose a specific reader, keep assumptions consistent, introduce fewer new concepts at once, use examples, mark genuine uncertainty, and make every illustration teach rather than decorate. |
| Martin Fowler | [Writing Software Patterns](https://martinfowler.com/articles/writingPatterns.html), [Using Footnotes](https://martinfowler.com/articles/2024-footnote-rendering.html), [The Almighty Thud](https://martinfowler.com/distributedComputing/thud.html) | Let form serve the idea; use only headings that perform work; keep the narrative thread clear by moving secondary detail aside; select the architectural elements the reader needs instead of documenting everything. |
| Maggie Appleton | [On Opening Essays, Conference Talks, and Jam Jars](https://maggieappleton.com/openings), [Tools for Thought as Cultural Practices](https://maggieappleton.com/tools-for-thought) | Begin narrative nonfiction at the consequential tension rather than the chronological beginning, derive tension from facts, identify the reader consequence, and place diagrams adjacent to the claims they explain. |
| Dan Abramov | [A Complete Guide to useEffect](https://overreacted.io/a-complete-guide-to-useeffect/), [How Imports Work in RSC](https://overreacted.io/how-imports-work-in-rsc/), [The Two Reacts](https://overreacted.io/the-two-reacts/), [Preparing for a Tech Talk: Content](https://overreacted.io/preparing-for-tech-talk-part-3-content/) | Build a mental model through a sequence of concrete examples and changed assumptions; use an outline to expose prerequisite inversions; test the hardest explanatory section early; make competing models credible before synthesis. |
| Salvatore Sanfilippo (antirez) | [A proposal for more reliable locks using Redis](https://antirez.com/news/77), [An update about Redis developments in 2014](https://antirez.com/news/83) | State safety or evaluation properties before an algorithm, present a naive baseline, expose it with a concrete failure trace, and interpret measurements with their causal and operational limits. |
| Mitchell Hashimoto | [Introducing Ghostty and Some Useful Zig Patterns](https://mitchellh.com/writing/ghostty-and-useful-zig-patterns) | Introduce the subsystem inventory, show the runtime architecture, walk the diagram in execution order, connect mechanisms to real source, and state both benefit and downside. |
| Bret Victor | [Explorable Explanations](https://worrydream.com/ExplorableExplanations/), [Media for Thinking the Unthinkable](https://worrydream.com/MediaForThinkingTheUnthinkable/) | Intertwine words and representations; show state and relationships that readers would otherwise simulate; expose assumptions and consequences; guide exploration instead of presenting an unguided interactive sandbox. |

## Derived policy by editorial dimension

| Dimension | Policy |
| --------- | ------ |
| Writing form | Choose an explicit reader contract. Do not expand a note into longform or compress an unresolved mental model into a slogan. |
| Sections | Create a section when the reader's question, evidence type, or abstraction level changes. Forms are optional; weak placeholder sections should be omitted. |
| Narrative | Prefer the shortest sound path from current understanding to target understanding. Use chronology only for decisions, and use tension only when the evidence contains it. |
| Viewpoint | Define criteria, show the strongest alternative, expose decisive evidence, distinguish fact from inference and preference, and scope the conclusion. |
| Visual explanation | Name the question first; select the medium by the relationship; introduce, label, and interpret every visual; use no quota. |

## Conflicts resolved for this skill

The sources use different forms because their purposes differ. This policy
therefore avoids universal surface rules:

- Explicit scope and route statements are useful in long guides but become
  throat-clearing in short notes and narrative records.
- Frequent headings support reference and selective reading; fewer headings
  preserve a narrative thread. Section density follows reader use.
- A final retrieval model can improve a long guide; a generic recap weakens a
  project record whose final technical consequence has already landed.
- Hand-drawn diagrams, formal diagrams, screenshots, plots, and interactive
  models are not ranked by prestige. The reader's question determines the
  medium.

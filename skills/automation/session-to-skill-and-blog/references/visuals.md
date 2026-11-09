# Visuals — explanatory questions, diagrams, image assets

## Contents

- [Reader question](#start-with-the-readers-question)
- [Explanation contract](#give-each-visual-an-explanation-contract)
- [Scope and progression](#control-scope-and-progression)
- [Excalidraw vs Mermaid](#excalidraw-vs-mermaid)
- [Authoring rules](#authoring-rules)
- [Attachments](#image-and-excalidraw-attachments)

## Start with the reader's question

Do not set a visual quota. A visual earns its place when prose would require
the reader to reconstruct a spatial, temporal, stateful, or quantitative
relationship mentally. Write the question before choosing the medium.

### Technical posts are illustrated by default

The site owner wants technical posts written with text and visuals
together, not walls of prose. While drafting each section, find the
relationship the prose is enumerating and draw it instead:

- dates or versions listed in a sentence → timeline or Gantt
- package, module, or ownership layout → structure diagram
- a numbered sequence of steps or a loop → flow diagram
- before/after or side-by-side numbers → `before-after-bars` widget or plot

Then cut the prose the visual now carries and keep only the reading order and
the conclusion. A section of three or more paragraphs that enumerates
structure, dates, or numbers without a visual is the failure mode. The
question-first rule below still applies: every visual answers a named
question, and a visual that only restates the heading is still decoration.

### Architecture over implementation

The site owner explains a design with architecture diagrams, not code. A
section says why the decision was made and how the architecture is shaped;
it does not walk through how it was implemented.

- No code reference implementations: no before/after call sites, hook
  bodies, or config listings. Draw the boundary, ownership, or data flow the
  code embodies instead.
- Implementation detail (method counts, timeouts, call names, a workaround
  for one bug) is cut unless the argument depends on it.
- A table of pitfalls and their workarounds becomes a layer diagram with the
  problems annotated on the layer that caused them.
- Section shape: one why-paragraph, the diagram, one conclusion paragraph.
  Before adding prose, check whether the diagram already carries it.

| Reader must understand… | Prefer | Reason |
| ----------------------- | ------ | ------ |
| An observed interface, rendered result, or tool state | Screenshot or short video | Preserve the actual artifact as evidence |
| Ownership, topology, data flow, or system boundaries | Excalidraw or Mermaid flowchart | Position and connections carry the meaning |
| Exact actor-to-actor message order | Mermaid sequence diagram | Lifelines and ordered messages are the model |
| A concrete failure or recovery sequence | Numbered trace; diagram only when branches or concurrent state matter | Exact events matter more than visual polish |
| Alternatives with enumerable properties | Table | Shared axes make the comparison inspectable |
| A quantitative relationship | Plot generated from named data | Shape, scale, and outliers support the claim |
| A parameter space or process the reader should explore | Cataloged `<dynamic>` widget | The reader's action reveals behavior that static examples cannot enumerate |

Use the simplest medium that preserves the relationship. A screenshot cannot
substitute for an architecture model; a diagram cannot prove an observed UI
state; an illustration that only restates the title is decoration.

## Give each visual an explanation contract

Every visual must satisfy three obligations:

1. **Before:** prose names the question or claim the reader should examine.
2. **Inside:** labels identify the relevant entities, direction, conditions,
   units, and boundary. The visual has one primary relationship.
3. **After:** prose walks the intended reading order and states the conclusion
   supported by the visual. Never require the image to make the argument
   alone.

The caption should state what the visual establishes or record the source of
its data. Do not use captions such as “architecture diagram” that merely name
the medium.

## Control scope and progression

- Show only components that affect the current claim. Omitting irrelevant
  detail is part of explanation, not loss of rigor.
- Introduce an overview before a detail view when both are necessary. Reuse
  the same base layout and highlight one change rather than redraw an
  unrelated diagram.
- For an algorithm or protocol, show the system state at each decisive step
  instead of asking readers to simulate it from prose.
- Keep names, colors, directions, and shapes semantically stable across the
  article. Add a legend only when the visual vocabulary is not self-evident.
- When several representations of the same behavior reveal different facts,
  link them by common labels or synchronized state. Do not present unrelated
  views as a gallery.

Plan visuals beside the section outline:

| Section question | Relationship or evidence | Medium | Sentence after the visual |
| ---------------- | ------------------------ | ------ | ------------------------- |
| What crosses the cache boundary? | Package ownership and import reachability | Excalidraw | The task hash must follow reachable build dependencies, not directory ownership. |

The row is a planning aid, not a mandatory article table.

## Excalidraw vs Mermaid

Choose per diagram, not per article. A post usually mixes both.

| Relationship | Use | Why |
| ------------ | --- | --- |
| Timeline / event chain | Mermaid `gantt` (`:milestone, <date>, 0d`; `section` per category) | Real day spacing and grouping without hand layout |
| Pipeline, ordered steps, generation chain | Mermaid `flowchart LR/TB` | Linear structure; automatic routing |
| Fan-in / fan-out ownership (owners → one interface → consumers) | Mermaid `flowchart` | Edges carry the meaning; layout is mechanical |
| Strict sequence diagram | Mermaid `sequenceDiagram` | Lifelines need a formal structure |
| Layered architecture the reader compares at a glance | Excalidraw | Position and stacking carry the meaning |
| Before/after or multi-state panels of the same system | Excalidraw | Panels need aligned, deliberate geometry |
| Problems annotated on the layer that caused them | Excalidraw | Annotations sit beside the exact layer |
| Coverage maps, boundary regions, directory before/after | Excalidraw | Regions and grouping are spatial |

Keep one palette across both media (light blue / light green / light
yellow / light pink, dashed grey for not-built) so colors stay semantic.
Render every Mermaid source locally before patching:
`PUPPETEER_EXECUTABLE_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" npx -y @mermaid-js/mermaid-cli -i x.mmd -o x.png -w 1400 -b white`
(from a scratch directory), then read the PNG. `gantt` does not accept
`classDef`. Inside LiteXML escape the body: `&lt;br/&gt;`, `--&gt;`.

## Authoring rules

- Embed Excalidraw inline as
  `<excalidraw><![CDATA[{...scene JSON...}]]></excalidraw>`.
- Use the canonical color palette (light blue / light purple / light yellow /
  light green / light pink).
- Position text elements explicitly; do not rely on auto-centering across
  blog renderers.
- Keep the palette subordinate to meaning. Do not assign a new color merely
  to make the scene more varied.
- Validate that every diagram answers its named question and that no two
  diagrams make the same point. In a technical post, a section with no visual
  needs a reason: its material is argument or narrative, not structure,
  sequence, or numbers.
- Mermaid inside LiteXML: write line breaks in labels as `&lt;br/&gt;`; a raw
  `<br/>` is parsed as an XML tag and `mxs draft patch` exits 5. Gantt tasks
  accept `Name :YYYY-MM-DD, YYYY-MM-DD`; keep `:` out of task names. After
  inserting, look at the rendered diagram in the admin editor once.

## Image and Excalidraw attachments

When the installed `mxs` has the `file` command group (`mxs file --help`),
upload assets instead of inlining or hot-linking:

```bash
mxs file upload ./shot.png --type image --silent   # → { url, name }
mxs file upload ./diagram.excalidraw --type file --silent
```

- Images: an `<img>` node MUST carry `width`, `height`, and `thumbhash` —
  not just `src`. The mx-core server only extracts image dimensions for
  non-lexical posts (`ImageService.saveImageDimensionsFromMarkdownText` is
  gated behind `!isLexical(doc)`), and blog posts are stored as Lexical, so a
  bare `<img src="..." />` leaves the reader with no aspect-ratio box (layout
  shift) and no blur placeholder. Compute the values with the bundled script
  and inline them:

  ```bash
  # $S is this skill's scripts/ dir. cwd must be a project whose
  # node_modules has sharp + thumbhash (e.g. mx-core). Accepts local
  # paths or the uploaded URL.
  node "$S/image-meta.mjs" --xml https://object.innei.in/.../shot.jpg
  # → <img src="…" width="1504" height="1152" thumbhash="UfcJHYK7uKhwd4aedieXjAlzcwOJ" />
  ```

  The script mirrors the editor's `computeImageMeta` and the server's
  `ImageService` byte-for-byte (longest side resized to 100px, RGBA →
  `rgbaToThumbHash` → base64), so the placeholder matches a natively-uploaded
  image. Drop `--xml` for JSON output.
- Excalidraw: the `<excalidraw>` body accepts a bare URL (remote snapshot) —
  `<excalidraw>https://…/diagram.excalidraw</excalidraw>` — instead of inline
  CDATA JSON. Prefer remote for large scenes; keep small scenes inline so the
  article stays self-contained.
- Manage assets with `mxs file list|delete|rename [--type <t>]`.

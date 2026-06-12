# Visuals — diagrams, palette, image assets

## Excalidraw vs Mermaid

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

## Authoring rules

- Embed Excalidraw inline as
  `<excalidraw><![CDATA[{...scene JSON...}]]></excalidraw>`.
- Use the canonical color palette (light blue / light purple / light yellow /
  light green / light pink).
- Position text elements explicitly; do not rely on auto-centering across
  blog renderers.
- For `site-owner` posts of any substance, **aim for at least three
  Excalidraw diagrams** — one for the high-level pipeline, one for the
  architecture overview, one for the most important decision or chain
  narrated in prose. More is fine; but each diagram must answer a question
  the prose struggled with (see `node-usage.md` quantity discipline).

## Image and Excalidraw attachments

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

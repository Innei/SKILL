---
name: co-write-blog-post
description: >
  Use when the user wants to write a blog post together with the agent in a
  live editor, starting from a blank page or resuming an unfinished draft —
  "从空白开始写一篇…我们协同写", "开个编辑器一起写", "继续写那篇草稿",
  "co-write a post with me", "open the editor and let's write" — and asks the
  agent along the way to draw diagrams, rewrite passages, add images, or check
  the prose in the same article.
---

# co-write-blog-post

The human writes in the Mix Space admin editor in the browser; the agent edits
the same draft when asked. Both sit in the draft's collaboration room on the
server: `mxs draft cat` reads the live draft, `mxs draft patch` applies one
SEARCH/REPLACE edit that lands in the open editor at once, behind a cursor
named after the agent, as one undoable row in the draft's history. There is
no local file and no local editor process. `mxs skill get commands-draft` is
the authoritative contract; read it once per session.

## Capability contract

- **Outcome:** a Mix Space draft (or post, after explicit approval) whose prose
  the human wrote, with agent contributions made only on request.
- **Preconditions:** `mxs` whose `mxs draft --help` lists `cat` and `patch`;
  `mxs auth whoami` succeeds; the server's admin URL is configured (the
  draft link comes from it); the `session-to-skill-and-blog` skill is
  installed (its references and scripts are reused, not copied).
- **Production profile:** `mxs` refuses writes to a profile marked production
  (`write blocked … is production`, exit 4) unless the command names it.
  Prefix every writing command — `create-draft.sh`, `draft patch`,
  `file upload`, `draft update` — with `MXS_PROFILE=<profile>`; an `export`
  does not survive between separate shell calls.
- **Boundaries:** not for turning a finished engineering session into a post
  (use `session-to-skill-and-blog`); never writes the human's prose
  unprompted; never publishes without an explicit yes.

## Setup

Locate the shared scripts once (same search loop as `session-to-skill-and-blog`):

```bash
S=""
for cand in \
  "$HOME/.claude/skills/session-to-skill-and-blog/scripts" \
  "$HOME/.codex/skills/session-to-skill-and-blog/scripts" \
  "$HOME/.agents/skills/session-to-skill-and-blog/scripts" \
  "$(git rev-parse --show-toplevel 2>/dev/null)/skills/automation/session-to-skill-and-blog/scripts"
do
  [ -f "$cand/resolve-skill-repo.sh" ] && { S="$(cd "$cand" && pwd)"; break; }
done
[ -n "$S" ] || { echo "error: session-to-skill-and-blog not installed" >&2; exit 1; }
REFS="$(dirname "$S")/references"
```

## Workflow

### [0] Intake

Ask in one interactive-question call (plain chat if no such tool), in Chinese,
then wait:

1. 这篇文章用哪种写作人格？ — 站长第一人称 / 中性叙述 / 看材料再定
   (record `site-owner` / `neutral` / `defer`; meaning per
   `$REFS/writing-style.md` › Choose the narrator).
2. 文章用什么语言？ — 中文 / English / 其他

The topic comes from the trigger message. Skip a question the trigger already
answered. When resuming, infer both from the draft's existing text and ask
only if it has none.

### [1] Create or resume the draft

- Resuming ("继续写…"): `mxs draft list` and pick the draft by title; ask in
  one line if more than one fits. Never create a second draft for the same
  article. If the human's tab is closed, point them at the draft in the
  admin Drafts list, then go to [2].
- New: write a minimal envelope to a scratch file (your session scratch
  directory, not the cwd) with the topic as the working title and a
  kebab-case slug, then create the draft with the AI disclosure set to
  handmade:

```xml
<mxpost>
  <meta>
    <title>工作标题</title>
    <slug>the-slug</slug>
    <format>lexical</format>
  </meta>
  <content><p></p></content>
</mxpost>
```

```bash
bash "$S/create-draft.sh" "$SCRATCH/article.xml" --ai-gen '-1'
```

The script prints `ok: true`, `id: <draftId>` and an `opening admin: <url>`
line.
Remember the id for the session; the scratch file is not used again.

### [2] Hand over the editor

Give the human the admin URL in one line and **stop** until they speak.
Outline ideas, if any, go in chat, not in the draft.

### [3] One request, one patch

For every request (a message with several requests — new title *and* a
smoother paragraph — runs this loop once per request):

1. Read the live draft: `mxs draft cat <id>`. Anything in context is stale;
   the human has been typing. For a long draft start with `--outline` and
   read the section you need. When the request points at the human's
   selection ("选中的这段", "这里", "this bit"), run
   `mxs draft cat <id> --selection`; it returns the blocks they last
   selected, even after the editor lost focus. If it says there is no
   selection, or the request still does not pin a spot (e.g. which paragraph
   a diagram follows), ask in one line before editing.
2. Load only the reference the request needs:

   | Request | Load |
   | ------- | ---- |
   | Diagram (画图, 流程图, 时序图) | `$REFS/visuals.md`, then LiteXML syntax via `bash "$S/load-litexml.sh"`; Excalidraw scenes go in as uploaded files per "Assets" |
   | Rewrite, tighten, continue a passage | `$REFS/writing-style.md` with the narrator from [0] |
   | Write or rewrite a section of a technical post | `$REFS/writing-style.md` and `$REFS/visuals.md` › Technical posts are illustrated by default: the section ships with its visual in the same patch, and prose the visual carries is cut |
   | Image / screenshot | "Assets" below |
   | Excalidraw scene, chart data, any JSON or file the article references | "Assets" below |
   | Interactive widget or special node | `$REFS/node-usage.md` |
   | Numbers compared before/after (timings, sizes) | `before-after-bars` entry in the `dynamic-widgets-catalog` snippet (`mxs snippet get dynamic-widgets-catalog`); insert a `<dynamic>` node with its current `url` and props instead of a table |
   | Any other interactive explanation | `$REFS/node-usage.md` › catalog rule: reuse a current catalog widget through its props; if none fits, tell the human instead of writing one inline |
   | Title, slug, tags, category, summary | the `<meta>` lines in `cat` output, patched like any block; category by an existing slug from `mxs category list --output llm` |

3. Apply it with **one** `mxs draft patch <id>` touching only the requested
   blocks. Copy each SEARCH from the `cat` output you just read, tags and
   `id` attributes included; to insert a block, use its neighbour as SEARCH
   and repeat it in REPLACE:

```bash
mxs draft patch <id> --message "rewrite intro" <<'EOF'
<<<<<<< SEARCH
<p id="hPzZ7MhV">exact text copied from cat</p>
=======
<p id="hPzZ7MhV">replacement</p>
>>>>>>> REPLACE
EOF
```

4. Read the exit code:
   - `0` and `applied: +a ~m -d blocks` (plus `; meta: <fields>` when
     `<meta>` changed) → done; the human already sees it.
   - `1` → the human changed that text after your `cat`. The error shows the
     block's current content: redo the edit on top of it with a fresh SEARCH.
     Never resend the same SEARCH. A second failure → tell the human.
   - `5` → the patch itself is malformed, or a replacement uses a tag the
     editor would drop (the message names it). Fix the block and retry.
   - `4` with `write blocked … is production` → rerun the same command with
     `MXS_PROFILE=<profile>` (see Preconditions).
   - `3` / `4` / `6` otherwise → not signed in, network, server rejected.
     Report the line; do not retry blindly.
5. When the edit is a new kind of contribution, record it in the draft's
   disclosure with a patch on `<ai-gen>` (see [4] step 3 for the values),
   e.g. `<ai-gen>-1</ai-gen>` → `<ai-gen>[8]</ai-gen>` after the first
   diagram. The draft is the only place that state lives.
6. Reply in one or two lines (what changed, where), then stop.

Suggestions the human did not ask to apply — alternative wording, a missing
transition, a follow-up sentence a diagram needs — go in chat for the human
to accept.

#### Assets

The editor is online, so anything the article references is uploaded when it
is inserted. Upload only what the human asked to insert.

- Images: run `image-meta.mjs --xml` on the local file first (cwd = a
  project with `sharp` + `thumbhash`, e.g. mx-core) for `width`, `height`,
  `thumbhash`, then `mxs file upload <path> --type image` and use the URL.
- Excalidraw scenes, chart data, JSON, attachments: write the file to your
  scratch directory, `mxs file upload <path> --type file`, and reference the
  URL (`<excalidraw>https://…/scene.excalidraw</excalidraw>`), never an
  inline CDATA body.
- Always upload **without** `--silent` and read the `url:` line. The server
  renames every file, and neither `--silent` output nor `mxs file list` gives
  the URL back; an upload whose URL was not captured is an orphan in object
  storage.

### [4] Finish

When the human says 写完了 / done:

1. `mxs draft cat <id>` for the final state. There is no diff file; compare
   with what you wrote only if you need to know what the human changed.
2. Run the no-ai-slop detect sweep (`bash "$S/load-no-ai-slop.sh"`) on that
   output and list findings in chat; the human edits in the browser or asks
   you to patch a specific one. Never auto-rewrite.
3. Wait until the human says the slop fixes are done, then propose the AI
   disclosure from the draft's `<ai-gen>` and let the human confirm: `-1`
   handmade (agent changed nothing), `0` assist (rewrote or drafted
   passages), `4` title, `8` illustration (diagrams or images). Values
   combine, e.g. `[0,8]`. Patch `<ai-gen>` to the confirmed value.
4. Make sure `<category>` holds an existing slug and `<tags>` are filled
   (patch them), then follow `$REFS/publish-flow.md` for publishing.
5. Paywall position ("设置付费墙位置") → `meta.paywall.previewBlocks` counts
   top-level blocks shown free. Count them from `mxs draft cat <id> --outline`,
   offer section boundaries as options, and patch the `<paywall>` line (add
   it after `<ai-gen>` if missing: `<paywall>{"previewBlocks":37}</paywall>`).
   The paywall only applies once the draft is premium:
   `mxs draft update <id> --premium true` (needs `mxs` ≥ 0.21.5; older builds
   have no flag, and the human toggles it in the admin premium panel).

Publish only after the human approves the draft preview.

## Failure boundaries

| Mistake | Fix |
| ------- | --- |
| Editing from a `cat` read several turns ago | `cat` again right before every patch; the human keeps typing. |
| Resending a SEARCH after exit `1` | The text changed: rebuild the edit from the current block shown in the error. |
| `mxs draft update --file` while the human has the editor open | Overwrites the whole draft over their edits; use `patch`. |
| Uploading files nobody asked to insert | Upload only on insertion; a draft abandoned mid-way leaves only what it shows. |
| Inline Excalidraw JSON in the draft | Upload the scene with `--type file` and reference the URL. |
| `mxs file upload --silent`, then looking for the URL | Upload without `--silent` and read `url:`; the server-side name is random and not recoverable. |
| Forgetting contributions on a resumed draft | Read and patch `<ai-gen>` in the draft. |
| Creating a second draft for an article that exists | `mxs draft list` and resume it. |
| Filling the blank page with a full draft or outline | Only write what was asked; offer outlines in chat. |
| Rewriting neighbouring blocks "while there" | Touch only the requested blocks. |
| A technical section that lists dates, structure, or numbers as prose | Draw the relationship (Gantt, structure, flow, bars) and cut the enumerating prose. |
| Raw `<br/>` inside `<mermaid>` (patch exits 5) | Write `&lt;br/&gt;`. |
| Publishing on 写完了 | 写完了 starts the finish sweep; publishing needs an explicit yes. |
| `aiGen=2` on a co-written post | Patch `<ai-gen>` to the confirmed value. |

## Verification

- [ ] Intake answers recorded (or taken from the trigger or the draft) before editing.
- [ ] One draft per article; a resumed draft was not recreated.
- [ ] Every agent change was one `mxs draft patch` built from a fresh `cat`, with exit `0`.
- [ ] No prose was added to the article without a request.
- [ ] Every uploaded file's URL was captured and is referenced in the article.
- [ ] Slop findings were reported, not auto-applied.
- [ ] `<ai-gen>` on the draft matches the value the human confirmed; nothing was published without an explicit yes.

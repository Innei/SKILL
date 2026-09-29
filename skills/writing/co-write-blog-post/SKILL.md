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

The human writes in the browser; the agent edits the same LiteXML file when
asked. `mxs author` keeps both in sync through a Loro CRDT: browser edits
autosave to the file, in-place agent edits are merged three-way and streamed
into the editor behind an **Agent** caret, and history persists in
`<file>.loro`. `mxs skill get commands-author` is the authoritative contract;
read it once per session.

## Capability contract

- **Outcome:** a Mix Space draft (or post, after explicit approval) whose prose
  the human wrote, with agent contributions made only on request.
- **Preconditions:** `mxs` whose `commands-author` chapter mentions `.loro`
  (Loro-synced author); `mxs auth whoami` succeeds before publishing; the
  `session-to-skill-and-blog` skill is installed (its references and scripts
  are reused, not copied).
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
DRAFTS=$(jq -r '.blog_drafts_dir // "~/blog-drafts"' ~/.config/innei-skills/config.json 2>/dev/null || echo "~/blog-drafts")
DRAFTS="${DRAFTS/#\~/$HOME}"
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
answered. When resuming, read the answers from `session.json` instead of asking.

### [1] Open or resume the draft file

Derive a kebab-case `<slug>` from the topic. The file is
`$DRAFTS/<slug>/article.xml` — never `/tmp`, because `article.xml.loro` holds
the history the human can restore later. Beside it, `session.json` carries
state across agent sessions; update it whenever a field changes:

```json
{ "narrator": "site-owner", "language": "zh", "aiGen": [8], "draftId": null, "paywall": null }
```

`aiGen` accumulates what you actually contributed (see [4]); `draftId` is set
once `create-draft.sh` returns.

- Resuming ("继续写…"): list `$DRAFTS/*/article.xml` with their `<title>`,
  pick the match, ask in one line if more than one fits. Never recreate it.
- New: write the file once, using the topic as the working title:

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

### [2] Start the editor

First check that no editor already serves this file
(`pgrep -fl "mxs.*author.*<slug>/article.xml"`); if one does, ask the human
whether its tab is still open instead of starting a second process on the same
file. Otherwise start it with your runtime's background mode (Claude Code:
Bash `run_in_background`), keeping its output in a log beside the draft:

```bash
mxs author --no-open "$DRAFTS/<slug>/article.xml" > "$DRAFTS/<slug>/author.log" 2>&1
```

Give the human the URL printed in `author.log` in one line, and **stop** until
they speak. Outline ideas, if any, go in chat, not in the file.

### [3] One request, one edit

For every request while the editor runs (a message with several requests —
new title *and* a smoother paragraph — runs this loop once per request):

1. Re-read the file. The browser has been autosaving; anything in context is stale.
2. Locate the target by quoting its heading or paragraph text back. When the
   request points at the human's selection ("选中的这段", "这里", "this bit"),
   read `<file>.selection.json` first and match `blocks[].id` to the `id`
   attributes in the file; it keeps the last selection after the editor loses
   focus, so check `updatedAt` is recent. If the file is missing (older `mxs`)
   or the request still does not pin a spot (e.g. which paragraph a diagram
   follows), ask in one line before editing.
3. Load only the reference the request needs:

   | Request | Load |
   | ------- | ---- |
   | Diagram (画图, 流程图, 时序图) | `$REFS/visuals.md`, then LiteXML syntax via `bash "$S/load-litexml.sh"` |
   | Rewrite, tighten, continue a passage | `$REFS/writing-style.md` with the recorded narrator |
   | Image / screenshot | `$REFS/visuals.md` › attachments (`mxs file upload`, `image-meta.mjs`) |
   | Interactive widget or special node | `$REFS/node-usage.md` |
   | Numbers compared before/after (timings, sizes) | `before-after-bars` entry in the `dynamic-widgets-catalog` snippet (`mxs snippet get dynamic-widgets-catalog`); insert a `<dynamic>` node with its exact `url` and props instead of a table |
   | Title, slug, tags, category | edit `<meta>` in place; the server adopts your envelope and later autosaves keep it (stdout: `+0 ~0 -0 blocks`) |

4. Apply it with **one in-place edit** (Claude Code `Edit`, Codex `apply_patch`)
   touching only the requested blocks.
5. Wait for the result line — edits stream in over a few seconds. Count
   `agent edit` lines in `$DRAFTS/<slug>/author.log` before editing, then wait
   (up to ~15 s) for the count to grow and read the last line:
   - `agent edit merged: +a ~m -d blocks` → re-read the changed block in the
     file: LiteXML drops unknown tags silently, so a mistyped node vanishes
     while the log still says merged.
   - `agent edit rejected: …` → the envelope or a tag pair is broken (the
     message names it); fix the file in place and retry.
   - `agent edit failed: …` → the merge threw; report the line to the human
     and do not retry blindly.

   In Claude Code, run the wait as a background `until` loop or a Monitor, not
   a foreground sleep. Record a new contribution kind in `session.json` › `aiGen`.
6. Reply in one or two lines (what changed, where), then stop.

Suggestions the human did not ask to apply — alternative wording, a missing
transition, a follow-up sentence a diagram needs — go in chat for the human
to accept.

### [4] Finish

When the human says 写完了 / done (for a bare "更新草稿" on a draft that already
has a `draftId`, skip to step 4 with the `aiGen` already in `session.json`):

1. Read `article.xml.diff` only if you need to know what the human changed.
2. Run the no-ai-slop detect sweep (`bash "$S/load-no-ai-slop.sh"`) and list
   findings in chat; the human edits in the browser. Never auto-rewrite.
3. Wait until the human says the slop fixes are done, then propose the AI
   disclosure from `session.json` › `aiGen` and let the human confirm: `-1`
   handmade (agent changed nothing), `0` assist (rewrote or drafted passages),
   `4` title, `8` illustration (diagrams or images). Values combine, e.g. `'[0,8]'`.
4. Fill `<category>` (existing slug from `mxs category list --output llm`) and
   `<tags>` in place, then follow `$REFS/publish-flow.md`:
   - no `draftId` yet → "Create" with
     `bash "$S/create-draft.sh" "$DRAFTS/<slug>/article.xml" --ai-gen '<value>'`,
     and store the returned id in `session.json`;
   - `draftId` exists (the human kept writing after a draft was made) →
     `mxs draft update <draftId> --file …`, then re-attach the whole meta:
     the confirmed `aiGen` (not `2`) plus any `paywall` recorded in
     `session.json`, e.g. `--meta '{"aiGen":[0,8],"paywall":{"previewBlocks":37}}'`.
   - Paywall position ("设置付费墙位置") → `meta.paywall.previewBlocks` counts
     top-level blocks shown free. Count root children of the server draft
     (`mxs draft get <id> --json`), offer section boundaries as options, set it
     with `mxs draft update <id> --meta` (keeping `aiGen`), and store it in
     `session.json` › `paywall`. `isPremium` has no CLI flag; the human toggles
     it in the admin premium panel.
   Keep the editor running; later browser edits reach the server only through
   this step. Publish only after the human approves the draft preview.

## Failure boundaries

| Mistake | Fix |
| ------- | --- |
| Draft under `/tmp` or the cwd | `$DRAFTS/<slug>/article.xml`; the `.loro` history must survive reboots. |
| Re-asking intake on resume, or forgetting contributions | Read and update `session.json`. |
| Second `mxs author` on a file already being served | `pgrep` first; two processes fight over one file. |
| Recreating a draft that exists | Resume it; the file and its history are the human's work. |
| `Write` of the whole file, or editing from a copy read minutes ago | Re-read, then one in-place edit; a stale base reads as deleting the human's new text. |
| Filling the blank page with a full draft or outline | Only write what was asked; offer outlines in chat. |
| Rewriting neighbouring blocks "while there" | Touch only the requested blocks. |
| Stopping the editor to edit `<meta>` | Meta edits are live; edit in place. |
| Following `publish-flow.md`'s old "do not rewrite while running" wording | The live contract is `mxs skill get commands-author`. |
| Publishing on 写完了 | 写完了 starts the finish sweep; publishing needs an explicit yes. |
| `aiGen=2` on a co-written post | Pass `--ai-gen` with the confirmed value. |

## Verification

- [ ] Intake answers recorded (or taken from the trigger) before the file was created.
- [ ] Draft lives at `$DRAFTS/<slug>/article.xml` with an up-to-date `session.json`; an existing draft was resumed, not recreated.
- [ ] Every agent change was one in-place edit followed by `agent edit merged` on stdout.
- [ ] No prose was added to the article without a request.
- [ ] Slop findings were reported, not auto-applied.
- [ ] `meta.aiGen` on the draft matches the value the human confirmed; nothing was published without an explicit yes.

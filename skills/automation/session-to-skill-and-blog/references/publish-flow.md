# Publish flow — draft, review, publish, stage/apply

This file is the single home for publish correctness. Do not improvise
meta, state, or category flags from memory.

## Order

Create the server-side draft first (next section), then review it in the
online editor. There is no local editor any more: `mxs author` was removed,
and the draft is reviewed and edited live in the admin write page.

## Review (online editor, after the draft exists)

`create-draft.sh` passes `--open`, which prints the admin URL of the draft.
Requires an `mxs` whose `mxs draft --help` lists `cat` and `patch`;
`mxs skill get commands-draft` is the authoritative contract.

Production profile: `mxs` refuses writes to a profile marked production
(`write blocked … is production`, exit 4) unless the command names it.
Prefix every writing command in this file (`push-skill.sh`,
`create-draft.sh`, `draft patch`, `draft publish`, `post stage/apply`,
`file upload`) with `MXS_PROFILE=<profile>`; an `export` does not survive
between separate shell calls.

Agent loop:

1. Create the draft (next section), tell the user the admin URL.
2. **Stop.** Do not poll, do not auto-continue.
3. If the user asks for changes, read the live draft with
   `mxs draft cat <draftId>` (or `--selection` when they point at "this
   paragraph"), then change only the requested blocks with one
   `mxs draft patch <draftId>` (SEARCH copied from `cat`, REPLACE the new
   text). The edit appears in their open editor immediately and prints
   `applied: +a ~m -d blocks`, plus `; meta: <fields>` when `<meta>`
   changed. On exit 1 the
   text changed under you: `cat` again and redo the edit; never resend the
   same SEARCH. Then stop again.
4. When the user says done, read the final state with
   `mxs draft cat <draftId>`. There is no diff file; compare against what
   you wrote only if you need to know what they changed.
5. Continue with the anti-slop sweep on that output (`writing-style.md` ›
   External sweep: lieflat for Chinese, no-ai-slop for English). Report
   findings; the user fixes them in the editor, or asks you to `patch` them.

Keep authoring sources `<doc>`-wrapped when editing bare fragments —
inter-block whitespace otherwise becomes root-level text nodes (Lexical
error #282). A save rewrites `<content>` as bare block tags (the `<doc>`
wrapper is dropped); that is fine for `mxs draft create`, which wraps
server-side.

Never pass a bare LiteXML body to `mxs --file`. Wrap it in
`references/envelope.template.xml` first.

Do not hand-write `<summary>` — server AI generates it and may overwrite.

## Create (native draft entity)

The article starts life as a server-side **draft entity** — not a post
with draft state. No post exists (and nothing can leak to readers) until
`mxs draft publish`.

Do not create a post (even with `--state draft`) to stage the article.
A draft-state post pollutes the post list and a stray `<state>draft</state>`
on a later update unpublishes the live post.

```bash
mxs auth whoami                      # confirm; if not, mxs auth login
mxs category list --output llm       # MUST reuse an existing category slug
cp "$(dirname "$S")/references/envelope.template.xml" /tmp/blog/article.xml
# edit envelope: fill <title>/<slug>/<category>/<tags>, paste LiteXML body

# Optional: repeat for every accepted skill so the blog can attach it.
SKILL_ID=$(bash "$S/push-skill.sh" "$REPO/skills/<domain>/<skill-name>/SKILL.md")

bash "$S/create-draft.sh" /tmp/blog/article.xml --skill-id "$SKILL_ID"
# With no accepted skill, omit every --skill-id argument:
# bash "$S/create-draft.sh" /tmp/blog/article.xml
# → prints `ok: true` and `id: <draftId>` — capture the id for the next steps.
# The user reviews in the admin draft editor opened by --open (see Review).
```

`create-draft.sh` runs `mxs draft create` with `aiGen=2` (override with
`--ai-gen '<json>'`, e.g. `'[0,8]'` for a co-written post) and `--open`.
With one or more `--skill-id <id>` args it jq-assembles `meta.skillIds`
so the admin SkillPicker / public article card list resolve the attached
skills. Without those arguments it writes only `meta.aiGen`. Never hand-write
the initial metadata payload.

Creating a new category requires an explicit second confirmation from
the user before `mxs category create`.

Legacy fallback (installed `mxs` lacks the `draft` group — check
`mxs draft --help`): `mxs post create --file <xml> --state draft`,
preview, then `mxs post publish <slug>`. `create-draft.sh` does not
implement this fallback.

## Iterate on the draft

Once the user has the editor open, edit only with `mxs draft patch`
(see Review). It changes just the blocks you name, keeps their concurrent
typing, and leaves `meta` alone unless a SEARCH/REPLACE block targets
`<meta>` (`<ai-gen>`, `<skill-ids>`, `<tags>`, …). Do not re-run
`draft create`.

`mxs draft update <draftId> --file …` replaces the whole draft, discards
anything the user typed in the editor, and **wipes `meta`** (`aiGen`, and
`skillIds` when present). Use it only before the user has opened the draft.
If it ran, re-attach and confirm. With attached skills:

```bash
mxs draft update <draftId> --meta '{"aiGen":2,"skillIds":["<SKILL_ID>"]}'
mxs draft get <draftId>
```

If several `--skill-id`s were used at create, list every id in
`skillIds`. With no accepted skill, restore only `aiGen`:

```bash
mxs draft update <draftId> --meta '{"aiGen":2}'
mxs draft get <draftId>
```

Skip the re-attach when no file update ran after create.

## Publish (after the user approves)

```bash
mxs draft publish <draftId>
```

One step: creates the live post from the draft (`POST /posts` with
`draftId`), links the draft to it, and marks the draft version as
published. The draft and its history are retained.

Publish creates the live post immediately. Only run it after the user
approves the admin preview.

Then **always** verify the live post — do not assume `draft publish`
preserved camelCase meta. mxs ≤0.14.x is known to fail with "draft not
found" (server snake_cases `ref_type`, CLI reads `refType`) and to
re-send snake_cased `meta` (`skill_ids` instead of `skillIds`). Newer
versions may have fixed this; still verify.

```bash
mxs --version
mxs post get <slug> --output json
```

Always confirm `meta.aiGen` equals the value passed to `create-draft.sh`
(`2` unless `--ai-gen` was given). When skills were attached, confirm
`meta.skillIds` is the exact id list (camelCase, not `skill_ids`) and that the
skill cards render on the live page. With no accepted skill, confirm
`meta.skillIds` is absent or empty. Repair the metadata when it differs:

```bash
mxs post update <slug> --meta '{"aiGen":2,"skillIds":["<SKILL_ID>"]}'
# No accepted skill:
# mxs post update <slug> --meta '{"aiGen":2}'
```

## Edit after publication (round-trip)

```bash
bash "$S/get-post.sh"   <slug> > /tmp/blog/article.xml
# edit
bash "$S/update-post.sh" <slug> /tmp/blog/article.xml
```

`update-post.sh` strips `<state>` so a reused create envelope cannot
unpublish the live post. Publish-state changes go only through
`mxs post publish|unpublish`.

## Update a published title or slug

Resolve the post by immutable id and check that the proposed slug is not
already in use. After the user approves the exact title and slug, update only
those fields:

```bash
mxs post get <new-slug> --output llm  # must return POST_NOT_FOUND
mxs post update <post-id> \
  --title '<approved-title>' \
  --slug '<approved-slug>' \
  --silent
```

Use the post id as the mutation target. Addressing the operation by the old
slug makes subsequent verification and retries ambiguous after the first
successful change.

In `mxs` 0.15.0, `post stage --title … --slug …` fails for lexical posts
because draft validation also requires `content` and `text`. For a reviewed
metadata-only change, use the partial `post update` command above. If the
change still requires an admin draft preview, round-trip the complete XML
envelope and stage that file instead.

The post service records the previous category-and-slug path when a slug
changes. Do not rely on that implementation without verification. Confirm the
new slug, publication state, content format, and metadata by immutable id;
then check that the new lookup succeeds and the old public URL redirects.

```bash
mxs post get <post-id> --output json
mxs post get <new-slug> --output llm
```

A partial title-and-slug update must preserve `meta.aiGen`, every existing
`meta.skillIds` entry, `contentFormat`, and the published state.

## Edit a published post (stage/apply)

Prefer stage/apply when the installed `mxs` supports it
(`mxs post stage --help`) — the live post stays untouched until the user
confirms:

```bash
mxs post stage <slug> --file /tmp/blog/article.xml   # readers see nothing; prints the draft
# The user reviews in the admin editor; agent changes go through
# `mxs draft cat/patch <draftId>` on the staged draft. Then, on approval:
mxs post apply <slug>                                # the confirm step
```

Fallback on older `mxs`: `update-post.sh` (it strips `<state>` so the post
at least never unpublishes, but changes go live immediately).

Do not use metadata-only stage flags for a lexical post unless the installed
CLI accepts them. Use the complete envelope or the approved partial-update
flow above.

On the first update of a legacy post that is missing `aiGen`, re-attach
with `mxs post update <slug> --meta '{"aiGen":2}'` (and `skillIds` if
the card should render).

## Receipt

Paste the final URL (`${MXS_API_URL}/posts/<category>/<slug>`) back into
the originating session as the asset-ization receipt.

## Publish checklist

- [ ] `mxs auth whoami` returned the expected user.
- [ ] `<category>` reuses an existing slug, or the user explicitly approved a new one.
- [ ] Envelope used; no hand-written `<summary>`.
- [ ] Title retains the defining technical identity; slug uses stable ASCII kebab-case terms and was checked for collision.
- [ ] Reviewed in the online draft editor; agent edits went through `mxs draft patch`; the final state was read with `mxs draft cat`.
- [ ] Native draft entity (`create-draft.sh` → `ok: true` / `id: <draftId>`), not a draft-state post.
- [ ] After the last `draft update --file`, meta re-attached and confirmed via `draft get`.
- [ ] `mxs draft publish <draftId>` ran only after the user approved the admin preview.
- [ ] Live `meta.aiGen` verified; `meta.skillIds` matches the accepted skills and is absent or empty when there are none.
- [ ] After a slug change, the new lookup succeeds and the old public path redirects.
- [ ] Every attached skill card renders on the live page, or the mx-core trade-off was explicitly accepted.
- [ ] Final post URL pasted back into the originating session.

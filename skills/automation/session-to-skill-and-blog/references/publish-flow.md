# Publish flow — preview, create, round-trip, stage/apply

## Preview

```bash
mxs preview /tmp/blog/article.xml
```

`mxs preview` is envelope-aware: it strips the `<mxpost>` / `<mxnote>`
wrapper, auto-detects `--variant`, and opens the HTML in the system browser
by default. `--print` dumps to stdout; `--save <path>` writes a file without
opening.

Keep authoring sources `<doc>`-wrapped when previewing bare fragments —
inter-block whitespace otherwise becomes root-level text nodes (Lexical
error #282). mxs wraps server-side, so the published post is unaffected.

## Create (always draft)

```bash
mxs auth whoami                      # confirm; if not, mxs auth login
mxs category list --output llm       # MUST reuse an existing category slug
cp "$(dirname "$S")/references/envelope.template.xml" /tmp/blog/article.xml
# edit envelope: fill <title>/<slug>/<category>/<tags>, paste LiteXML body

# Optional: push the SKILL.md to mx-core first so the blog can attach it.
SKILL_ID=$(bash "$S/push-skill.sh" "$REPO/skills/<domain>/<skill-name>/SKILL.md")

bash "$S/publish-post.sh" /tmp/blog/article.xml --skill-id "$SKILL_ID"
# Innei previews in the admin tab opened by --open; when approved:
mxs post publish <slug>
```

`publish-post.sh` creates as draft with `aiGen=2` and `--open`. With one
or more `--skill-id <id>` args it jq-assembles `meta.skillIds` so the
admin SkillPicker / public article card list resolve the attached
skill(s). Never `--state publish` on create; never hand-write
`<summary>` (server AI generates it).

## Edit a draft (round-trip)

```bash
bash "$S/get-post.sh"   <slug> > /tmp/blog/article.xml
# edit
bash "$S/update-post.sh" <slug> /tmp/blog/article.xml
```

## Edit a published post (stage/apply)

Prefer stage/apply when the installed `mxs` supports it
(`mxs post stage --help`) — the live post stays untouched until Innei
confirms:

```bash
mxs post stage <slug> --file /tmp/blog/article.xml   # readers see nothing
# Innei reviews (local preview / admin), then approves:
mxs post apply <slug>                                # the confirm step
```

Fallback on older `mxs`: `update-post.sh` (it strips `<state>` so the post
at least never unpublishes, but changes go live immediately).

## Receipt

Paste the final URL (`${MXS_API_URL}/posts/<category>/<slug>`) back into
the originating session as the asset-ization receipt.

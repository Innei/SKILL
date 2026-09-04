---
name: working-summary
disable-model-invocation: true
description: Use when the user asks for a work summary, weekly report, 工作总结，周报，working summary, or sprint/period recap. Aggregates GitHub PR/commit/issue activity from configured repos, optionally reads Linear cycle issues via MCP, honors Chinese public holidays, and produces a markdown report. Default range is the previous Mon-Sun week.
---

# Working Summary

Generate a **period work summary** by aggregating GitHub PR/commit activity across configured repositories and — optionally — Linear cycle issues. The default time range is the previous Mon–Sun week, computed with awareness of Chinese public holidays. Output is **markdown**, suitable for Obsidian or any note system.

## Config

Config path (default): **`~/.config/working-summary/config.yaml`**
Override via `--config <path>`.

If the file is missing, tell the user to copy `config.example.yaml` (next to this skill) into the expected path and edit. Do **not** fabricate defaults.

```yaml
github:
  user: innei # optional; falls back to `gh api user -q .login`
  orgs: # org-scope query — ONE gh search call per org
    - lobehub
    - lobehub-biz
  repos: # optional explicit repos (in addition to orgs)
    - innei/next-real-comment
    - mx-space/core
  include_commits: true # pull per-repo commits for active repos
linear: # optional, needs `linear` CLI authed
  workspace: lobehub # informational
  team: LOBE # team key (issue prefix)
  cycle: auto # previous | current | auto
  include_states: [In Progress, Done]
output:
  # Language for synthesized prose. Section headers and raw PR/issue/commit
  # titles are kept verbatim regardless; only descriptions and framing prose
  # follow this setting. Examples: zh-CN, en, ja
  language: zh-CN
  # Optional persistence target. When set, the user may choose to save the
  # report to `dir` at the end of a run. Leave unset to operate ephemerally.
  dir: ~/Documents/Obsidian/Reports
  # Placeholders: {year} {month} {week} {start} {end} {ext}
  filename: '{year}-{month}-w{week}.{ext}'
```

## Output Flow

The skill **never writes a file by default**. It synthesizes markdown in the
conversation (which serves as the terminal display) and then asks the user
whether to persist the result.

At the end of synthesis, prompt the user with these options:

| Choice         | Behavior                                                                                                                                                                                                                                                                |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `no` / nothing | Done. Report lives only in the conversation.                                                                                                                                                                                                                            |
| `md`           | Write markdown to `output.dir/{filename}` (ext=`md`).                                                                                                                                                                                                                   |
| `html`         | Render themed HTML to `$TMPDIR/working-summary-<stamp>.html` via `scripts/render_html.py`, run `open` on it, then ask whether to also move a copy to `output.dir/{filename}` (ext=`html`).                                                                              |
| `both`         | Do `md` and `html` in that order.                                                                                                                                                                                                                                       |
| `linear`       | Create a Linear issue in the **report cycle**, assigned to the viewer, state set to the team's `completed` state (typically "Done"), with the report markdown as the description. Requires Linear to be configured AND connected. See **Linear archive** below.          |
| `lobehub`      | Create a markdown document in the configured LobeHub knowledge base via the `lh` CLI (the company weekly-report library). Requires `output.lobehub`. See **LobeHub publish** below.                                                                          |
| `publish`      | Upload the HTML report to the configured R2 bucket (served at the configured public base URL via a Cloudflare Worker behind Access). Requires `output.publish` to be set. Renders HTML to a tempfile if no `html` was produced yet. See **R2 publish** below.            |

Choices compose with `+`: e.g. `linear+html`, `html+publish`, `lobehub+md`.
Order of operations within a composite:

1. **linear** archive (if requested) — so the issue exists before any file write.
2. **lobehub** publish (if requested) — the markdown goes up as-is, before any rendering.
3. **publish** to R2 (if requested) — so the public URL exists before the local file is touched.
4. **html** / **md** local persistence (if requested).

Bare `linear` / `lobehub` / `publish` is fine when no local file is wanted.

**Default choice from config**: when `output.format` is set in the config
file, use it as the **highlighted default** in the prompt (e.g.
`format: html` → "落盘否？[**html** / md / both / linear / publish / no]").
The user can still override by typing another choice. When `output.format`
is unset or is `markdown`, highlight `md` as default. When `output.format`
is `both`, highlight `both`. `output.format` may also be set to any of the
composite values (`linear`, `linear+md`, `linear+html`, `linear+both`,
`publish`, `html+publish`, `linear+publish`, `linear+html+publish`,
`lobehub`, `lobehub+md`, `lobehub+html`, `lobehub+linear`).

The HTML renderer is a deterministic post-processor — the LLM only ever
produces markdown. See **HTML Rendering** below.

Never overwrite an existing file silently. If the target exists, ask the
user (append, overwrite, or new suffix).

## Default Time Range

The skill uses a **previous Mon–Sun week** as the default:

| Today is | Range                                 |
| -------- | ------------------------------------- |
| Mon      | `[last Mon, yesterday Sun]`           |
| Tue..Sat | `[prev Mon, prev Sun]`                |
| Sun      | `[prev Mon, prev Sun]` (not this Sun) |

Explicit overrides:

- `--from YYYY-MM-DD --to YYYY-MM-DD` — hard range
- `--from YYYY-MM-DD` — start from date, end at today
- `--date YYYY-MM-DD` — pretend today is this date, then apply default rule

### Chinese public holidays

`scripts/compute_range.py` uses the `chinesecalendar` Python library (loaded via `uv --with chinesecalendar`) to classify each day as workday / holiday. The orchestrator always emits a `range.breakdown` containing `{date, weekday, workday, holiday}` for every day, plus aggregated `workdays` / `holidays` counts. Use this data to:

- Annotate the report header (e.g. "本周 3 工作日、2 节假日")
- Decide whether the range is meaningful at all (if `workdays == 0`, ask the user whether they want the **previous** working week instead)

## Data Collection

### Step 1 — run the orchestrator

```bash
python skills/automation/working-summary/scripts/collect.py \
  [--config PATH] \
  [--from YYYY-MM-DD --to YYYY-MM-DD | --date YYYY-MM-DD]
```

Returns JSON to stdout:

```jsonc
{
  "range": { "start": "...", "end": "...", "workdays": N, "holidays": N, "breakdown": [...] },
  "config": { "author": "...", "orgs": [...], "repos": [...], "include_commits": true, "linear": {...}, "output": {...} },
  "github": {
    "owner/repo": {
      "prs_merged":  [...],  // reconstructed from commit (#NNN) refs → /repos/{r}/pulls/{n}
      "prs_open":    [...],  // /repos/{r}/pulls?state=open, filtered by author + updated window
      "commits":     [...],  // /repos/{r}/commits?author=&since=&until=
      "issues":      [...]   // /repos/{r}/issues?assignee=&since=, PRs filtered out
    }
  },
  "stats": {
    "prs_merged": 34,
    "by_type": { "feat": 14, "fix": 9, "refactor": 6, "chore": 5 },
    "by_repo": [
      { "repo": "lobehub/lobehub", "prs": 18, "by_type": { "feat": 8, "fix": 5 } }
    ]
  }
}
```

**Why REST instead of `gh search`** — the previous version used `gh search prs/issues` for org-wide queries. That index is unreliable: private orgs are unindexed entirely, and even public mono-repos return partial results (one test run showed 1/27 merged PRs hit). The current flow:

1. `GET /orgs/{org}/repos` — page through every repo (incl. private), then merge with explicit `repos`.
2. Per-repo `GET /repos/{r}/commits?author=...&since/until` — concurrent (16 workers). Commits filtered by GIT author + merge date window. Empty repos (HTTP 409) and archived repos (404) are silently skipped.
3. **Merged PRs are reconstructed** from commit message refs: every `(#NNN)` in a commit message becomes a `GET /repos/{r}/pulls/{n}` call. Because commit dates are merge dates, these PRs are guaranteed merged in window.
4. For "active" repos (had commits) plus explicit repos, fetch open PRs (`/pulls?state=open`) and assigned issues (`/issues`), filter by author + updatedAt client-side.

Set `github.include_commits: false` to skip steps 2-3 entirely (only open PRs / issues on the explicit repo list).

### Step 2 — Linear (optional, via `linear` CLI)

When `config.linear.team` is set, `collect.py` invokes `scripts/fetch_linear.py` which shells out to `linear api` (the GraphQL endpoint of [`@schpet/linear-cli`](https://github.com/schpet/linear-cli)). Requires `linear auth login` once.

1. Resolve `viewer.id` via `{ viewer { id } }`.
2. Resolve the **target cycle** for `linear.team` per `linear.cycle`:
   - `previous` — most recently completed cycle (`endsAt <= today`, max `endsAt`)
   - `current` — cycle whose `[startsAt, endsAt)` contains today
   - `auto` — cycle whose `[startsAt, endsAt]` overlaps the computed `range` (max overlap wins)
3. Query `issues(filter: { team, cycle, assignee = viewer })` with optional state filter from `linear.include_states`.
4. Each issue carries `attachments` — GitHub PR/commit URLs are exposed there, enabling PR ↔ issue linking without text matching.

The script returns `null` (silent) when:

- the `linear` binary is missing,
- the user is not authenticated,
- the cycle cannot be resolved.

In any of those cases, the report continues with GitHub-only output and **must note** that Linear was skipped.

In addition to the **report cycle** (resolved against the date range), the script also fetches the **active cycle** (the one containing today) and pulls only its `started` issues. For the typical "previous Mon-Sun" weekly report these are different cycles — the report cycle is the cycle that just ended, the active cycle is what the user is currently working on. When the two happen to be the same cycle, the in-progress slice is filtered from the already-fetched issues with no extra round-trip.

```jsonc
{
  "linear": {
    "team": "LOBE",
    "team_id": "...",          // Linear team UUID — used by create_linear_issue.py
    "done_state_id": "...",    // first workflow state with type=completed (typically "Done")
    "viewer_id": "...",
    "cycle": { "id": "...", "number": 9, "name": "...", "startsAt": "...", "endsAt": "...", "progress": 0.37 },
    "issues": [
      {
        "identifier": "LOBE-6603",
        "title": "...",
        "state": "Done",
        "stateType": "completed",
        "priority": 1,
        "priorityLabel": "Urgent",
        "labels": ["🐛 Bug", "Improvement"],
        "url": "https://linear.app/.../LOBE-6603",
        "completedAt": "...",
        "attachments": [
          { "url": "https://github.com/.../pull/13481", "title": "...", "sourceType": "github" }
        ]
      }
    ],
    "in_progress": {
      "cycle": { "number": 10, "name": "2026.04 W2", ... },
      "issues": [ /* same shape as above; only state.type == "started" */ ]
    }
  }
}
```

The report's "Linear cycle snapshot" section MUST surface `in_progress.issues` under a sub-heading like **"本周仍在进行（active cycle #N）"** so the user sees both retrospective Done items and forward-looking work in one place. Skip the sub-heading when `in_progress.issues` is empty.

### Step 3 — noise filter

The following never anchor a 要点 theme, and never justify one on their own:

- i18n / locale-only sync
- Submodule bumps, lockfile-only updates
- Formatting-only, single-line config tweaks
- Release PRs

They still increment `stats` and the repo table. They never anchor a 要点 theme and never become a digest bullet.

Substantive work (features, non-trivial fixes, infra, security) is what theme selection draws from.

## Report Synthesis

Synthesize markdown from the collected JSON.

### Language rule

The output language is controlled by `output.language` in config (default `zh-CN`). The rule is:

- **Translated to `output.language`** — readable descriptions, framing prose, headers you author yourself, callout text, follow-up notes.
- **Kept verbatim regardless of language** — fixed section labels (`In Progress`, `Features`, `Fixes`, `Refactor`, `Build / CI / Deps`, etc.), and **raw PR / issue / commit titles** (these are quoted verbatim for traceability — never translate them).

So even when `language: zh-CN`, a 本周要点 theme looks like:

```
**1. 首屏 boot −80%** — 27154 → 5425 render（zh-CN −86%）
`bindI18nStore: 'added'` 每个 namespace 整树重绘；首屏闭包 3.84MB → 2.26MB。涉及 5 个 PR。[#19120](https://…) · [#19033](https://…)
```

…and a 仓库汇总 bullet keeps the raw title verbatim:

```
- `⚡️ perf: make SPA startup demand-aware` [#17577](https://…)
```

The prose is 中文; the backtick-quoted raw titles and the link text stay English (or whatever the original PR author wrote).

The synthesized language applies to descriptions even when the **PR body** is in a different language — the description is _your_ paraphrase, written in `output.language`, distilled from the body.

### Sections

1. **Header** — period title, date range, workday/holiday count, repo count + activity totals. Copy `stats.by_type` into a **构成** line (`feat 14 · fix 9 · …`), canonical order, omit zero buckets. Skip the line when `stats.prs_merged == 0`. **Copy `stats`; do not recount.**

   Then a **仓库表** (markdown's stand-in for the HTML stacked bars). One row per `stats.by_repo` entry, same order. No mermaid, no Unicode `█`. Skip the table when `stats.prs_merged == 0`.

   ```
   | 仓库 | PR | 构成 |
   | --- | ---: | --- |
   | lobehub/lobehub | 36 | fix 13 · feat 7 · perf 6 · refactor 5 · chore 5 |
   ```

   `构成` cell: that row's `by_type`, canonical order, omit zeros. Copy the numbers.

2. **一、本周要点** (Highlights) — **the section the user actually reports from.** Everything else in the report exists to back this section up.

   Cluster the window's merged PRs and loose commits into **3–6 cross-repo themes**. A theme is a storyline several PRs advance together — an architecture migration and the defect class it exposed, one performance push landing across OSS + Cloud, a single capability shipped through three repos. It is emphatically **not** "the N most important PRs".

   Each theme is **exactly two lines**:

   ```
   **N. <consequence + number>** — <the metric>
   <one sentence of why>. 涉及 N 个 PR。[#a](url) · [#b](url)
   ```

   Line 1 is the user-visible consequence or measured number. Line 2 is the cause plus 2–5 key PR links. A third line is a failure. A paragraph theme is a failure.

   Rules:

   - Order by significance. Not chronology, not repo, not PR count.
   - Lead with the **user-visible consequence or the measured number**, not the refactor's name — "按发送没反应"、"冷启动 TTFB 1369ms"、"非英文系统首启显示英文" beat "重构了 router 层".
   - Synthesize from PR bodies (`prs_merged[].body` is collected for this). A theme that only restates PR titles has failed.
   - Each PR belongs to at most one theme. PRs that fit no theme simply do not appear here.
   - Do **not** pad to reach 6. Three real threads beat six manufactured ones. If a "theme" has one PR under it, it is not a theme.
   - Mention the theme's PR count when it is large ("涉及 5 个 PR") — that is the part that reads as a week's work.

3. **二、仓库汇总** (Per-Repo Digest) — **not a dump, not a second 要点.** Every merged PR and loose commit as a bullet is forbidden.

   Repos with `stats.by_repo[].prs >= 2` get their own heading, in `stats.by_repo` order:

   ```
   ### owner/repo *(18 PRs)*

   这周主要在收 SPA 冷启动，顺手修了非英文首启。

   - `fix: sidebar file highlight` [#18916](url)
   ```

   - `N` comes from `stats.by_repo[].prs`. Copy it.
   - One framing sentence in `output.language`, distilled from **PR bodies**. Do not restate 要点 prose.
   - Bullets are **incremental**: a PR already linked in 要点 does **not** appear here. Add at most 0–2 notable PRs that did not make a theme, chosen by reading `prs_merged[].body`. Zero bullets is correct when 要点 already covered the repo.
   - Title / commit message is not enough to choose a bullet. Noise (i18n / lockfile / formatting / Release PR) may increment `stats` but must not be a bullet.
   - Raw titles stay verbatim in backticks; link text is the PR number.

   Repos with `prs <= 1` (including loose-commit-only, `*(0 PRs)*`) fold into a single `### 其他` — no own heading:

   ```
   ### 其他

   - `owner/small` *(1 PR)* — 一句概括
   - `owner/push-only` *(0 PRs)* — 仅有 N 次直接 push：一句在干什么
   ```

   Loose commits are never listed (no SHA, no “and 12 other commits”).

   Hard bans: do not list every commit/PR “for traceability”; do not re-list 要点 PRs “as an index”; do not give a 1-PR repo its own `###`; do not treat a commit message as sufficient to judge importance.

4. **三、未合并 / 跟进** (Follow-ups) — closed-but-unmerged PRs needing reopen, open PRs, assigned issues still open, stale work, Linear issues without PRs.

5. **四、Linear cycle snapshot** — if Linear is configured and connected.

Use Obsidian callouts where appropriate:

- `> [!success]` — shipped highlights
- `> [!info]` — context / cycle snapshot
- `> [!warning]` — follow-up actions

### PR ↔ Linear linking heuristics

Match a merged PR to a Linear issue when:

- PR title or body contains the Linear issue identifier (e.g. `TEAM-123`)
- Branch name starts with the issue identifier
- An `attachments` entry on the Linear issue links to the PR URL

Flag any merged PR with **no** Linear match as an untracked item.

## Persistence Targets

When the user opts to persist (see **Output Flow** above), expand placeholders
from the computed range before constructing the filename:

- `{year}` / `{month}` — from `range.end`
- `{week}` — ISO week number of `range.end`
- `{start}` / `{end}` — `YYYY-MM-DD`
- `{ext}` — `md` or `html` depending on the chosen format

Targets:

- **markdown** → `{output.dir}/{filename}` (ext=`md`)
- **html temporary** → `$TMPDIR/working-summary-{start}-{end}.html` then `open` it
- **html permanent** (optional follow-up) → `{output.dir}/{filename}` (ext=`html`)
- **linear archive** → no file; see **Linear archive** below
- **lobehub** → no file; see **LobeHub publish** below

Never overwrite an existing file silently — if present, ask the user
(append, overwrite, or new suffix).

## Linear archive

When the user picks `linear` (or a composite), the skill must:

1. Write the final synthesized markdown to a working file (e.g. the same
   one used for `render_html.py`).
2. Invoke `scripts/create_linear_issue.py --json collected.json --md report.md`.
   The script reads `linear.team_id`, `linear.done_state_id`,
   `linear.viewer_id`, `linear.cycle.id`, `range.start`, `range.end` from
   the collected JSON and submits a single `issueCreate` mutation via
   `linear api`.
3. Title defaults to `Weekly Summary YYYY-Www (start ~ end)` using the ISO
   week of `range.end`. Override via `--title`.
4. The created issue lands in the **report cycle** (not the active cycle),
   assigned to the viewer, with state set to the team's first `completed`
   workflow state — typically "Done". Description is the markdown report
   verbatim.
5. On success the script prints `{identifier, url, state, cycle, assignee}`
   as JSON. Surface the identifier + URL back to the user.
6. Failure modes: missing `linear` CLI, missing fields in collected JSON
   (re-run `collect.py` against an updated `fetch_linear.py`), or GraphQL
   errors. The script exits non-zero with a stderr message — propagate it.
7. Use `--dry-run` to print the mutation input without sending; useful for
   debugging or when the user wants to confirm the destination before the
   write.

The `linear` choice never writes a file. Combine with `md` / `html` /
`both` to also persist locally.

## R2 publish

When the user picks `publish` (or a composite), the skill must:

1. Ensure an HTML report exists on disk. If the chosen composite did not
   already render HTML, run `render_html.py` into a tempfile under
   `$TMPDIR`. Reuse the same tempfile if `html` was also chosen.
2. Compute the R2 key from the same placeholder used for local persistence
   (`{year}-{month}-w{week}.html`).
3. Probe for conflict:
   `scripts/publish_r2.sh check <bucket> <key>` → exit 0 = exists, 1 = missing.
4. If the object exists, ask the user `[overwrite / suffix / skip]`. On
   `suffix`, append `-1`, `-2`, ... until a free key is found (re-running
   `check` between each attempt).
5. Upload:
   `scripts/publish_r2.sh put <bucket> <local-file> <key> <base-url>` →
   prints the public URL to stdout on success.
6. Surface the URL back to the user. Do NOT visit it from inside the skill
   — Cloudflare Access requires interactive email login.

The script invokes `wrangler r2 object put` with `--content-type
"text/html; charset=utf-8"`. The user must already be `wrangler login`-ed
to the Cloudflare account that owns the bucket; the skill never handles
credentials directly.

`output.publish` is required. If missing, the `publish` choice is hidden
from the prompt and any composite containing `publish` is rejected with a
clear message.

The hosting Worker code itself lives under `host/` (see `host/README.md`)
and is deployed independently via `wrangler deploy`. The skill never
redeploys the Worker — new reports are just new objects in the bucket and
become visible in the index on the next page load.

## LobeHub publish

When the user picks `lobehub` (or a composite), the skill must:

1. Write the final synthesized markdown to a working file.
2. Expand `output.lobehub.title` and `output.lobehub.folder` with the same
   placeholders used for filenames, plus `{author}` (the report author's
   display name — ask once if the config does not pin it in the title).
3. Run:

   ```bash
   scripts/publish_lobehub.py \
     --workspace <output.lobehub.workspace_id> \
     --slug <output.lobehub.slug> \
     --kb <output.lobehub.kb> \
     --folder "2026.08" \
     --title "Innei 周报 — 2026-W35（08-24–08-30）" \
     --md report.md
   ```

4. The script creates the folder on demand, refuses by default when a
   document with the same title already exists (exit 1), and prints
   `{id, title, parent, url}` as JSON on success. Surface the URL.
5. On a duplicate, ask the user: re-run with `--on-duplicate replace`
   (creates the new doc, then removes the old one) or `allow` (keeps both).
   Never pass `replace` without asking.
6. `--dry-run` prints the resolved kb / folder / parent / duplicate list
   without writing anything. Use it when the user wants to confirm the
   destination first.

`output.lobehub.workspace_id` must be the workspace **ID**, not the slug.
The `X-Workspace-Id` header is not validated server-side: a slug is
accepted, silently ignored, and every call falls back to personal scope —
so a wrong value looks like "the KB does not exist". `lh whoami` is no help
either — its `Scope:` line just echoes whatever was passed in.

The CLI exposes no `workspace list` command, and the app URL carries the
slug, not the ID. To rediscover the ID, capture the session token off a
logging proxy and call the tRPC route directly:

```bash
cat > proxy.mjs <<'JS'
import http from 'node:http'; import https from 'node:https'
http.createServer((req, res) => {
  console.error(req.headers['oidc-auth'])
  const p = https.request('https://app.lobehub.com' + req.url,
    { method: req.method, headers: { ...req.headers, host: 'app.lobehub.com' } },
    r => { res.writeHead(r.statusCode, r.headers); r.pipe(res) })
  req.pipe(p)
}).listen(8899)
JS
node proxy.mjs 2>token.log &
LOBEHUB_SERVER=http://127.0.0.1:8899 lh whoami >/dev/null
curl -s -H "Oidc-Auth: $(head -1 token.log)" \
  'https://app.lobehub.com/trpc/lambda/workspace.list?input=%7B%7D'
```

The response lists `{id, slug, name}` per workspace. Store the `id` in
config; do not repeat this dance per run.

## HTML Rendering

HTML is produced **deterministically** by `scripts/render_html.py`, not by
the LLM. This keeps token cost low and the visual theme consistent across
runs.

```bash
scripts/render_html.py \
  --markdown <md-file | -> \
  [--json collected.json] \
  [--lang zh-CN] \
  [--title "2026-W14"] \
  [--user innei] [--host reports] \
  -o <out.html | ->
```

**Inputs**

- `--markdown` (required) — the synthesized markdown report. Pass `-` to
  read from stdin. The script extracts `<h1>` as report title and parses
  the header paragraph (`**周期**` / `**作者**` / `**仓库**`) plus the
  leading blockquote for the summary callout.
- `--json` (optional) — `collect.py` JSON output. When provided, meta grid
  and type-mix charts are computed from `stats` (or re-derived from
  `github.prs_merged` via `pr_stats.build_stats` if `stats` is missing).
  Prefer `--json` when available. No JSON / 0 merged PRs → no chart appendix.

**What the script does**

1. `markdown-it-py` converts the report body to HTML fragment.
2. BeautifulSoup post-process passes:
   - extract h1 → typewriter header
   - peel off header metadata `<p>` + summary `<blockquote>` and render
     them as a meta-grid and a shipped callout
   - drop stray top-level `<hr>`
   - convert `> [!kind]` blockquotes into `.callout.<kind>` divs
   - wrap each repo `<h3>` inside the「仓库汇总」section in `<details>`
     (first open) with a `copy` button; the `*(N PRs)*` suffix
     becomes the right-aligned count badge
   - wrap each `<h2>` + its following siblings in `<section id=slug>`
   - scan every `<li>` for a conventional-commit prefix in any `<code>`
     descendant (`feat|fix|refactor|perf|build|ci|chore|docs|test|style|revert`)
     and prepend a colored `.tag` span
   - assign slug ids to section h3 headings so the sidebar TOC can
     link to sub-items
3. The shell (CSS + HTML + JS) lives in
   `scripts/templates/report.html` and is filled via `string.Template`.
   It honors `prefers-color-scheme` (dark by default, light on light
   systems) and includes a dedicated `@media print` theme that switches
   to black-on-white, hides the sidebar/toolbar, expands every `<details>`,
   and appends `(url)` to anchors for print traceability.
4. Output is a single self-contained HTML file — no external assets.

**Degradation**: if the markdown lacks the expected header paragraphs or
the「仓库汇总」section, the script still renders a plain themed page
without the meta grid or collapsible repo blocks. It never raises.

## After the report

Offer — and **wait for explicit confirmation** — before any write action:

- Close Linear issues whose PRs were merged in the window
- Create Linear issues for substantive untracked PRs
- Create GitHub issues for trivial but recurring follow-ups

## Sub-scripts (debugging)

- `scripts/compute_range.py --classify` — print the computed range and per-day holiday breakdown.
- `scripts/compute_range.py --date 2026-04-06 --classify` — simulate running on a specific date.
- `scripts/fetch_github.py --author innei --repo mx-space/core --from 2026-03-30 --to 2026-04-05` — single repo.
- `scripts/fetch_github.py --author innei --org lobehub --org lobehub-biz --from 2026-03-30 --to 2026-04-05` — expand both orgs, full pipeline.
- `scripts/fetch_github.py ... --no-commits` — skip commit + merged-PR reconstruction; only open PRs / issues on explicit repos.
- `scripts/fetch_linear.py --team LOBE --cycle auto --from 2026-03-30 --to 2026-04-05` — Linear-only fetch, useful for debugging cycle resolution.
- `scripts/render_html.py --markdown report.md -o /tmp/out.html` — render a standalone markdown file into themed HTML. Add `--json collected.json` to enrich the meta grid and stats.
- `scripts/create_linear_issue.py --json collected.json --md report.md --dry-run` — print the `issueCreate` mutation input without sending. Drop `--dry-run` to actually create the issue in the report cycle.
- `scripts/publish_r2.sh check <bucket> <key>` — probe whether a key already exists in the R2 bucket (exit 0 = yes, 1 = no, 2 = wrangler/auth error).
- `scripts/publish_r2.sh put <bucket> <local-file> <key> <base-url>` — upload the local file as `<key>` with `text/html` content type, print the resulting public URL.
- `scripts/publish_lobehub.py --workspace <id> --kb <kb-id> --title T --md report.md --dry-run` — resolve the KB / folder / duplicates without writing. Drop `--dry-run` to create the document.

## Dependencies

- `gh` CLI, authenticated (`gh auth status`)
- `uv` (for script shebangs — `collect.py` pulls `pyyaml` + `chinesecalendar`, `render_html.py` pulls `markdown-it-py` + `beautifulsoup4` on first run)
- `linear` CLI, authenticated (`linear auth login`) — only required if `config.linear` is set
- `lh` CLI (`@lobehub/cli`), logged in (`lh login`) — only required if `output.lobehub` is set
- Make scripts executable once: `chmod +x skills/automation/working-summary/scripts/*.py`

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
| Sun      | `[this Mon, today]` — the week ends today, so it *is* 上周 |

Explicit overrides:

- `--from YYYY-MM-DD --to YYYY-MM-DD` — hard range
- `--from YYYY-MM-DD` — start from date, end at today
- `--date YYYY-MM-DD` — pretend today is this date, then apply default rule

### Chinese public holidays and weekends

`scripts/compute_range.py` uses the `chinesecalendar` Python library (loaded via `uv --with chinesecalendar`) to classify each day as workday / holiday. Weekends are classified separately and unconditionally: Saturday/Sunday stay `weekend: true` even when the holiday library marks them as a make-up workday (调休).

The orchestrator always emits a `range.breakdown` containing `{date, weekday, weekend, workday, holiday}` for every day, plus aggregated `workdays` / `holidays` / `weekends` / `weekend_dates` / `makeup_workdays` counts. `stats.weekend` adds `{prs_merged, commits, dates}` for the weekend days. Use this data to:

- Annotate the report header with all three buckets — workdays **and weekends** and holidays, never as "5 个工作日、0 节假日" with the weekend silently missing
- Name the weekend dates explicitly in a `**周末**` header line and report weekend output separately (see **Header**)
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
  "range": { "start": "...", "end": "...", "days": 7, "workdays": N, "holidays": N, "weekends": N, "weekend_dates": ["..."], "makeup_workdays": N, "breakdown": [...] },
  "config": { "author": "...", "orgs": [...], "repos": [...], "include_commits": true, "linear": {...}, "output": {...} },
  "github": {
    "owner/repo": {
      "prs_merged":  [...],  // reconstructed from commit (#NNN) refs → /repos/{r}/pulls/{n}
      "prs_open":    [...],  // /repos/{r}/pulls?state=open, filtered by author + updated window
      "commits":     [...],  // /repos/{r}/commits?author=&since=&until=
      "issues":      [...]   // /repos/{r}/issues?assignee=&since=, PRs filtered out
    }
  },
  "evidence": [              // Step 4 — ledger entries dated inside the window
    { "date": "2026-11-02", "title": "...", "detail": "...", "source": "...", "image": "..." }
  ],
  "stats": {
    "prs_merged": 34,
    "by_type": { "feat": 14, "fix": 9, "refactor": 6, "chore": 5 },
    "by_repo": [
      { "repo": "lobehub/lobehub", "prs": 18, "by_type": { "feat": 8, "fix": 5 } }
    ],
    "weekend": { "prs_merged": 3, "commits": 30, "dates": ["2026-10-17", "2026-10-18"] }
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

`in_progress.issues` is the forward-looking half. It never becomes a list: surface only the items that are real work in flight, as 卡点 entries; alert-aggregation issues (hourly Vercel 5xx/404 buckets) collapse into one line. Skip it when `in_progress.issues` is empty.

### Step 3 — noise filter

The following never anchor a theme, and never justify one on their own:

- i18n / locale-only sync
- Submodule bumps, lockfile-only updates
- Formatting-only, single-line config tweaks
- Release PRs

They still increment `stats` and appear in 附录. They never anchor a theme and never carry a 判断/代价 line.

Substantive work (features, non-trivial fixes, infra, security) is what theme selection draws from.

### Step 4 — the evidence ledger

Numbers that GitHub and Linear cannot produce — a CI run comparison, a
Cloudflare zone export, a billing screenshot — arrive out of band, often after
the window closed. They go into `~/.config/working-summary/evidence.jsonl`
with their images beside them, and `collect.py` returns only the entries dated
inside the report window as `evidence`:

```jsonc
{"date": "2026-11-02", "title": "type-check 换 tsrs：快的快、慢的慢",
 "detail": "cloud 冷 Bun 122–171s → ~33s；lobe-chat 冷 11.6s → 35–50s",
 "source": "screenshot 2026-11-02 01:59",
 "image": "~/.config/working-summary/evidence/2026-11-02-tsrs-typecheck.jpg"}
```

```bash
scripts/evidence.py --add --date 2026-11-02 --title "…" --detail "…" \
                    --source "screenshot" --image ~/Desktop/shot.png
scripts/evidence.py --list
```

- A measurement taken after the window belongs to the **next** report. Never
  pull a later entry into an earlier range to make a theme look stronger — the
  window is the contract with the reader.
- Record it the moment it arrives, not when the report is written: this is the
  only place a screenshot's numbers survive.
- `detail` carries each scenario with its own before/after. A single "快了
  X 倍" that hides a regression is worse than no number.

## Report Synthesis

Synthesize markdown from the collected JSON.

### Language rule

The output language is controlled by `output.language` in config (default `zh-CN`). The rule is:

- **Translated to `output.language`** — readable descriptions, framing prose, headers you author yourself, callout text, follow-up notes.
- **Kept verbatim regardless of language** — fixed section labels (`In Progress`, `Features`, `Fixes`, `Refactor`, `Build / CI / Deps`, etc.), and **raw PR / issue / commit titles** (these are quoted verbatim for traceability — never translate them).

So even when `language: zh-CN`, a theme reads like:

```
## 01 页面协作：人和 Agent 编辑同一份 Y.Doc

**判断** — 页面一直是单人加锁编辑，Agent 改页面只能整篇覆盖。
**做了什么** — agent-gateway 新增 `DocumentRoomDO`，每页一个 Yjs room，约 2s 防抖投影回 `documents`。
**结果** — 灰度可控；打开页面先显示已存副本而不是白屏。尚未全量。
**代价** — room 状态单值存 SQLite，单页上限约 2 MB，要拆。

证据：#20322 · #22 · #21924
```

…and an appendix bullet keeps the raw PR title verbatim, in the appendix only:

```
- `⚡️ perf: make SPA startup demand-aware` [#17577](https://…)
```

The prose is 中文; the backtick-quoted raw titles and the link text stay English (or whatever the original PR author wrote).

The synthesized language applies to descriptions even when the **PR body** is in a different language — the description is _your_ paraphrase, written in `output.language`, distilled from the body.

### Shape

One markdown file is the source. Two projections come out of it, and they never disagree:

- **editor summary** — `scripts/render_md.py` cuts everything from `## 附录` down. This is what a KB document holds.
- **HTML** — `scripts/render_html.py` renders the whole file and folds `## 附录` into a collapsed `<details>`.

The report is **display only**. It exists to be read: no comment widgets, no anchor chips for readers to cite, no interactive state. Do not add affordances a reader is expected to click.

### Sections

1. **Header** — the metadata lines the HTML meta grid parses, and nothing else:

   ```markdown
   **周期**：2026-10-12 ~ 2026-10-18
   **周末**：10-17 Sat · 10-18 Sun — 合入 3 个 PR、30 次提交
   **作者**：<name>
   ```

   - `weekends`, `weekend_dates` and `makeup_workdays` come from `range`; `stats.weekend` supplies `prs_merged` / `commits`. Copy them, never recount or hardcode.
   - The `**周末**` line is required even with zero activity: `**周末**：10-17 Sat · 10-18 Sun — 无活动`. When `makeup_workdays > 0`, append `（其中 N 天调休上班）` to the 周期 line; those days stay listed under 周末.
   - A PR merged or a substantive commit pushed on Sat/Sun must surface in a theme or in 卡点. The 周末 counts must equal `stats.weekend`.
   - 构成 / 仓库表 / PR 清单 belong to `## 附录` (item 5). Never in the header.

2. **Lead** — two short paragraphs, no heading:

   ```markdown
   这周只做成一件事：<the week's judgement>。

   <supporting cast, one line>。<N> 仓 <M> 个 PR（上周 <K>）。状态：<thread> <state> · …
   ```

   - The first sentence is a **judgement**, not an inventory: "页面从一个人编辑变成人和 Agent 同房间编辑", not "完成了页面协作功能".
   - The state list may only use `灰度中` / `已上线` / `含一次回滚` / `未合并` / `已回滚`. Every thread named in the lead appears there with one of them.

3. **Themes** — 3 to 5, numbered `## 01` … One theme per separately shippable change, or per measured number worth reporting. Each theme is exactly four labelled lines plus one evidence line:

   ```markdown
   ## 01 <what a user can now do that they could not before>

   **判断** — <why this exists: the constraint or defect that forced it.>
   **做了什么** — <the mechanism in one sentence, naming the real components.>
   **结果** — <what now works, and its state: 灰度 / 已上线 / 未全量.>
   **代价** — <the cost paid: a cap, an incident, a rollback, a rule switched off.>

   证据：#NNN · #NNN · owner/repo@sha7
   ```

   - **Eligibility is substance, not PR count.** Work landing as direct pushes (the `lobehub-biz` repos do this) or as a single merged PR anchors a theme when it shipped something usable or bought a judgment worth having. `stats.by_repo[]` now carries `commits` for every active repo, and push-only repos carry `push_only: true` plus `top_commits` (4 newest, `{sha, subject}`) — read them before deciding nothing happened. Cite pushes as `owner/repo@sha7`.
   - A theme title names the capability or the judgment, never the tool: `迁移从「看起来一样」变成「0 差异」` — not `验证器开发`.
   - `结果` must answer "shipped or not". A theme that never states its state is unfinished.
   - **A measured number carries its scope.** Every figure in `结果` names where it came from (run id, usage snapshot, date) and every figure that is partial says so in `代价` — one day of billing, a team-level number that includes other projects, a 17-hour window. A number whose caveat is dropped is worse than no number.
   - When a number argues *against* the work — CI got faster but the end-to-end build did not — say that in `结果`, not in a footnote. It is the most credible line in the report.
   - **A migration that helps one scenario and hurts another reports both.** `cloud 冷 122–171s → 33s，lobe-chat 冷 11.6s → 35–50s` is the honest line; "type-check 快 4 倍" is a lie with a number attached, and the title may not claim a speedup the numbers do not hold across scenarios.
   - `代价` must be a real, checkable cost. If there genuinely is none, omit the line — never invent one.
   - Order by significance of the change to the product, not by PR count or repo.
   - Each PR belongs to at most one theme. One PR with no storyline behind it is an appendix entry, not a theme.
   - Fold work that serves one outcome into one theme (a lint migration, a style-parity verifier and a font re-slice are all "making migrations judgeable") instead of giving each its own.
   - Synthesize from `prs_merged[].body` and, for push-only repos, the commit messages. A theme that only restates titles has failed.
   - Noise (i18n / lockfile / formatting / release PR) never anchors a theme. It still counts in `stats` and in the appendix.

4. **卡点** — `## 卡点`, 2–4 bullets, each naming its blocking object (issue id, PR number, repo, person). There is no `下周计划` section: the blockers are the plan. Delete the section when nothing blocks.

   **Shipped work never appears here.** A merged verifier that has not yet reached its gate is a `代价` line inside its theme, not a blocker; 卡点 answers "what stops the next step", and only that.

5. **附录** — `## 附录`, folded in HTML and dropped from the editor summary:

   - `### 仓库分布` — the `stats.by_repo` table, with both counts: `| 仓库 | PR | 提交 | 构成 |`. A repo with `0` PRs and 23 commits is visible there, not hidden.
   - `### 合入 PR 清单` — every merged PR number grouped by repo.
   - `### 直接 push` — one line per push-only repo: commit count, then its 2–4 substantive commits as `subject（sha7）`. This is the only place that work survives when it is not a theme.
   - `### Linear cycle snapshot` — cycle, progress, and only the issues whose state moved (Done / In Review) plus one line for the rest. Never a raw issue dump.

   The appendix carries every PR number and every push-only repo, which is exactly why the narrative may stay short.

### 字数预算

| projection | what it counts | budget |
| --- | --- | --- |
| each theme | one `##` section | ≤ 750 字 |
| narrative | header + lead + themes + 卡点, i.e. everything the editor gets | ≤ 4000 字 |
| full markdown | narrative + appendix | ≤ 6000 字 |

A theme carrying measured numbers runs to the top of its range — that is the one place extra words buy credibility. The budget is per unit, not a total to fill: over it means the theme is two themes, the detail belongs in `代价`, or it is not a theme at all.

### Callouts

Use Obsidian callouts sparingly; `render_html.py` turns them into styled blocks:

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

## LobeHub artifact hosting (alternative to R2)

`@lobehub/cli` ≥ 0.0.72 can host the rendered page itself:

```bash
lh artifact publish /abs/path/report.html --root /abs/dir --type html \
  --title "Innei 周报 — 2026-W45" --slug 2026-w45 --json
# {"publicUrl": "https://2026-w45-xxxx.lobe.page",
#  "shareUrl": "https://app.lobehub.com/share/artifact/dpEMSEdk", ...}
```

- `--root` must contain the file: a path under `/tmp` resolves to
  `/private/tmp` on macOS and is rejected without it.
- Re-publishing updates the same artifact (`releaseCount` grows) and keeps the
  URL; `--new` forks a separate deployment.
- **`publicUrl` is world-readable.** It answers `200` to an anonymous request,
  while the R2 host answers `302` into Cloudflare Access. A weekly report
  carries internal PR numbers, issue ids and billing figures — publishing it
  there is a decision for the human partner, never a convenience. Say so
  before the first publish, and there is no CLI to unpublish it again.
- `--type canvas` is **not** a drop-in for this page: a canvas renders inside
  LobeHub from `<lobe-*>` components, rejects unknown tags, forbids network
  access and styling `html`/`body`, and takes colours from attributes. Our
  report is a standalone page with its own CSS, `<figure>` and `<details>`;
  a canvas needs its own renderer, not a re-publish.

## LobeHub publish

When the user picks `lobehub` (or a composite), the skill must:

1. Project the full report onto the editor summary — the KB document gets
   the narrative, not the appendix, and gets the public HTML link:

   ```bash
   scripts/render_md.py --md report.md \
     --title "Innei 周报 — 2026-W45（2026-10-26–2026-11-01）" \
     --url https://reports.innei.dev/2026-11-w45.html \
     --upload-images -o summary.md
   ```

   `--upload-images` sends each figure through `lh file upload` (needs
   `@lobehub/cli` ≥ 0.0.72) and rewrites it to `https://app.lobehub.com/f/…`,
   which the document can render. Uploads are cached by file path + size +
   mtime in `~/.config/working-summary/image-cache.json`, so re-running never
   duplicates a file. Drop the flag and every figure is removed instead.
   Skip `--url` when this run does not publish HTML; the summary still
   stands on its own.
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
     --md summary.md
   ```

4. The script creates the folder on demand, refuses by default when a
   document with the same title already exists (exit 1), and prints
   `{id, title, parent, url}` as JSON on success. Surface the URL.
5. On a duplicate, ask the user: re-run with `--on-duplicate replace`
   (creates the new doc, then removes the old one **and deletes its orphaned
   file entry**, which `kb remove-files` leaves behind) or `allow` (keeps
   both). Never pass `replace` without asking. Deleting the file needs
   `lh file delete` (≥ 0.0.72); on an older CLI the orphan is kept and
   reported, and `lh file list` will show the pile.
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
  the header paragraphs (`**周期**` / `**周末**` / `**作者**` / `**仓库**`)
  plus the leading blockquote for the summary callout. The weekend line
  feeds a dedicated meta-grid cell (weekend days + weekend PR/commit counts).
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
   - inline local `<img>` sources as data URIs and wrap each in a
     `<figure>` with the alt text as `<figcaption>`
   - fold the `附录` section into one collapsed `<details class="appendix">`,
     so the narrative is what the reader scrolls and the repo table / PR
     list / Linear snapshot sit behind one click
   - (legacy) wrap each repo `<h3>` inside a「仓库汇总」section in its own
     `<details>` with a `copy` button; the current shape has no such heading
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

**Evidence screenshots.** Place a figure right after the theme's 证据 line, as `![<the claim it proves, with the numbers>](ci-lint.jpg)`, with the file beside the markdown. `render_html.py` inlines it as a data URI; `render_md.py --upload-images` uploads it with `lh file upload` so the editor copy can show it too. Rules:

- The number must stand in text (`结果`) on its own — the figure is support, not the claim, and a reader who sees neither copy must still get the point.
- The caption states what the figure proves, not what it is: `HTML 命中率 4% → 45.9%，回源 344 万/天 → 约 220 万/天` — never `截图 1`.
- Compress before adding: ≤ 1400 px wide, JPEG ~80, so the self-contained file stays under a megabyte.
- A figure whose numbers are not also in `结果` is decoration; delete it.

**Degradation**: if the markdown lacks the expected header paragraphs or
an `附录` section, the script still renders a plain themed page without
the meta grid or the collapsed appendix. It never raises.

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
- `scripts/render_md.py --md report.md --title T --url U -o summary.md` — project the full report onto the editor summary (drops `## 附录` and every evidence figure, swaps the H1, appends the full-report link). This is what a KB document receives.
- `scripts/evidence.py --list` — print the evidence ledger; `--add --date D --title T --detail D --source S [--image path]` records one measurement and copies its screenshot next to the ledger.
- `scripts/create_linear_issue.py --json collected.json --md report.md --dry-run` — print the `issueCreate` mutation input without sending. Drop `--dry-run` to actually create the issue in the report cycle.
- `scripts/publish_r2.sh check <bucket> <key>` — probe whether a key already exists in the R2 bucket (exit 0 = yes, 1 = no, 2 = wrangler/auth error).
- `scripts/publish_r2.sh put <bucket> <local-file> <key> <base-url>` — upload the local file as `<key>` with `text/html` content type, print the resulting public URL.
- `scripts/publish_lobehub.py --workspace <id> --kb <kb-id> --title T --md report.md --dry-run` — resolve the KB / folder / duplicates without writing. Drop `--dry-run` to create the document.

## Dependencies

- `gh` CLI, authenticated (`gh auth status`)
- `uv` (for script shebangs — `collect.py` pulls `pyyaml` + `chinesecalendar`, `render_html.py` pulls `markdown-it-py` + `beautifulsoup4` on first run)
- `linear` CLI, authenticated (`linear auth login`) — only required if `config.linear` is set
- `lh` CLI (`@lobehub/cli`), logged in (`lh login`) — only required if `output.lobehub` is set. Needs **≥ 0.0.72** for `lh file upload`, which carries figures into the document; older builds silently fail the `--upload-images` step. `pnpm add -g @lobehub/cli@latest` may resolve one release behind (pnpm 12's `minimumReleaseAge`), so check `lh --version` after updating.
- Make scripts executable once: `chmod +x skills/automation/working-summary/scripts/*.py`

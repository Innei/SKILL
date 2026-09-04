# Working Summary — Digest + HTML Type Charts

**Date:** 2026-09-05
**Owner:** Innei
**Status:** Spec — awaiting implementation
**Skill:** `skills/automation/working-summary`

## 1. Purpose

The weekly report currently dumps every merged PR and loose commit under
「仓库汇总」. That dump is not read. Replace it with a per-repo digest
whose notable items are chosen from PR bodies, and replace the HTML
ASCII activity bars with CSS charts of merged-PR type mix.

Markdown (Obsidian / Linear / LobeHub) and HTML share the same digest.
HTML additionally renders an appendix of charts from structured stats.

## 2. Locked decisions

| Item | Choice |
| --- | --- |
| Commit / PR dump | Gone in every format. No collapsed appendix of the full list. |
| Per-repo section | Digest: one framing sentence + `*(N PRs)*` + at most 2–3 notable PRs. |
| Importance | Read `prs_merged[].body`. Title / commit message is not enough. |
| HTML reading order | Unchanged: 要点 → digest → 跟进. Charts are an appendix, not a dashboard. |
| Charts | Overall type pills + per-repo stacked bars. No daily-rhythm chart. No single-color bars. |
| Chart unit | Merged PRs. Loose commits never enter the charts. |
| Numbers | `collect.py` emits `stats`. The LLM copies them. The renderer draws from the same object. The LLM does not recount. |
| Chart stack | Absolute width (longest bar = repo with the most merged PRs), not 100% stacked. |
| Heading suffix | `### owner/repo *(18 PRs)*`. Type mix does not go in `<em>` (badge would overflow). |
| Chart library | None. Pure CSS. Report stays a single HTML file. |

## 3. Report shape (markdown)

The LLM still produces only markdown. Section order is unchanged.

### 3.1 Header

Existing period / workday / repo / PR totals stay. Add one line copied
from `stats.by_type`, keys in canonical order, zero buckets omitted:

```
**构成** feat 14 · fix 9 · refactor 6 · chore 5
```

If `stats.prs_merged == 0`, omit the 构成 line.

Then a repo table (markdown stand-in for the HTML stacked bars), one
row per `stats.by_repo` entry, same order. No mermaid, no Unicode `█`.
Omit the table when `stats.prs_merged == 0`.

```
| 仓库 | PR | 构成 |
| --- | ---: | --- |
| lobehub/lobehub | 36 | fix 13 · feat 7 · perf 6 |
```

### 3.2 一、本周要点

Cluster from PR bodies into 3–6 cross-repo themes. Each theme is
**exactly two lines**: line 1 = consequence + number; line 2 = one
sentence of why + 2–5 PR links. A third line or a paragraph theme
is a failure.

### 3.3 二、仓库汇总

Repos with `prs >= 2` get `### owner/repo *(N PRs)*` plus one framing
sentence. Bullets are incremental: a PR already linked in 要点 does
not appear. At most 0–2 body-chosen notable PRs that did not make a
theme. Zero bullets is correct.

Repos with `prs <= 1` (including loose-commit-only) fold into a
single `### 其他` — they do not get their own heading. No SHA lists.

Do not re-list 要点 PRs “as an index”. Do not give a 1-PR repo its
own `###`.

### 3.4 三、未合并 / 跟进 and 四、Linear

Unchanged.

## 4. Stats (single source of truth)

### 4.1 Shape

`collect.py` adds a sibling of `github` / `linear` / `range`:

```jsonc
"stats": {
  "prs_merged": 34,
  "by_type": { "feat": 14, "fix": 9, "refactor": 6, "chore": 5 },
  "by_repo": [
    {
      "repo": "lobehub/lobehub",
      "prs": 18,
      "by_type": { "feat": 8, "fix": 5, "refactor": 3, "chore": 2 }
    }
  ]
}
```

- `by_type` omits zero-count buckets.
- `by_repo` includes only repos with `prs > 0`, sorted by `prs`
  descending, then repo name ascending.
- Canonical key order (pills, stacks, markdown 构成 line):
  `feat`, `fix`, `refactor`, `perf`, `chore`, `docs`, `other`.

### 4.2 Classification

Input: `prs_merged[].title` (not commit messages).

1. Strip leading whitespace.
2. Strip a single leading pictograph / emoji token plus following
   whitespace (covers `⚡️ perf: …`).
3. Match case-insensitively:

   ```
   ^(feat|fix|refactor|perf|build|ci|chore|docs|test|style|revert)(?:\s*[\(:!]|$)
   ```

   This accepts `feat:`, `feat(scope):`, `feat!:`, `feat (scope):`.

4. Map prefix → bucket:

   | Prefix | Bucket |
   | --- | --- |
   | feat | feat |
   | fix | fix |
   | refactor | refactor |
   | perf | perf |
   | chore, build, ci, style, revert | chore |
   | docs, test | docs |
   | no match | other |

Implementation lives in one helper module, e.g.
`skills/automation/working-summary/scripts/pr_stats.py`, imported by
`collect.py` (always emit `stats`) and `render_html.py` (re-derive if
an older JSON lacks `stats`). Do not duplicate the mapping.

## 5. HTML appendix

### 5.1 Placement

`$stats` stays after `.content` in `templates/report.html`, same slot
as today’s ASCII bars. Not in the sidebar TOC. Section title:

```
附：活动构成
```

### 5.2 Contents

When `stats.prs_merged > 0`:

1. **Pills** — one pill per `stats.by_type` key in canonical order.
   Value is the count, label is the bucket name. Colors match the
   existing conventional-commit tag palette (feat / fix / refactor /
   perf / chore / docs; `other` uses `--border-strong`).
2. **Stacked bars** — one row per `stats.by_repo` entry. Columns:
   repo name (truncate with ellipsis), flex bar, PR count.
   Bar width = `prs / max(prs)` of the list. Inner segments are
   `by_type` counts in canonical order, widths proportional to that
   repo’s own `prs`. `title` attribute on each segment: `feat 8`.

When `stats` is missing and `--json` is missing, or
`stats.prs_merged == 0`: render nothing. Do **not** scrape markdown
for `*(N commits)*` and do **not** fall back to ASCII `█` bars.

### 5.3 Template / CSS

Replace `.stats .row .bar` (monospace block characters) with flex
segment bars (`.stack`, `.seg.feat`, …). Print theme keeps the
segments and the numeric column; no JavaScript chart library, no
CDN, no inline SVG required.

`wrap_repos_into_details` is unchanged: the `<em>` inside each repo
`h3` becomes the summary badge. Because the suffix is now
`*(18 PRs)*`, the badge reads `18 PRs`. Update
`REPO_STAT_MD_RE` only if it still has a caller; the markdown-scrape
stats path is deleted.

## 6. Skill instruction edits

In `SKILL.md`, replace the 「二、仓库汇总」 bullet-dump contract with
§3.3. Add:

- Header 构成 line from `stats.by_type` (§3.1).
- “Copy `stats`; do not recount.”
- “Read `prs_merged[].body` before choosing the 2–3 bullets.”
- Hard bans:
  - Do not list every commit / PR “for traceability”. The PR links
    in 要点 and digest are the index.
  - Do not list all items because “this repo only has a few”.
  - Do not treat a commit message or PR title as sufficient to
    judge importance.

HTML Rendering section: document the new appendix, the `stats`
input, and the removal of the ASCII heat bars. Collect JSON example
gains the `stats` object.

Do not change: 要点 clustering, follow-ups, Linear snapshot, output
flow (`md` / `html` / `linear` / `lobehub` / `publish`), GitHub fetch
strategy, `body` truncation at 1500 characters, host Worker / R2.

## 7. Degradation

| Case | Behavior |
| --- | --- |
| No `--json` | Themed HTML of the markdown digest; no chart appendix. |
| `stats` missing but `github` present | Renderer derives `stats` via `pr_stats.build_stats`. |
| `prs_merged == 0` | No appendix. Digest may say 本周无合入. Loose-commit repos get a one-liner, still no SHA list. |
| Repo is all noise | Counts still enter stats / bars. Digest has heading + framing, zero bullets. |
| Title has no conventional prefix | Bucket `other`. Omitted from pills / legend when count is 0. |
| LLM numbers disagree with `stats` | Charts follow JSON. Skill forbids hand-counting so this should be rare. |

## 8. Non-goals

- Daily-rhythm / heatmap chart.
- Lines-added, review-cycle, or any extra GitHub stats endpoints.
- Embedding SVG / HTML / mermaid in the markdown the LLM writes.
- Expanding `prs_merged[].body` past the current 1500-character cap.
- Changing Linear archive, LobeHub publish, or R2 publish.
- A dashboard-first HTML layout (要点 stays the first section).

## 9. Files

| File | Change |
| --- | --- |
| `skills/automation/working-summary/scripts/pr_stats.py` | New. `classify_title`, `build_stats`. Stdlib only. |
| `skills/automation/working-summary/scripts/collect.py` | Attach `stats` to the JSON payload. |
| `skills/automation/working-summary/scripts/render_html.py` | Delete ASCII `render_stats` / markdown scrape. Draw pills + stacks from `stats`. |
| `skills/automation/working-summary/scripts/templates/report.html` | CSS for pills and stacked bars. Drop `.bar { letter-spacing }` ASCII styling. |
| `skills/automation/working-summary/SKILL.md` | Digest contract, 构成 line, stats, chart appendix, hard bans. |

No config.yaml changes. No host/ Worker changes.

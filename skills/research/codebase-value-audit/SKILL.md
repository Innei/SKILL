---
name: codebase-value-audit
description: >
  Use when asked whether a codebase's size is justified — "is 800k lines
  reasonable?", "audit our LOC", "are we bloated?", "值不值" — or when a
  LOC number is being used in an argument and nobody agrees what it
  measures. Produces a defensible per-sub-product accounting: strict line
  counts, a product-surface inventory, every line attributed to exactly
  one sub-product, and a worth verdict per block.
metadata:
  author: innei
  version: "1.0.0"
---

# codebase-value-audit

Turns "our repo is N lines, is that bad?" from a vibes debate into an
audit. The core move: a raw LOC number is meaningless until (a) the
measurement lens is pinned, (b) the product surface it bought is
inventoried, and (c) every line is attributed to one sub-product and
judged against what a standalone alternative would cost. The output is a
report where the verdict is per-block, not global — because the honest
answer is always "these 4 blocks are gold, these 4 deserve a discount."

## When to use

- Someone quotes a repo-wide LOC figure and asks if it's reasonable.
- Two people quote different LOC figures for the same repo and both are
  "right" (different lenses) — reconcile before arguing.
- Deciding where to cut: which subsystems dilute maintenance attention.

Not for: per-PR review, performance work, or dead-code sweeps alone
(knip/depcheck do that); this skill tells you *which blocks* deserve a
sweep.

## Inputs

- Repo root (git-tracked; works on monorepos).
- Optional: the number the requester believes ("we have 800k lines") —
  you must reconcile your count with theirs, not just assert your own.

## Files provided

- `scripts/count-pure-loc.sh` — strict source-file list + pure-code line
  count (3 lenses printed side by side).
- `scripts/bucketize.py` — attributes every file to the first matching
  bucket prefix and sums pure-code lines per bucket.

## Workflow

```text
[1] Pin the lens        3 counts: tracked-total / non-test / pure-code
[2] Inventory surface   parallel read-only agents, one per layer
[3] Attribute lines     bucketize.py: every line -> exactly one bucket
[4] Verdict per block   5 tiers, judged vs standalone-alternative cost
[5] Report              table + tier commentary + squeeze list
```

### [1] Pin the lens

Run `scripts/count-pure-loc.sh <repo-root>`. It prints three numbers:

1. **Tracked total** — all git-tracked TS/JS lines.
2. **Non-test physical** — minus tests/fixtures/e2e/scripts/mocks/
   stories/`.d.ts`.
3. **Pure code** — minus blank and comment-only lines.

These differ by 2x+ on a healthy repo (1.84M / 1.06M / 836k on the repo
this skill came from). When the requester's number differs from yours,
find which lens produces their number and say so explicitly — "your 800k
is lens 3, my 1.84M is lens 1, both correct" ends the argument; a
counter-assertion restarts it. All later steps use lens 3.

Also record: test:code ratio, and the largest data-as-code files (model
catalogs, locale tables, generated schemas) — they surface in step 4.

### [2] Inventory the product surface

Dispatch parallel read-only agents (Explore-type), one per layer, e.g.:
web client (routes/stores), server (routers/services/modules), desktop +
CLI, shared packages, and **docs/changelog** (the marketed feature list —
this one cross-checks the code-derived inventory against what the product
claims to ship; discrepancies are findings). Each agent returns a breadth
inventory: surfaces, one-liners, and a "full sub-products" shortlist —
no code review, no line counts.

Merge into a sub-product list (typically 15–25 entries). A sub-product is
something that could be a standalone company/tool: an eval platform, a
bot gateway, a document editor — not a feature like "dark mode".

### [3] Attribute every line

Copy `scripts/bucketize.py`, fill in the bucket → path-prefix table from
step 2's inventory, run it against the file list from step 1. Rules:

- First match wins; order buckets specific → general.
- One catch-all `infra` bucket with prefix `""` must be last; inspect its
  breakdown output — anything large hiding in it means a missing prefix.
- Cross-layer buckets are the point: one sub-product's bucket lists its
  frontend routes, its stores, its server services, its packages, and its
  CLI commands together.
- Expect ±10% precision; say so in the report. Sum must equal lens-3
  exactly (the script guarantees it — every file lands somewhere).

### [4] Verdict per block

Judge each sub-product's pure-code count against **what acquiring that
capability standalone would cost** (build or adopt), not against zero.
Five tiers:

| Tier | Criteria |
| --- | --- |
| core asset | Directly implements the product's differentiation; rebuilding or adopting would cost more; high leverage per line |
| market price | Table-stakes capability at a normal size for what it does |
| risk bet | Coherent and well-built, but its value depends on an unproven product thesis — flag "watch usage data" |
| discount | Competes head-on with dedicated products without an edge, or carries measurable waste (data-as-code, duplicated generations, copy-paste variants) |
| necessary cost | Settings, auth, base layer — nobody loves it, nothing works without it; judge only its share (base layer ≤ ~20% is healthy) |

Also assemble the **squeeze list**: concrete removable waste with line
estimates (coexisting old/new generations of a subsystem, overlapping
sibling services, data-as-code to externalize, convention violations,
unused i18n keys, stale packages). This is the actionable output.

### [5] Report

Lead with the global verdict and its split (e.g. "70% worth it / 13%
core / 18% discounted / 8–10% pure squeeze"). Then: lens reconciliation,
the ranked table (lines, share, verdict chip), tier commentary, squeeze
list, and a closing that answers the requester's actual question. If they
invoked an "AI era = fewer lines" thesis, engage it honestly: writing
cost fell, review/maintenance cost didn't; the metric that matters is
features per maintenance unit, and a ~1:1 test ratio is agent-era
scaffolding, not bloat.

## Common pitfalls

| Mistake | Fix |
| ------- | --- |
| `xargs wc -l \| tail -1` as the total | xargs batches into multiple `wc` calls; `tail -1` returns the last batch only. Sum with `awk '$2 != "total" {s+=$1}'`. |
| Counting merge-conflicted files 3x | `git ls-files` lists each unmerged file once per stage. Always `sort -u` the file list. |
| Arguing totals before pinning the lens | Both parties are usually right under different lenses. Reconcile first (step 1), then argue. |
| Running the counting script from the wrong cwd | Relative paths silently `open()`-fail and count 0 per file; totals become 0 without an error. Run from repo root; treat an all-zero bucket table as this bug, not as truth. |
| Treating a high test share as waste | ~1:1 test:code is the agent-era signature — it's the guardrail that lets agents keep writing. Cut discipline debt, not tests. |
| Data-as-code inflating "logic" | Model catalogs, locale tables, generated schemas are declarations. Measure them separately and recommend externalizing, or the density math is wrong. |
| Inventorying from code only | Also sweep docs/changelog/README with an agent — the marketed surface reveals sub-products the directory names hide, and mismatches are findings. |
| Catch-all bucket swallowing a subsystem | Order prefixes specific → general; always print the infra-bucket breakdown and chase anything unexpectedly large. |
| Verdict by size alone | A 10k-line block can be the highest-leverage asset (device gateway) and an 80k block half-waste (provider variants). Judge vs standalone-alternative cost. |
| Global verdict only | "Worth it overall" helps nobody decide anything. The per-block table with tiers is the deliverable; the global number is its summary row. |

## Verification

- [ ] The three lens counts are internally consistent (lens1 > lens2 >
      lens3) and the requester's number is mapped to one of them.
- [ ] Bucket sums equal the lens-3 total exactly; file list was
      `sort -u`'d.
- [ ] Infra/catch-all breakdown inspected; nothing unexplained > ~5%.
- [ ] Every sub-product has: lines, share, tier verdict, and a one-line
      justification referencing a standalone alternative or a concrete
      waste observation.
- [ ] Squeeze list items each carry a line estimate and a concrete fix.
- [ ] Report states the ±10% attribution caveat and any excluded scopes
      (e.g. closed-source stubs).

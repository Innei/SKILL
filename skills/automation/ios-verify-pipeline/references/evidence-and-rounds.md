# Evidence and rounds

Two consumers, one run. `results.json` gates a merge; the same artifacts become
a reviewable round when a delivery needs a person to accept or reject it. Do not
build a second capture pipeline for the second consumer.

## Evidence vocabulary

| Type | Use when |
| --- | --- |
| `screenshot` | A settled visual state or layout is the claim |
| `video` | A transition, animation, gesture, or multi-step flow is the claim |
| `dom_snapshot` | An accessibility tree (`axe describe-ui`) is stronger and smaller than pixels |
| `text` | Command output, probe JSON, logs, computed assertions |
| `markdown` | Reviewer-facing prose that should render as body text |
| `transcript` | A conversation or event stream is itself the proof |

Typing rules:

- The declared type is binding. A `video` claim cannot be satisfied by a final
  screenshot, and a `dom_snapshot` claim cannot be satisfied by prose.
- A type the case did not produce **invalidates the case** — never record it as
  a pass with a missing attachment. The coverage gate enforces this.
- Structured data uses a machine-readable artifact (JSON/CSV) plus a summary;
  do not screenshot a table you could export.

## Non-visual claims need two text artifacts

For anything asserted by a script — geometry, timing, protocol, persistence —
attach both:

1. a **reasoning** artifact: the claim, the setup, the method, the pass
   criteria, the interpretation, the limits;
2. an **execution** artifact: the exact command, the raw observed values, the
   exit status, and a short mapping back to the pass criteria.

An unexplained log dump is not evidence, and a prose claim with no raw values is
not evidence either.

## Status vocabulary

| Status | Use when |
| --- | --- |
| `pass` | The intended input was delivered, the expected state was observed, and the declared evidence exists |
| `fail` | The input was delivered and the product violated the expectation |
| `blocked` | The harness or environment could not execute or observe the condition |

Blocked carries an obligation: attach the attempted command, the UI hierarchy
before and after, and the missing capability. A blocked case is not a pass, and
a suite that quietly reclassifies failures as blocked is worse than no suite.

## Gates are not acceptance checks

The repo's own gates — unit tests, lint, type-check, build, coverage, "the suite
is green" — are never review items. State them as one line of narrative. The
subject of a review item is a behavior a person can accept or reject: what the
user sees, reads, or receives. "All 40 cases passed" is not such a behavior;
"the fused composer keeps one glass surface while sending" is.

Review items use a stable id and the plan/round vocabulary of the `acceptance`
skill; that skill owns the publishing contract.

## Rounds are immutable

One round = one timestamped directory, written once:

```text
rounds/<subject>/<YYYYMMDD-HHMMSS>-<slug>/
├── result.json        # plan[] + cases[] + summary; the page renders from this
├── report.md          # narrative tail only: scope, environment, gates, limits
└── assets/            # the evidence, grouped by case and appearance
```

- A published round is a permanent record. After a fix, export a **new** round;
  never overwrite one that a reviewer already judged.
- `report.md` never repeats the case table; it carries what the table cannot —
  the scope actually covered, the environment, the gates (as one line), and the
  limits.
- The round contains **only the behaviors this delivery claims**, not the whole
  case inventory. Exporting the suite makes the reviewer read the suite.

## Claims file

```json
[
  {
    "id": "glass-fusion",
    "behavior": "聊天输入框融合后共用玻璃交互",
    "category": "输入框交互",
    "cases": ["composer-glass"],
    "requiredEvidence": ["screenshot", "video", "dom_snapshot"]
  }
]
```

- `behavior` is one user-judgeable sentence. If it needs two sentences, it is
  two claims.
- `cases` lists the cases whose artifacts prove it — including each host and
  appearance the behavior claims to cover.
- `verifier` defaults to `program` when a case script asserted the behavior;
  set `agent` for a purely visual claim judged by looking.
- A claim may require **no more than its cases produce**: every type in
  `requiredEvidence` must appear in the union of its cases' declared evidence.
  Asking a review item for a type no case captures fails at export, which is the
  intended outcome — the claim was never measurable.

## Export workflow

```sh
verify export --config ... --output .artifacts/verify \
  --claims claims.json --title '融合 Plus 的玻璃交互' --requirement '<durable goal>' \
  --dir .artifacts/rounds/20260911-0121-glass
```

The exporter is deliberately strict, and each refusal is a real failure mode:

| Refusal | Because |
| --- | --- |
| A claimed case has no result | A claim that was never run must not read as covered |
| A required evidence type is missing | "Declared but not captured" is the most common silent gap |
| The target round directory is not empty | Rounds are immutable |
| A claim id repeats | Reviewers address items by id |

It prints the coverage line and the ingest command. Publishing is a separate,
explicit step — a regression run never publishes, and the exporter never talks
to the network.

## Reviewing

- Open every image and clip you cite. File existence and a caption are not
  visual verification.
- For a temporal claim, inspect the clip or the timestamped frames; sparse
  stills cannot establish the absence of a one-frame defect, and neither can a
  representative frame prove the intervening transition.
- Record provenance per artifact: device, revision, build, and whether the
  artifact came from the first run or a re-run after a repair. A screenshot
  whose revision is unknown proves nothing.
- A diff is not evidence of a pass or a failure; it only explains what changed.

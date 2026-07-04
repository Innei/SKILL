#!/usr/bin/env python3
"""Create a Linear issue archiving the working summary into the report cycle.

Reads the collected.json output of `collect.py` (for cycle ID + state ID +
team ID + viewer ID + date range) and a markdown report body, then opens a
new Linear issue in that cycle, assigned to the viewer, with state set to
the team's first `completed` workflow state (typically "Done").

Usage:
    create_linear_issue.py --json collected.json --md report.md \
        [--title "Weekly Summary 2026-W26"] \
        [--dry-run]

Both `--json` and `--md` accept `-` to read from stdin (but not both at the
same time).

Exits non-zero with a stderr message when:
- the `linear` CLI is missing
- the collected JSON has no `linear` block (Linear was not configured)
- the report cycle lacks a resolvable ID
- the team's Done state cannot be resolved

Output (success): single JSON object `{identifier, url, state, cycle}` to stdout.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path


ISSUE_CREATE_MUTATION = """
mutation IssueCreate($input: IssueCreateInput!) {
  issueCreate(input: $input) {
    success
    issue {
      id
      identifier
      title
      url
      state { name }
      cycle { number }
      assignee { displayName }
    }
  }
}
"""


def _die(msg: str, code: int = 2) -> None:
    print(f"create_linear_issue: {msg}", file=sys.stderr)
    sys.exit(code)


def _read(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).expanduser().read_text(encoding="utf-8")


def _iso_week(end_iso: str) -> tuple[int, int]:
    d = datetime.fromisoformat(end_iso).date()
    iso = d.isocalendar()
    return iso[0], iso[1]


def default_title(range_start: str, range_end: str) -> str:
    year, week = _iso_week(range_end)
    return f"Weekly Summary {year}-W{week:02d} ({range_start} ~ {range_end})"


def build_input(collected: dict, body: str, title: str | None) -> dict:
    linear = collected.get("linear") or {}
    if not linear:
        _die("collected JSON has no `linear` block — was Linear configured?")
    cycle = linear.get("cycle") or {}
    cycle_id = cycle.get("id")
    team_id = linear.get("team_id")
    state_id = linear.get("done_state_id")
    viewer_id = linear.get("viewer_id")
    rng = collected.get("range") or {}
    start = rng.get("start")
    end = rng.get("end")

    missing = [k for k, v in {
        "linear.team_id": team_id,
        "linear.done_state_id": state_id,
        "linear.viewer_id": viewer_id,
        "linear.cycle.id": cycle_id,
        "range.start": start,
        "range.end": end,
    }.items() if not v]
    if missing:
        _die(f"missing fields in collected JSON: {', '.join(missing)}. "
             "Re-run collect.py against an updated fetch_linear.py.")

    return {
        "title": title or default_title(start, end),
        "description": body,
        "teamId": team_id,
        "cycleId": cycle_id,
        "stateId": state_id,
        "assigneeId": viewer_id,
    }


def linear_api_mutation(mutation: str, variables: dict) -> dict | None:
    if shutil.which("linear") is None:
        _die("`linear` CLI not found on PATH. Install schpet/linear-cli.")
    r = subprocess.run(
        ["linear", "api", "--variables-json", json.dumps(variables)],
        input=mutation, capture_output=True, text=True,
    )
    if r.returncode != 0:
        _die(f"linear api failed: {r.stderr.strip()[:400]}")
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        _die(f"linear api returned non-JSON: {r.stdout[:400]}")
    if data.get("errors"):
        _die(f"GraphQL errors: {data['errors']}")
    return data.get("data")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", required=True,
                    help="collected.json path (or '-' for stdin)")
    ap.add_argument("--md", required=True,
                    help="markdown report path (or '-' for stdin)")
    ap.add_argument("--title", default=None,
                    help="issue title override; default: Weekly Summary YYYY-Www (start ~ end)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the issueCreate input as JSON and exit, do not send")
    args = ap.parse_args()

    if args.json == "-" and args.md == "-":
        _die("--json and --md cannot both be stdin")

    collected = json.loads(_read(args.json))
    body = _read(args.md)

    issue_input = build_input(collected, body, args.title)

    if args.dry_run:
        print(json.dumps({"input": issue_input}, ensure_ascii=False, indent=2))
        return

    data = linear_api_mutation(ISSUE_CREATE_MUTATION, {"input": issue_input})
    created = ((data or {}).get("issueCreate") or {})
    if not created.get("success"):
        _die(f"issueCreate returned success=false: {data}")
    issue = created.get("issue") or {}
    print(json.dumps({
        "identifier": issue.get("identifier"),
        "url": issue.get("url"),
        "state": (issue.get("state") or {}).get("name"),
        "cycle": (issue.get("cycle") or {}).get("number"),
        "assignee": (issue.get("assignee") or {}).get("displayName"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

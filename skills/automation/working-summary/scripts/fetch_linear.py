#!/usr/bin/env python3
"""Fetch Linear cycle issues for the working-summary report.

Uses the `linear` CLI (https://github.com/schpet/linear-cli) via its `api`
sub-command. Requires the user to be authenticated to the target workspace
(`linear auth login`).

Strategy:
1. Resolve the viewer ID via `{ viewer { id } }`.
2. Resolve the target cycle for the team:
   - `previous` — most recently completed cycle
   - `current` — cycle containing today (uses Linear's `activeCycle`)
   - `auto`    — cycle whose [startsAt, endsAt] overlaps the given range
3. Query issues in that cycle filtered by `assignee = viewer`, optionally
   filtered by state name list.
4. Return JSON to stdout.

Stdlib only. Returns `null` (silently) when the linear CLI is missing or
authentication fails — collect.py treats that as "Linear skipped".
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import date, datetime


def linear_api(query: str, variables: dict | None = None) -> dict | None:
    if shutil.which("linear") is None:
        return None
    args = ["linear", "api"]
    if variables:
        args += ["--variables-json", json.dumps(variables)]
    r = subprocess.run(args, input=query, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[linear err] {r.stderr.strip()[:200]}", file=sys.stderr)
        return None
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        return None
    if data.get("errors"):
        print(f"[linear gql err] {data['errors']}", file=sys.stderr)
        return None
    return data.get("data")


def get_viewer_id() -> str | None:
    d = linear_api("{ viewer { id displayName } }")
    if not d:
        return None
    return (d.get("viewer") or {}).get("id")


def list_team_cycles(team_key: str) -> list[dict]:
    q = """
    query($key: String!) {
      cycles(filter: { team: { key: { eq: $key } } }, first: 50) {
        nodes { id number name startsAt endsAt progress completedAt }
      }
    }
    """
    d = linear_api(q, {"key": team_key})
    if not d:
        return []
    return ((d.get("cycles") or {}).get("nodes")) or []


def _parse_iso(s: str) -> date | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def resolve_cycle(team_key: str, spec: str, start: date, end: date) -> dict | None:
    """Resolve `spec` to a single cycle dict.

    spec ∈ {previous, current, auto}
    """
    cycles = list_team_cycles(team_key)
    if not cycles:
        return None

    # Annotate with parsed dates
    for c in cycles:
        c["_start"] = _parse_iso(c.get("startsAt"))
        c["_end"] = _parse_iso(c.get("endsAt"))

    today = date.today()

    if spec == "current":
        for c in cycles:
            if c["_start"] and c["_end"] and c["_start"] <= today < c["_end"]:
                return c
        return None

    if spec == "previous":
        completed = [c for c in cycles if c["_end"] and c["_end"] <= today]
        if not completed:
            return None
        completed.sort(key=lambda c: c["_end"], reverse=True)
        return completed[0]

    if spec == "auto":
        # Cycle whose [start, end] overlaps [range_start, range_end+1]
        candidates = [
            c for c in cycles
            if c["_start"] and c["_end"]
            and c["_start"] <= end and c["_end"] > start
        ]
        if not candidates:
            return None
        # If multiple, pick the one with max overlap
        def overlap(c):
            ov_start = max(c["_start"], start)
            ov_end = min(c["_end"], end)
            return (ov_end - ov_start).days
        candidates.sort(key=overlap, reverse=True)
        return candidates[0]

    return None


_ISSUE_FIELDS = """
nodes {
  identifier
  title
  priority
  priorityLabel
  estimate
  state { name type }
  labels(first: 20) { nodes { name } }
  url
  completedAt
  updatedAt
  createdAt
  attachments(first: 20) { nodes { url title sourceType } }
}
"""


def fetch_cycle_issues(
    team_key: str, cycle_number: int, viewer_id: str,
    include_states: list[str] | None = None,
    state_types: list[str] | None = None,
) -> list[dict]:
    q = "query($filter: IssueFilter!) { issues(filter: $filter, first: 250) {" + _ISSUE_FIELDS + "} }"
    flt: dict = {
        "team": {"key": {"eq": team_key}},
        "cycle": {"number": {"eq": cycle_number}},
        "assignee": {"id": {"eq": viewer_id}},
    }
    if include_states:
        flt["state"] = {"name": {"in": include_states}}
    elif state_types:
        flt["state"] = {"type": {"in": state_types}}
    d = linear_api(q, {"filter": flt})
    if not d:
        return []
    return ((d.get("issues") or {}).get("nodes")) or []


def normalize_issue(it: dict) -> dict:
    """Flatten the GraphQL result into a friendlier shape."""
    return {
        "identifier": it.get("identifier"),
        "title": it.get("title") or "",
        "priority": it.get("priority"),
        "priorityLabel": it.get("priorityLabel"),
        "estimate": it.get("estimate"),
        "state": (it.get("state") or {}).get("name"),
        "stateType": (it.get("state") or {}).get("type"),
        "labels": [l.get("name") for l in ((it.get("labels") or {}).get("nodes") or [])],
        "url": it.get("url"),
        "completedAt": it.get("completedAt"),
        "updatedAt": it.get("updatedAt"),
        "createdAt": it.get("createdAt"),
        "attachments": [
            {
                "url": a.get("url"),
                "title": a.get("title"),
                "sourceType": a.get("sourceType"),
            }
            for a in ((it.get("attachments") or {}).get("nodes") or [])
        ],
    }


def _cycle_meta(c: dict | None) -> dict | None:
    if not c:
        return None
    return {
        "number": c.get("number"),
        "name": c.get("name"),
        "startsAt": c.get("startsAt"),
        "endsAt": c.get("endsAt"),
        "progress": c.get("progress"),
        "completedAt": c.get("completedAt"),
    }


def collect(
    team_key: str, cycle_spec: str,
    range_start: str, range_end: str,
    include_states: list[str] | None = None,
) -> dict | None:
    """Top-level entrypoint for collect.py.

    Returns issues for the **report cycle** (resolved by `cycle_spec` against
    the date range), plus a separate snapshot of in-progress issues from the
    **active cycle** (the one containing today). For typical weekly reports
    these are different cycles — the report cycle is the just-completed week
    and the active cycle is what the user is currently working in.
    """
    if shutil.which("linear") is None:
        return None
    viewer = get_viewer_id()
    if not viewer:
        return None
    start = _parse_iso(range_start)
    end = _parse_iso(range_end)
    if not (start and end):
        return None

    report_cycle = resolve_cycle(team_key, cycle_spec, start, end)
    active_cycle = resolve_cycle(team_key, "current", start, end)

    report_issues: list[dict] = []
    if report_cycle:
        raw = fetch_cycle_issues(team_key, report_cycle["number"], viewer, include_states)
        report_issues = [normalize_issue(it) for it in raw]

    # In-progress snapshot from the active cycle. If the active cycle is the
    # same as the report cycle, reuse its already-fetched issues to skip a
    # second round-trip.
    in_progress: list[dict] = []
    in_progress_cycle = None
    if active_cycle:
        in_progress_cycle = active_cycle
        if report_cycle and active_cycle["number"] == report_cycle["number"]:
            in_progress = [
                it for it in report_issues if it.get("stateType") == "started"
            ]
        else:
            raw_ip = fetch_cycle_issues(
                team_key, active_cycle["number"], viewer,
                state_types=["started"],
            )
            in_progress = [normalize_issue(it) for it in raw_ip]

    return {
        "team": team_key,
        "viewer_id": viewer,
        "cycle": _cycle_meta(report_cycle),
        "issues": report_issues,
        "in_progress": {
            "cycle": _cycle_meta(in_progress_cycle),
            "issues": in_progress,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--team", required=True, help="Linear team key, e.g. LOBE")
    ap.add_argument("--cycle", default="auto", choices=["previous", "current", "auto"])
    ap.add_argument("--from", dest="start", required=True)
    ap.add_argument("--to", dest="end", required=True)
    ap.add_argument("--state", action="append", default=[],
                    help="filter by state name (repeatable)")
    args = ap.parse_args()

    out = collect(
        args.team, args.cycle, args.start, args.end,
        include_states=args.state or None,
    )
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()

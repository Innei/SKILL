#!/usr/bin/env -S uv run --quiet --with pyyaml --with chinesecalendar python
"""Orchestrator: load config -> compute range -> fetch GitHub data -> JSON.

Default config path: ~/.config/working-summary/config.yaml
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from compute_range import classify_range, default_range, parse_date  # noqa: E402
from fetch_github import collect as fetch_github_collect  # noqa: E402
from fetch_linear import collect as fetch_linear_collect  # noqa: E402
from pr_stats import build_stats  # noqa: E402

DEFAULT_CONFIG = Path.home() / ".config" / "working-summary" / "config.yaml"


def load_config(path: Path) -> dict:
    if not path.exists():
        print(f"config not found: {path}", file=sys.stderr)
        print("copy scripts/../config.example.yaml to this path and edit.", file=sys.stderr)
        sys.exit(2)
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def gh_current_user() -> str:
    try:
        r = subprocess.run(
            ["gh", "api", "user", "-q", ".login"],
            capture_output=True, text=True, check=True,
        )
        return r.stdout.strip()
    except Exception:
        return ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--from", dest="start", help="YYYY-MM-DD")
    ap.add_argument("--to", dest="end", help="YYYY-MM-DD")
    ap.add_argument("--date", help="reference date, default today")
    args = ap.parse_args()

    cfg = load_config(Path(args.config).expanduser())

    today = parse_date(args.date) if args.date else date.today()
    if args.start and args.end:
        start, end = parse_date(args.start), parse_date(args.end)
    elif args.start:
        start, end = parse_date(args.start), today
    else:
        start, end = default_range(today)

    breakdown = classify_range(start, end)

    gh_cfg = cfg.get("github") or {}
    author = gh_cfg.get("user") or gh_current_user()
    repos: list[str] = gh_cfg.get("repos") or []
    orgs: list[str] = gh_cfg.get("orgs") or []
    include_commits: bool = gh_cfg.get("include_commits", True)
    if not author:
        print("cannot resolve github author (set github.user in config or run `gh auth login`)", file=sys.stderr)
        sys.exit(3)
    if not repos and not orgs:
        print("config.github must list at least one of `orgs` or `repos`", file=sys.stderr)
        sys.exit(3)

    github_data = fetch_github_collect(
        author, start.isoformat(), end.isoformat(),
        repos=repos, orgs=orgs,
        include_commits=include_commits,
    )

    linear_cfg = cfg.get("linear") or {}
    linear_data = None
    if linear_cfg.get("team"):
        linear_data = fetch_linear_collect(
            team_key=linear_cfg["team"],
            cycle_spec=linear_cfg.get("cycle", "auto"),
            range_start=start.isoformat(),
            range_end=end.isoformat(),
            include_states=linear_cfg.get("include_states") or None,
        )

    result = {
        "range": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "days": (end - start).days + 1,
            "workdays": sum(1 for d in breakdown if d["workday"]),
            "holidays": sum(1 for d in breakdown if d["holiday"]),
            "breakdown": breakdown,
        },
        "config": {
            "author": author,
            "orgs": orgs,
            "repos": repos,
            "include_commits": include_commits,
            "linear": cfg.get("linear"),
            "output": cfg.get("output"),
        },
        "github": github_data,
        "linear": linear_data,
        "stats": build_stats(github_data),
    }
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()

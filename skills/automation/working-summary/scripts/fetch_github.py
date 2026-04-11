#!/usr/bin/env python3
"""Fetch GitHub PRs, commits, and issues for a date range.

Strategy (REST-only, no GitHub Search index):

1. Expand orgs to all repos via `GET /orgs/{org}/repos` (paginated, includes private).
2. For every repo (org-expanded + explicit), fetch commits filtered by
   `author=` and `since/until` window via `/repos/{repo}/commits`.
3. Reconstruct merged PRs by extracting `(#NNN)` refs from commit messages and
   calling `/repos/{repo}/pulls/{n}` per ref. Commit dates are merge dates, so
   the resulting PRs are guaranteed merged in window.
4. For "active" repos (those with commits) plus explicit repos, fetch open PRs
   (`/repos/{r}/pulls?state=open`) and assigned issues (`/repos/{r}/issues`),
   then filter by author + updated window client-side.

The previous implementation used `gh search prs/issues` which is unreliable:
private orgs are unindexed, and even public mono-repos return partial results.
REST endpoints are authoritative.

Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

PR_NUM_RE = re.compile(r"\(#(\d+)\)")
MAX_WORKERS = 16


_BENIGN_ERRORS = (
    "Git Repository is empty",  # 409 on empty repos
    "Not Found",                 # 404 on archived/missing — caller handles []
)


def gh(*args: str) -> str:
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if r.returncode != 0:
        stderr = (r.stderr or "").strip()
        if not any(msg in stderr for msg in _BENIGN_ERRORS):
            print(f"[gh err] {' '.join(args[:4])}: {stderr.splitlines()[0][:200] if stderr else ''}", file=sys.stderr)
        return ""
    return r.stdout or ""


def _json(raw: str, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


# ---------- repo discovery ----------

def list_org_repos(org: str) -> list[str]:
    """Page through `GET /orgs/{org}/repos` until exhausted."""
    out: list[str] = []
    page = 1
    while True:
        raw = gh(
            "api",
            f"orgs/{org}/repos?per_page=100&page={page}&type=all",
            "-q", ".[].full_name",
        )
        names = [x for x in raw.split("\n") if x]
        if not names:
            break
        out.extend(names)
        if len(names) < 100:
            break
        page += 1
    return out


# ---------- normalizers ----------

def _normalize_pr(data: dict, repo: str) -> dict:
    return {
        "number": data.get("number"),
        "title": data.get("title") or "",
        "state": "merged" if data.get("merged_at") else data.get("state"),
        "url": data.get("html_url"),
        "createdAt": data.get("created_at"),
        "updatedAt": data.get("updated_at"),
        "mergedAt": data.get("merged_at"),
        "labels": [{"name": (l.get("name") or "")} for l in (data.get("labels") or [])],
        "repository": {
            "name": repo.split("/")[-1],
            "nameWithOwner": repo,
        },
        "body": (data.get("body") or "")[:1500],
    }


def _normalize_issue(data: dict, repo: str) -> dict:
    return {
        "number": data.get("number"),
        "title": data.get("title") or "",
        "state": data.get("state"),
        "url": data.get("html_url"),
        "updatedAt": data.get("updated_at"),
        "labels": [{"name": (l.get("name") or "")} for l in (data.get("labels") or [])],
        "repository": {
            "name": repo.split("/")[-1],
            "nameWithOwner": repo,
        },
    }


# ---------- per-repo fetchers ----------

def fetch_commits(repo: str, author: str, start: str, end: str) -> list[dict]:
    path = (
        f"/repos/{repo}/commits"
        f"?author={author}&since={start}T00:00:00Z&until={end}T23:59:59Z&per_page=100"
    )
    data = _json(gh("api", path), [])
    if not isinstance(data, list):
        return []
    return [
        {
            "sha": (c.get("sha") or "")[:7],
            "message": ((c.get("commit") or {}).get("message") or "").split("\n", 1)[0],
            "date": ((c.get("commit") or {}).get("author") or {}).get("date"),
            "url": c.get("html_url"),
        }
        for c in data
    ]


def fetch_pr_detail(repo: str, number: int) -> dict | None:
    data = _json(gh("api", f"/repos/{repo}/pulls/{number}"), None)
    if not isinstance(data, dict) or "number" not in data:
        return None
    return _normalize_pr(data, repo)


def fetch_open_prs(repo: str, author: str, start: str, end: str) -> list[dict]:
    """List open PRs in repo, filter by author + updatedAt window.

    Sorted by updated DESC so we can short-circuit once we cross the start cutoff.
    """
    out: list[dict] = []
    page = 1
    cutoff_start = f"{start}T00:00:00Z"
    cutoff_end = f"{end}T23:59:59Z"
    author_lower = author.lower()
    while True:
        raw = gh(
            "api",
            f"/repos/{repo}/pulls?state=open&sort=updated&direction=desc&per_page=100&page={page}",
        )
        data = _json(raw, [])
        if not isinstance(data, list) or not data:
            break
        stop = False
        for pr in data:
            updated = pr.get("updated_at") or ""
            if updated < cutoff_start:
                stop = True
                continue
            if updated > cutoff_end:
                continue
            user = ((pr.get("user") or {}).get("login") or "").lower()
            if user != author_lower:
                continue
            out.append(_normalize_pr(pr, repo))
        if stop or len(data) < 100:
            break
        page += 1
    return out


def fetch_issues(repo: str, assignee: str, start: str, end: str) -> list[dict]:
    """List issues assigned to `assignee`, updated in window.

    `/repos/{r}/issues` returns PRs too — filter them out via the
    `pull_request` key. `since=` is updated >= start; we filter end client-side.
    """
    out: list[dict] = []
    page = 1
    cutoff_end = f"{end}T23:59:59Z"
    while True:
        raw = gh(
            "api",
            f"/repos/{repo}/issues?assignee={assignee}&state=all"
            f"&since={start}T00:00:00Z&sort=updated&direction=desc&per_page=100&page={page}",
        )
        data = _json(raw, [])
        if not isinstance(data, list) or not data:
            break
        for it in data:
            if "pull_request" in it:
                continue
            if (it.get("updated_at") or "") > cutoff_end:
                continue
            out.append(_normalize_issue(it, repo))
        if len(data) < 100:
            break
        page += 1
    return out


# ---------- orchestration ----------

def collect(
    author: str, start: str, end: str,
    repos: list[str], orgs: list[str],
    include_commits: bool = True,
) -> dict:
    """Fetch all PR/commit/issue data, grouped by `owner/name`.

    Args:
        author: GitHub login to filter by.
        start, end: ISO dates (YYYY-MM-DD), inclusive.
        repos: explicit repo list.
        orgs: org slugs to expand into all member repos.
        include_commits: when False, skip commit + merged-PR reconstruction
            (open PRs and issues are still fetched on the explicit repo list).
    """
    # 1. Expand orgs
    expanded: set[str] = set(repos)
    for org in orgs:
        expanded.update(list_org_repos(org))

    commit_map: dict[str, list] = {}
    if include_commits and expanded:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futs = {ex.submit(fetch_commits, r, author, start, end): r for r in expanded}
            for fut in as_completed(futs):
                r = futs[fut]
                try:
                    cs = fut.result()
                except Exception as e:
                    print(f"[err] commits {r}: {e}", file=sys.stderr)
                    cs = []
                if cs:
                    commit_map[r] = cs

    # 2. Reconstruct merged PRs from commit message refs
    pr_refs: list[tuple[str, int]] = []
    seen: set[tuple[str, int]] = set()
    for r, cs in commit_map.items():
        for c in cs:
            for m in PR_NUM_RE.finditer(c["message"]):
                key = (r, int(m.group(1)))
                if key not in seen:
                    seen.add(key)
                    pr_refs.append(key)

    g_merged: dict[str, list] = {}
    if pr_refs:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futs = {ex.submit(fetch_pr_detail, r, n): (r, n) for r, n in pr_refs}
            for fut in as_completed(futs):
                r, _n = futs[fut]
                try:
                    data = fut.result()
                except Exception as e:
                    print(f"[err] pr {futs[fut]}: {e}", file=sys.stderr)
                    continue
                if data and data.get("state") == "merged":
                    g_merged.setdefault(r, []).append(data)
    for r in g_merged:
        g_merged[r].sort(key=lambda p: p.get("number") or 0, reverse=True)

    # 3. Per-target-repo open PRs + issues. Targets = active (had commits) + explicit.
    target_repos = sorted(set(commit_map.keys()) | set(repos))
    g_open: dict[str, list] = {}
    g_issues: dict[str, list] = {}
    if target_repos:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            f_open = {ex.submit(fetch_open_prs, r, author, start, end): r for r in target_repos}
            f_iss = {ex.submit(fetch_issues, r, author, start, end): r for r in target_repos}
            for fut in as_completed(f_open):
                r = f_open[fut]
                try:
                    op = fut.result()
                except Exception as e:
                    print(f"[err] open prs {r}: {e}", file=sys.stderr)
                    op = []
                if op:
                    g_open[r] = op
            for fut in as_completed(f_iss):
                r = f_iss[fut]
                try:
                    iss = fut.result()
                except Exception as e:
                    print(f"[err] issues {r}: {e}", file=sys.stderr)
                    iss = []
                if iss:
                    g_issues[r] = iss

    # 4. Assemble
    all_repos = sorted(set(g_merged) | set(g_open) | set(g_issues) | set(commit_map))
    return {
        r: {
            "prs_merged": g_merged.get(r, []),
            "prs_open": g_open.get(r, []),
            "issues": g_issues.get(r, []),
            "commits": commit_map.get(r, []),
        }
        for r in all_repos
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", action="append", default=[], help="owner/name, repeatable")
    ap.add_argument("--org", action="append", default=[], help="org slug, repeatable")
    ap.add_argument("--author", required=True)
    ap.add_argument("--from", dest="start", required=True, help="YYYY-MM-DD")
    ap.add_argument("--to", dest="end", required=True, help="YYYY-MM-DD")
    ap.add_argument("--no-commits", action="store_true")
    args = ap.parse_args()

    if not args.repo and not args.org:
        print("at least one --repo or --org is required", file=sys.stderr)
        sys.exit(2)

    result = collect(
        args.author, args.start, args.end,
        repos=args.repo, orgs=args.org,
        include_commits=not args.no_commits,
    )
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()

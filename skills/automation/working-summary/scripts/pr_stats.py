from __future__ import annotations

import re
import unicodedata

CANONICAL = ("feat", "fix", "refactor", "perf", "chore", "docs", "other")

_BUCKET = {
    "feat": "feat",
    "fix": "fix",
    "refactor": "refactor",
    "perf": "perf",
    "chore": "chore",
    "build": "chore",
    "ci": "chore",
    "style": "chore",
    "revert": "chore",
    "docs": "docs",
    "test": "docs",
}

_PREFIX_RE = re.compile(
    r"^(feat|fix|refactor|perf|build|ci|chore|docs|test|style|revert)(?:\s*[\(:!]|$)",
    re.I,
)


def _strip_leading_emoji(title: str) -> str:
    t = title.strip()
    if not t:
        return t
    i = 0
    n = len(t)
    while i < n:
        ch = t[i]
        cat = unicodedata.category(ch)
        code = ord(ch)
        if cat in ("So", "Sk", "Sm", "Mn", "Me") or code in (0xFE0F, 0x200D, 0x20E3):
            i += 1
            continue
        if 0x1F000 <= code <= 0x1FAFF or 0x2600 <= code <= 0x27BF:
            i += 1
            continue
        break
    return t[i:].lstrip()


def classify_title(title: str) -> str:
    t = _strip_leading_emoji(title or "")
    m = _PREFIX_RE.match(t)
    if not m:
        return "other"
    return _BUCKET.get(m.group(1).lower(), "other")


def _ordered(counts: dict[str, int]) -> dict[str, int]:
    return {k: counts[k] for k in CANONICAL if counts.get(k)}


def build_stats(github: dict, weekend_dates: list[str] | None = None) -> dict:
    weekend_set = set(weekend_dates or [])
    total: dict[str, int] = {}
    by_repo: list[dict] = []
    weekend_prs = 0
    for repo, data in (github or {}).items():
        prs = (data or {}).get("prs_merged") or []
        commits = (data or {}).get("commits") or []
        if not prs and not commits:
            continue  # repository had no activity in the window
        counts: dict[str, int] = {}
        for pr in prs:
            bucket = classify_title((pr or {}).get("title") or "")
            counts[bucket] = counts.get(bucket, 0) + 1
            total[bucket] = total.get(bucket, 0) + 1
            if ((pr or {}).get("mergedAt") or "")[:10] in weekend_set:
                weekend_prs += 1
        row = {
            "repo": repo,
            "prs": len(prs),
            "commits": len(commits),
            "by_type": _ordered(counts),
        }
        if not prs:
            # Direct-push repos are how the biz repos ship; they are not "nothing
            # happened". Keep them in the stats so the appendix can list them.
            row["push_only"] = True
            row["top_commits"] = [
                {
                    "sha": (c.get("sha") or "")[:7],
                    "subject": ((c.get("message") or "").splitlines() or [""])[0][:110],
                }
                for c in sorted(commits, key=lambda c: c.get("date") or "", reverse=True)[:4]
            ]
        by_repo.append(row)
    weekend_commits = sum(
        1
        for data in (github or {}).values()
        for commit in ((data or {}).get("commits") or [])
        if (commit.get("date") or "")[:10] in weekend_set
    )
    by_repo.sort(key=lambda row: (-row["prs"], -row["commits"], row["repo"]))
    return {
        "prs_merged": sum(row["prs"] for row in by_repo),
        "by_type": _ordered(total),
        "by_repo": by_repo,
        "weekend": {
            "prs_merged": weekend_prs,
            "commits": weekend_commits,
            "dates": sorted(weekend_set),
        },
    }

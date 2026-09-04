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


def build_stats(github: dict) -> dict:
    total: dict[str, int] = {}
    by_repo: list[dict] = []
    for repo, data in (github or {}).items():
        prs = (data or {}).get("prs_merged") or []
        if not prs:
            continue
        counts: dict[str, int] = {}
        for pr in prs:
            bucket = classify_title((pr or {}).get("title") or "")
            counts[bucket] = counts.get(bucket, 0) + 1
            total[bucket] = total.get(bucket, 0) + 1
        by_repo.append(
            {
                "repo": repo,
                "prs": len(prs),
                "by_type": _ordered(counts),
            }
        )
    by_repo.sort(key=lambda row: (-row["prs"], row["repo"]))
    return {
        "prs_merged": sum(row["prs"] for row in by_repo),
        "by_type": _ordered(total),
        "by_repo": by_repo,
    }

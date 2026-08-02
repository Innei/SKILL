#!/usr/bin/env python3
"""Attribute every source file to exactly one sub-product bucket.

Usage:
    python3 bucketize.py <file-list> [buckets.json]
    (run from the repo root -- paths in <file-list> are repo-relative)

<file-list>: one repo-relative path per line (from count-pure-loc.sh).
[buckets.json]: ordered list of [bucket, prefix] pairs, first match wins.
Without it, EXAMPLE_BUCKETS below runs -- replace with your inventory.

Rules encoded here:
- order prefixes specific -> general; the final ["infra", ""] catch-all
  guarantees every file lands somewhere, so bucket sums == lens-3 total
- pure-code counting matches count-pure-loc.sh (blank/comment stripped)
- unreadable files count 0 loudly, not silently (see MISSES check)
"""
import json
import sys
from collections import defaultdict

EXAMPLE_BUCKETS = [
    ["eval", "src/routes/(main)/eval/"],
    ["eval", "apps/server/src/services/agentEvalRun"],
    ["chat", "src/store/chat/"],
    ["chat", "src/features/Conversation/"],
    ["infra", ""],
]


def code_lines(path):
    n = 0
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith(("//", "/*", "*")):
                continue
            n += 1
    return n


def main():
    files = [l for l in open(sys.argv[1]).read().split() if l]
    buckets = (
        json.load(open(sys.argv[2])) if len(sys.argv) > 2 else EXAMPLE_BUCKETS
    )
    if buckets[-1][1] != "":
        sys.exit("last bucket must be a catch-all with prefix \"\"")

    tot, cnt = defaultdict(int), defaultdict(int)
    catch_all = buckets[-1][0]
    detail, misses = defaultdict(int), []
    for f in files:
        for name, prefix in buckets:
            if f.startswith(prefix):
                try:
                    n = code_lines(f)
                except OSError:
                    misses.append(f)
                    n = 0
                tot[name] += n
                cnt[name] += 1
                if name == catch_all:
                    detail["/".join(f.split("/")[:2])] += n
                break

    grand = sum(tot.values())
    for name in sorted(tot, key=lambda k: -tot[k]):
        print(f"{tot[name]:>9}  {cnt[name]:>5} files  {name}")
    print(f"{grand:>9}  TOTAL")

    print(f"\n--- {catch_all} breakdown (top 20, chase anything large) ---")
    for k in sorted(detail, key=lambda k: -detail[k])[:20]:
        print(f"{detail[k]:>9}  {k}")

    if misses:
        print(f"\nWARNING: {len(misses)} unreadable files counted as 0 "
              "(wrong cwd? run from the repo root):", file=sys.stderr)
        for f in misses[:5]:
            print(f"  {f}", file=sys.stderr)
        sys.exit(1)
    if grand == 0:
        sys.exit("all buckets are 0 -- wrong cwd or empty file list")


if __name__ == "__main__":
    main()

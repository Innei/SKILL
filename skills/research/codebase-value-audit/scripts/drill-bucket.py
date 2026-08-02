#!/usr/bin/env python3
"""Drill one bucket a level deeper: aggregate pure-code lines per directory.

Usage:
    python3 drill-bucket.py <file-list> <depth> <prefix> [prefix...]
    (run from the repo root)

Use before defending any bucket verdict that gets challenged, and on
every bucket above ~15k lines before issuing a verdict at all. Directory
keys are truncated to <depth> path segments; files matching any prefix
are included. Output is sorted by lines, descending — the top rows are
where squatters, dead-but-routed pages, and data-as-code hide.
"""
import sys
from collections import defaultdict


def code_lines(path):
    n = 0
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if s and not s.startswith(("//", "/*", "*")):
                n += 1
    return n


def main():
    if len(sys.argv) < 4:
        sys.exit("usage: drill-bucket.py <file-list> <depth> <prefix> [prefix...]")
    depth = int(sys.argv[2])
    prefixes = tuple(sys.argv[3:])
    tot, cnt = defaultdict(int), defaultdict(int)
    grand = files = 0
    for f in open(sys.argv[1]).read().split():
        if not f.startswith(prefixes):
            continue
        n = code_lines(f)
        key = "/".join(f.split("/")[:depth])
        tot[key] += n
        cnt[key] += 1
        grand += n
        files += 1
    print(f"TOTAL {grand} lines in {files} files\n")
    for k in sorted(tot, key=lambda k: -tot[k]):
        print(f"{tot[k]:>8} {cnt[k]:>5}  {k}")


if __name__ == "__main__":
    main()

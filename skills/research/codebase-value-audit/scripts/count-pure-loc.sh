#!/usr/bin/env bash
# Usage: count-pure-loc.sh <repo-root> [out-file-list]
# Prints three lens counts and writes the strict (lens-3 scope) file list
# for bucketize.py. All counts sum per-file to survive xargs batching.
set -euo pipefail

REPO="${1:?usage: count-pure-loc.sh <repo-root> [out-file-list]}"
OUT="${2:-/tmp/audit_src_files.txt}"
cd "$REPO"

EXT='\.(ts|tsx|js|jsx|mjs|cjs|mts)$'
NONSRC='(\.test\.|\.spec\.|__tests__/|__mocks__/|/fixtures/|\.fixture\.|^e2e/|^scripts/|^tests/|\.stories\.|\.mock\.|/testUtils|/test-utils|vitest|\.d\.ts$)'

sum_lines() { xargs wc -l 2>/dev/null | awk '$2 != "total" {s+=$1} END {print s+0}'; }

L1=$(git ls-files | sort -u | grep -E "$EXT" | sum_lines)

git ls-files | sort -u | grep -E '\.(ts|tsx)$' | grep -vE "$NONSRC" > "$OUT"
L2=$(sum_lines < "$OUT")

read -r BLANK COMMENT CODE <<< "$(xargs awk '
  /^[[:space:]]*$/ {b+=1; next}
  /^[[:space:]]*(\/\/|\/\*|\*)/ {c+=1; next}
  {n+=1}
  END {print b+0, c+0, n+0}
' < "$OUT" 2>/dev/null | awk '{b+=$1; c+=$2; n+=$3} END {print b, c, n}')"

echo "lens 1  tracked total (TS/JS):        $L1"
echo "lens 2  non-test physical (TS/TSX):   $L2   ($(wc -l < "$OUT" | tr -d ' ') files)"
echo "lens 3  pure code (no blank/comment): $CODE   (blank $BLANK, comment $COMMENT)"
echo "file list for bucketize.py: $OUT"

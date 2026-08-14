#!/usr/bin/env bash
# Scaffold a new skill in the SKILL repo: directory, stub SKILL.md,
# README row (alphabetical inside the domain table), and the two flat
# symlinks required by the pre-commit hook. Stages everything with `git add`
# but does NOT commit — the agent fills in SKILL.md, then commits.
#
# Usage: scaffold-skill.sh <domain> <skill-name> "<one-line purpose>"
#   domain ∈ infrastructure | automation | writing | research | content
set -euo pipefail

if [ $# -ne 3 ]; then
  echo "usage: $(basename "$0") <domain> <skill-name> \"<one-line purpose>\"" >&2
  exit 2
fi

DOMAIN="$1"
NAME="$2"
PURPOSE="$3"

case "$DOMAIN" in
  infrastructure|automation|writing|research|content) ;;
  *) echo "error: invalid domain '$DOMAIN' (expected one of: infrastructure|automation|writing|research|content)" >&2; exit 2 ;;
esac

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(bash "$HERE/resolve-skill-repo.sh")"
TARGET="$REPO/skills/$DOMAIN/$NAME"

[ -e "$TARGET" ] && { echo "error: $TARGET already exists" >&2; exit 1; }

mkdir -p "$TARGET"

cat > "$TARGET/SKILL.md" <<EOF
---
name: $NAME
description: >
  <State the capability and every concrete trigger condition. Remove this
  placeholder before committing.>
---

# $NAME

## Capability contract

- **Outcome:** <state the externally meaningful result>
- **Preconditions:** <state required access, inputs, and environment>
- **Boundaries:** <state exclusions and stopping conditions>

## Operational core

<Give the shortest sufficient procedure or decision path. Use imperative
instructions. Add decision tables, diagrams, pitfalls, rollback, or examples
only when they carry operational information.>

## Verification

- [ ] <state an externally observable success criterion>
EOF

HELPER="$REPO/.githooks/readme-domain-table.py"
[ -f "$HELPER" ] || { echo "error: $HELPER not found" >&2; exit 1; }
python3 "$HELPER" insert "$REPO/README.md" "$DOMAIN" "$NAME" "$PURPOSE"

cd "$REPO"
ln -sf "../../skills/$DOMAIN/$NAME" ".agent/skills/$NAME"
ln -sf "../../skills/$DOMAIN/$NAME" ".claude/skills/$NAME"

git add "skills/$DOMAIN/$NAME" "README.md" ".agent/skills/$NAME" ".claude/skills/$NAME"

cat <<EOF

scaffolded: $TARGET
next steps:
  1. replace every placeholder in $TARGET/SKILL.md
  2. add scripts/, references/, or assets/ only when they improve reuse
  3. validate the skill and remove empty conditional sections
  4. cd "$REPO" && git add "skills/$DOMAIN/$NAME" && git commit -m "feat: add $NAME skill" && git push
EOF

#!/usr/bin/env bash
# Print the absolute path to the SKILL repo.
# Reads `skill_repo_dir` from ~/.config/innei-skills/config.json; falls back to
# ~/git/innei-repo/SKILL. Expands a leading ~ to $HOME.
set -euo pipefail

CFG="${XDG_CONFIG_HOME:-$HOME/.config}/innei-skills/config.json"
DIR=""
if [ -f "$CFG" ] && command -v jq >/dev/null 2>&1; then
  DIR="$(jq -r '.skill_repo_dir // empty' "$CFG" 2>/dev/null || true)"
fi
DIR="${DIR:-$HOME/git/innei-repo/SKILL}"
DIR="${DIR/#\~/$HOME}"
if [ ! -d "$DIR" ]; then
  echo "error: skill repo not found at $DIR" >&2
  echo "set skill_repo_dir in $CFG (see references/config.example.json)" >&2
  exit 1
fi
echo "$DIR"

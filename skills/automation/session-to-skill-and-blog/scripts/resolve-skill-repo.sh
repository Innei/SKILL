#!/usr/bin/env bash
# Print the absolute path to the SKILL repo.
# Reads `skill_repo_dir` from ~/.config/innei-skills/config.json; falls back to
# ~/git/innei-repo/skill. Expands a leading ~ to $HOME.
set -euo pipefail

CFG="${XDG_CONFIG_HOME:-$HOME/.config}/innei-skills/config.json"
DIR=""
if [ -f "$CFG" ] && command -v jq >/dev/null 2>&1; then
  DIR="$(jq -r '.skill_repo_dir // empty' "$CFG" 2>/dev/null || true)"
fi
DIR="${DIR:-$HOME/git/innei-repo/skill}"
DIR="${DIR/#\~/$HOME}"
echo "$DIR"

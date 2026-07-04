#!/usr/bin/env bash
# Publish a working-summary HTML report to R2 via wrangler.
#
# Two subcommands so the skill can probe for conflicts before deciding
# whether to overwrite, suffix, or skip.
#
#   publish_r2.sh check <bucket> <key>
#       exit 0  → object exists
#       exit 1  → object missing
#       exit 2  → other error (wrangler/auth)
#
#   publish_r2.sh put <bucket> <local-file> <key> <base-url>
#       uploads <local-file> as <bucket>/<key> with text/html content type
#       on success prints "<base-url>/<key>" to stdout
#       exit 0 on success, exit 1 on failure
#
# The skill is responsible for asking the user before overwriting.

set -euo pipefail

die() {
  echo "publish_r2: $*" >&2
  exit 1
}

need_wrangler() {
  if ! command -v wrangler >/dev/null 2>&1 && ! command -v pnpm >/dev/null 2>&1; then
    die "neither wrangler nor pnpm on PATH"
  fi
}

# Resolve `wrangler` so users that only have it as a devDependency still work.
run_wrangler() {
  if command -v wrangler >/dev/null 2>&1; then
    wrangler "$@"
  else
    pnpm wrangler "$@"
  fi
}

cmd_check() {
  [[ $# -eq 2 ]] || die "usage: check <bucket> <key>"
  local bucket="$1" key="$2"
  # `--remote` is REQUIRED — wrangler 4 defaults r2 object commands to the
  # local miniflare emulator, which silently no-ops against production R2.
  if run_wrangler r2 object get "${bucket}/${key}" --pipe --remote >/dev/null 2>&1; then
    return 0
  fi
  if ! run_wrangler r2 bucket info "$bucket" >/dev/null 2>&1; then
    return 2
  fi
  return 1
}

cmd_put() {
  [[ $# -eq 4 ]] || die "usage: put <bucket> <local-file> <key> <base-url>"
  local bucket="$1" local_file="$2" key="$3" base_url="$4"
  [[ -f "$local_file" ]] || die "local file not found: $local_file"
  run_wrangler r2 object put "${bucket}/${key}" \
    --file "$local_file" \
    --content-type "text/html; charset=utf-8" \
    --remote >&2
  printf "%s/%s\n" "${base_url%/}" "$key"
}

main() {
  [[ $# -ge 1 ]] || die "usage: publish_r2.sh check|put ..."
  need_wrangler
  local sub="$1"; shift
  case "$sub" in
    check) cmd_check "$@" ;;
    put)   cmd_put   "$@" ;;
    *)     die "unknown subcommand: $sub" ;;
  esac
}

main "$@"

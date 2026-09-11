#!/usr/bin/env bash
# Usage: launch-timing.sh <App.app/Contents/MacOS/binary> [runs=3] [extra electron args...]
# Env:
#   USER_DATA_DIR   isolated --user-data-dir (default: mktemp; keeps the single-instance lock away)
#   WAIT_SECS       seconds to let the app run before killing it (default 7)
#   MILESTONES      pipe-separated regexes matched against stdout/stderr lines that carry a
#                   HH:MM:SS.mmm timestamp; each is reported relative to exec (default: common ones)
#   ENV_EXTRA       extra env for the app, e.g. "DEBUG=core:* LOBE_PROF=/tmp/main.cpuprofile"
# Output per run: [boot] probe lines (if the entry is instrumented) + milestone ms since exec.
set -euo pipefail

bin="${1:?binary path}"; runs="${2:-3}"; shift $(( $# >= 2 ? 2 : $# ))
ud="${USER_DATA_DIR:-$(mktemp -d)}"
wait_secs="${WAIT_SECS:-7}"
milestones="${MILESTONES:-Starting|Application ready|BrowserWindow instance created|Showing window|ready-to-show|first frame|BOOT_PROFILE}"
name="$(basename "$bin")"

for i in $(seq 1 "$runs"); do
  out="$(mktemp)"
  t0="$(perl -MTime::HiRes=time -e 'printf "%d\n", time*1000')"
  ( env ${ENV_EXTRA:-} "$bin" --user-data-dir="$ud" "$@" >"$out" 2>&1 & )
  sleep "$wait_secs"
  pkill -f "$name" || true
  sleep 1.5
  echo "=== run $i (exec wall=$t0)"
  grep -a '^\[boot\]' "$out" | tr '\n' ' '; echo
  grep -aE "$milestones" "$out" | head -20 | node -e '
    const t0 = +process.argv[1];
    const lines = require("fs").readFileSync(0, "utf8").split("\n").filter(Boolean);
    for (const l of lines) {
      let ms = null;
      const iso = l.match(/(\d{4}-\d\d-\d\dT[\d:.]+Z)/);
      const local = l.match(/(?:^|\s)(\d\d):(\d\d):(\d\d)\.(\d{3})/);
      if (iso) ms = Date.parse(iso[1]) - t0;
      else if (local) { const d = new Date(t0); d.setHours(+local[1], +local[2], +local[3], +local[4]); ms = d.getTime() - t0; }
      const text = l.replace(/^.*?›\s*/, "").replace(/^\S+Z\s*/, "").slice(0, 90);
      console.log(String(ms ?? "?").padStart(7) + "ms  " + text);
    }' "$t0"
  rm -f "$out"
done

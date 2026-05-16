#!/usr/bin/env bash
# Probe candidate hostnames for Reality `dest` suitability.
#
# A host passes only when ALL of:
#   1. TLS 1.3 negotiated
#   2. ALPN protocol h2 negotiated
#   3. Cert issuer chains via a publicly-trusted CA — i.e. NOT a vendor-internal
#      one like "Microsoft Update Secure Server CA" or "iCloud" / "Apple".
#
# Run this ON THE SERVER (egress from the same AS as the production server),
# not from the client side.
#
# Usage:
#   reality-probe.sh                       # uses default candidate list
#   reality-probe.sh host1 host2 ...       # custom list

set -euo pipefail

DEFAULT_HOSTS=(
  www.microsoft.com
  learn.microsoft.com
  support.microsoft.com
  www.bing.com
  www.yahoo.co.jp
  www.swift.com
)

hosts=("${@:-${DEFAULT_HOSTS[@]}}")

# Issuer-CN substrings that mean "internal CA — reject".
REJECT_PATTERNS=(
  'Update Secure Server'
  'iCloud'
)

for h in "${hosts[@]}"; do
  printf '\n--- %s ---\n' "$h"

  out=$(echo | timeout 6 openssl s_client \
        -connect "$h:443" -servername "$h" \
        -tls1_3 -alpn h2 2>&1 || true)

  proto=$(echo "$out" | awk -F': ' '/^[[:space:]]*Protocol/ {gsub(/ /,"",$2); print $2; exit}')
  alpn=$(echo  "$out" | awk -F': ' '/ALPN protocol:/ {print $NF; exit}')
  issuer=$(echo "$out" | awk -F'CN ?= ?' '/^issuer=/ {print $NF; exit}' | sed 's/[,\/].*//')

  printf '  Protocol: %s\n  ALPN:     %s\n  Issuer:   %s\n' \
    "${proto:-(none)}" "${alpn:-(none)}" "${issuer:-(none)}"

  ok="yes"
  [[ "$proto" == "TLSv1.3" ]] || ok="no (need TLSv1.3)"
  [[ "$alpn"  == "h2"      ]] || ok="no (need ALPN h2)"
  [[ -n "$issuer" ]] || ok="no (no issuer)"
  for pat in "${REJECT_PATTERNS[@]}"; do
    [[ "$issuer" == *"$pat"* ]] && ok="no (internal CA matched: $pat)"
  done

  if [[ "$ok" == "yes" ]]; then
    printf '  => OK   (valid Reality dest candidate)\n'
  else
    printf '  => SKIP %s\n' "$ok"
  fi
done

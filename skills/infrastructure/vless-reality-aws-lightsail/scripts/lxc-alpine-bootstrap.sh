#!/usr/bin/env bash
# Bootstrap a freshly-created Alpine LXC for unattended use.
#
# The Alpine minirootfs has NO openrc, NO ifupdown-ng, NO loopback configured.
# Unprivileged LXC also lacks /run/openrc/softlevel by default, which makes
# rc-service complain ("you will get unpredictable results").
#
# This script does, idempotently:
#   * bring up eth0 with the supplied static IP, set default route
#   * switch apk repo to Aliyun (Proxmox CDN is slow from CN/HK)
#   * apk add openrc + ifupdown-ng
#   * enable networking + hostname at boot
#   * write /etc/local.d/00-bootstrap.start to fix lo + softlevel at every boot
#   * enable the `local` service at boot
#
# RUN ON THE PVE HOST as root.
#
# Usage:
#   lxc-alpine-bootstrap.sh <CT_ID> <CT_IP/CIDR> <CT_GW>
# Example:
#   lxc-alpine-bootstrap.sh 205 10.0.0.30/24 10.0.0.8

set -euo pipefail

CT_ID="${1:?CT id required, e.g. 205}"
CT_IP="${2:?CT IP/CIDR required, e.g. 10.0.0.30/24}"
CT_GW="${3:?CT gateway required, e.g. 10.0.0.8}"

pct exec "$CT_ID" -- sh -s -- "$CT_IP" "$CT_GW" <<'REMOTE'
set -e
CT_IP="$1"
CT_GW="$2"

# bring eth0 up manually so apk can reach the world
ip link set eth0 up
ip addr add "$CT_IP" dev eth0 2>/dev/null || true
ip route replace default via "$CT_GW"

# Aliyun mirror — Proxmox CDN is slow, dl-cdn flaky from CN/HK
sed -i 's,dl-cdn.alpinelinux.org,mirrors.aliyun.com,g' /etc/apk/repositories
apk update
apk add --no-cache openrc ifupdown-ng

rc-update add networking boot 2>/dev/null || true
rc-update add hostname   boot 2>/dev/null || true

cat > /etc/local.d/00-bootstrap.start <<'EOS'
#!/bin/sh
mkdir -p /run/openrc
touch /run/openrc/softlevel
ip link set lo up 2>/dev/null
ip addr add 127.0.0.1/8 dev lo 2>/dev/null
exit 0
EOS
chmod +x /etc/local.d/00-bootstrap.start
rc-update add local boot 2>/dev/null || true

echo "bootstrap done in CT"
REMOTE

echo
echo "CT $CT_ID bootstrap complete. Reboot to verify auto-start:"
echo "  pct reboot $CT_ID && sleep 6 && pct exec $CT_ID -- ip addr show eth0"

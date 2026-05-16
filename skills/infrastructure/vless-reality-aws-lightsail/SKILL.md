---
name: vless-reality-aws-lightsail
description: Use when deploying VLESS+Reality+Vision on AWS Lightsail and bridging it to Surge (or similar TUN clients) with an Alpine LXC SOCKS5 bridge on the LAN plus a brew sing-box on the laptop for off-LAN use. Triggers on "set up vless reality on aws", "tokyo lightsail proxy", "surge doesn't support vless", "vless when away from home lan", "alpine lxc client for vless".
---

# VLESS + Reality + Vision on AWS Lightsail with LAN+Local Bridges for Surge

Use this skill when the egress is a Lightsail VLESS+Reality+Vision server and the consumer is Surge (or any client that does not speak VLESS). The deployment has two co-existing client locations: an Alpine LXC on the home LAN that serves every device, and a sibling sing-box on the user's Mac that takes over when the Mac leaves the LAN. Surge sees both as plain SOCKS5 and switches via a `fallback` group.

## Scope

- Target task class: one fresh Lightsail VLESS+Reality+Vision server with a Static IP, one LAN-side Alpine LXC sing-box bridge, one Mac-side brew sing-box, and a Surge `MANAGED-CONFIG` patch (proxy entries + fallback group + TUN bypass).
- Assumes: AWS CLI authenticated; Proxmox VE 8.x host reachable as `root@<pve>`; target Surge config managed as a file; the LAN has a WAN gateway that does NOT MITM the egress IP; the Mac runs Surge in TUN mode.
- Out of scope: WireGuard / Tailscale back-home (an alternative to the Mac local sing-box); server hardening; Hysteria2 / Trojan; multi-user Xray.

## Inputs

| Variable | Meaning |
|---|---|
| `LIGHTSAIL_REGION` | e.g. `ap-northeast-1` |
| `INSTANCE_NAME` | Lightsail instance name |
| `PVE_HOST` | Proxmox host, e.g. `root@10.0.0.10` |
| `CT_ID` / `CT_IP` / `CT_GW` | LXC id, static IP/CIDR, gateway (e.g. `205`, `10.0.0.30/24`, `10.0.0.8`) |
| `SURGE_HOST` / `SURGE_CONF_PATH` | Host running the Surge config file server and the path to `.conf` |
| `MAC_SINGBOX_CONF` | `/opt/homebrew/etc/sing-box/config.json` (Apple Silicon) or `/usr/local/etc/sing-box/config.json` (Intel) |

## Files Provided by This Skill

```
scripts/
  lightsail-ssh-init.sh      — fetch one-shot SSH key+cert+known_hosts (cert TTL ~13 min)
  reality-probe.sh           — probe SNI candidates for TLS 1.3 + ALPN h2 + public CA
  lxc-alpine-bootstrap.sh    — idempotent Alpine LXC bring-up (lo, openrc, softlevel, networking)
  vless-share-link.py        — generate vless:// share URI for mobile/GUI clients
references/
  xray-server.json           — server config template with placeholders
  singbox-client.json        — sing-box ≥1.13 client config template
```

## Workflow

```text
[1] Lightsail: open ports, attach Static IP, get SSH        -> scripts/lightsail-ssh-init.sh
[2] Pick Reality dest with PUBLIC CA chain                  -> scripts/reality-probe.sh
[3] Server: install Xray, write config                      -> references/xray-server.json
[4] PVE: create LXC, bootstrap Alpine                       -> scripts/lxc-alpine-bootstrap.sh
[5] CT sing-box (LAN bridge, listen 0.0.0.0:10808)          -> references/singbox-client.json
[6] Mac sing-box (off-LAN bridge, listen 127.0.0.1:10808)   -> references/singbox-client.json
[7] Surge: tun-excluded-routes += SERVER_IP/32; fallback group
[8] Verify both bridges via curl --socks5-hostname ipinfo.io
```

## Step 1 — Lightsail: Ports, Static IP, SSH

The Lightsail UI cannot add ICMP rules — only the CLI/API can. `put-instance-public-ports` is **full-overwrite**; prefer `open-instance-public-ports` for incremental adds.

```bash
# Open required ports incrementally
aws lightsail open-instance-public-ports --region "$LIGHTSAIL_REGION" --instance-name "$INSTANCE_NAME" \
  --port-info 'fromPort=443,toPort=443,protocol=tcp,cidrs=["0.0.0.0/0"],ipv6Cidrs=["::/0"]'
aws lightsail open-instance-public-ports --region "$LIGHTSAIL_REGION" --instance-name "$INSTANCE_NAME" \
  --port-info 'fromPort=8,toPort=-1,protocol=icmp,cidrs=["0.0.0.0/0"]'

# Attach a Static IP so SERVER_IP never drifts (free while attached to a running instance)
aws lightsail allocate-static-ip --region "$LIGHTSAIL_REGION" --static-ip-name "${INSTANCE_NAME}-static"
aws lightsail attach-static-ip   --region "$LIGHTSAIL_REGION" --static-ip-name "${INSTANCE_NAME}-static" \
  --instance-name "$INSTANCE_NAME"

# Reach SSH (cert valid ~13 min — re-run to refresh)
scripts/lightsail-ssh-init.sh "$INSTANCE_NAME" "$LIGHTSAIL_REGION" ./ssh
```

To re-roll a dynamic IP (only if Static IP not attached): `stop-instance` then `start-instance`. Attaching the Static IP **changes the public IP** to the allocated one — re-validate Reality and refresh all `server: ...` fields in client configs afterward.

## Step 2 — Reality `dest`: The Single Biggest Footgun

**Reality forwards unauthenticated TLS handshakes to the configured `dest`.** If the dest serves a cert from an internal CA (e.g. `Microsoft Update Secure Server CA`, Apple iCloud internal), the Reality module flags it as `target sent incorrect server hello or handshake incomplete` and refuses to relay. The client sees `x509: certificate signed by unknown authority` and stalls forever.

A dest passes only when **all three** hold:

1. `Protocol: TLSv1.3` negotiated
2. `ALPN protocol: h2` negotiated
3. Issuer is a publicly-trusted CA (chains to DigiCert, ISRG, etc.) — NOT a vendor-internal CA

Probe from the server itself (egress matches production):

```bash
# Defaults to a known-good candidate list
ssh ec2-user@$IP 'bash -s' < scripts/reality-probe.sh
# Or: ./scripts/reality-probe.sh learn.microsoft.com download.microsoft.com
```

**Known-good (2026):** `www.microsoft.com`, `learn.microsoft.com`, `support.microsoft.com`, `www.bing.com`, `www.yahoo.co.jp`.
**Known-bad:** `sls.update.microsoft.com`, `fe2.update.microsoft.com`, `dl.delivery.mp.microsoft.com`, `www.icloud.com`.

## Step 3 — Server: Install Xray and Deploy Config

```bash
# On the server (as ec2-user via the SSH from Step 1):
sudo bash -c 'curl -fsSL https://github.com/XTLS/Xray-install/raw/main/install-release.sh | bash -s -- install'

# Generate identity bits
/usr/local/bin/xray x25519           # PrivateKey + Password (== publicKey)
/usr/local/bin/xray uuid             # client UUID
openssl rand -hex 8                  # 8-byte shortId
```

Copy `references/xray-server.json` to `/usr/local/etc/xray/config.json` and substitute `<UUID>`, `<SNI>`, `<PRIVATEKEY>`, `<SHORTID>` (and drop the `_comment_template` field). Including `""` in `shortIds` lets clients connect with either the chosen shortId or an empty one — useful when distributing multiple variants.

```bash
sudo /usr/local/bin/xray run -test -config /usr/local/etc/xray/config.json
sudo systemctl restart xray && sudo ss -tlnp | grep ':443'
```

### Debugging Reality auth failures

The default `loglevel: warning` hides Reality's `REALITY: processed invalid connection` messages. To diagnose a failing client, temporarily set `info` and tail journalctl:

```bash
sudo sed -i 's/"warning"/"info"/' /usr/local/etc/xray/config.json
sudo systemctl restart xray
sudo journalctl -u xray -f          # watch for REALITY: lines, then revert
```

The file logs at `/var/log/xray/{access,error}.log` stay empty for Reality fallback events — journalctl captures stdout/stderr from the systemd unit and is the authoritative source.

## Step 4 — PVE: Create Alpine LXC

The Proxmox CDN can be very slow from CN/HK gateways. Pull the Alpine minirootfs from Aliyun and rename to `.tar.gz` (despite Proxmox naming convention using `.tar.xz`):

```bash
ssh "$PVE_HOST" '
cd /var/lib/vz/template/cache
curl -fsSL -o alpine-3.23-default_20260116_amd64.tar.gz \
  https://mirrors.aliyun.com/alpine/v3.23/releases/x86_64/alpine-minirootfs-3.23.0-x86_64.tar.gz
'

ssh "$PVE_HOST" "pct create $CT_ID local:vztmpl/alpine-3.23-default_20260116_amd64.tar.gz \
  --hostname vless-client --memory 256 --swap 256 --cores 1 \
  --rootfs local-lvm:2 --net0 name=eth0,bridge=vmbr0,ip=$CT_IP,gw=$CT_GW \
  --unprivileged 1 --onboot 1 --ostype alpine"

ssh "$PVE_HOST" "pct start $CT_ID"

# Bring up loopback, install openrc/ifupdown-ng, persist softlevel fix
scp scripts/lxc-alpine-bootstrap.sh "$PVE_HOST:/tmp/"
ssh "$PVE_HOST" "/tmp/lxc-alpine-bootstrap.sh $CT_ID $CT_IP $CT_GW"
```

The Alpine minirootfs has no `lo`, no `openrc`, no `ifupdown-ng`. Unprivileged LXC also misses `/run/openrc/softlevel`. The bootstrap script handles all four (see script docs).

## Step 5 — CT: sing-box as VLESS Client (LAN Bridge)

Alpine's community repo has `sing-box` 1.12 but **does not have `xray`**. sing-box's Reality client is fully interoperable with an Xray server.

```bash
ssh "$PVE_HOST" "pct exec $CT_ID -- apk add --no-cache sing-box sing-box-openrc curl"
```

Copy `references/singbox-client.json` into `/etc/sing-box/config.json`, substitute the placeholders, and set `inbounds[0].listen` to `0.0.0.0` so other LAN hosts can reach it as `$CT_IP:10808`.

```bash
ssh "$PVE_HOST" "pct exec $CT_ID -- sh -c '
sing-box check -c /etc/sing-box/config.json
rc-update add sing-box default
rc-service sing-box start
ss -tlnp | grep :10808
'"
```

### sing-box 1.13 syntax migration

**1.13 removed the legacy inbound `sniff` / `sniff_override_destination` fields** ([migration doc](https://sing-box.sagernet.org/migration/#migrate-legacy-inbound-fields-to-rule-actions)). The `references/singbox-client.json` template is already 1.13-form (no inline `sniff`; `{ "action": "sniff" }` as a route rule). It also works on 1.12 — write once, deploy on both Alpine 1.12 and brew 1.13.

### Routing pitfall: do NOT use `geoip:cn → direct` if local DNS returns fake IPs

When the LAN runs Surge in TUN mode (or any setup that remaps DNS to a private range like `198.18.0.0/16`), an Xray/sing-box rule of `ip → direct for geoip:private` catches every resolved address and sends everything direct. Symptom: client log shows `app/dispatcher: taking detour [direct]` for every domain and remote endpoints in `198.18.x.x`. **Fix:** use `domainStrategy: "AsIs"` (Xray) or domain-only rules in sing-box so routing decides on the original domain before any DNS happens.

## Step 6 — Mac sing-box (Off-LAN Bridge)

The CT bridge is unreachable once the Mac leaves the home LAN. Mirror the same client on the Mac.

```bash
brew install sing-box
mkdir -p /opt/homebrew/etc/sing-box /opt/homebrew/var/lib/sing-box
# Copy references/singbox-client.json to $MAC_SINGBOX_CONF, substitute placeholders.
# Keep inbounds[0].listen = "127.0.0.1" (Mac is a single host, no LAN reach needed).
/opt/homebrew/opt/sing-box/bin/sing-box check -c "$MAC_SINGBOX_CONF"
brew services start sing-box
lsof -nP -iTCP -sTCP:LISTEN | grep ':10808'
```

The Mac sing-box reuses the **same UUID, public_key, and short_id** as the CT — Xray accepts both clients on one credential. Issue a separate UUID per device only if you need per-device revocation.

## Step 7 — Surge: TUN Bypass, Two Proxies, Fallback Group

Surge does not speak VLESS. Both bridges expose the tunnel as plain SOCKS5; Surge consumes whichever is reachable.

### Critical: bypass Surge TUN for the upstream `SERVER_IP`

When the Mac runs Surge in TUN mode, every outbound socket — including sing-box's TCP to `SERVER_IP:443` — is captured by utun. If a Surge MITM rule matches, the Reality handshake breaks with `x509: certificate signed by unknown authority` (symptom identical to a Step 2 server-side problem, but the cause is local).

Fix: exclude `SERVER_IP/32` from TUN entirely.

```ini
[General]
tun-excluded-routes = <existing CIDRs>, <SERVER_IP>/32
```

`tun-excluded-routes` accepts a comma-separated CIDR list. A static IP (Step 1) makes the entry stable; without it, every IP rotation needs a TUN-list edit.

### Add both bridges and a `fallback` group

**Always back up the live config first** — Surge subscribers pull whatever is at the URL on next interval:

```bash
ssh "$SURGE_HOST" "cp $SURGE_CONF_PATH ${SURGE_CONF_PATH}.bak.\$(date +%Y%m%d-%H%M%S)"
```

```ini
[Proxy]
# Rename the prior single AWS_JP to AWS_JP_LAN; add the local sibling.
# [Proxy] and [Proxy Group] share a namespace, so the new group named AWS_JP
# (below) replaces the old proxy named AWS_JP. Existing group references
# (Proxy, JP, AI, Reality, etc.) automatically resolve to the fallback group.
AWS_JP_LAN   = socks5, <CT_IP>, 10808, udp-relay=true
AWS_JP_Local = socks5, 127.0.0.1, 10808, udp-relay=true

[Proxy Group]
# Prefer LAN (faster, offloads Mac); drop to Local when LAN url-test fails.
AWS_JP = fallback, AWS_JP_LAN, AWS_JP_Local, url=http://cp.cloudflare.com/generate_204, interval=60, timeout=3
```

Notes:

- `udp-relay=true` is required for QUIC / HTTP/3 over SOCKS5.
- Surge MITM is irrelevant for SOCKS5 outbounds (Surge MITMs only direct TLS) — that's why Step 7's `tun-excluded-routes` matters for the upstream connection only.
- Do not chain `AWS_JP*` behind `underlying-proxy=` when the target is on LAN or localhost.
- Surge subscribers with `#!MANAGED-CONFIG ... interval=...` refresh on schedule; trigger now with `⌘R`.

## Step 8 — Verify

Test both bridges independently so a regression points at the right config.

```bash
# CT bridge (LAN side):
pct exec $CT_ID -- curl -s --max-time 10 --socks5-hostname 127.0.0.1:10808 https://ipinfo.io/json
curl -s --max-time 10 --socks5-hostname $CT_IP:10808 https://ipinfo.io/json     # from any LAN host

# Mac bridge (local side; requires tun-excluded-routes applied + Surge reloaded):
curl -s --max-time 10 --socks5-hostname 127.0.0.1:10808 https://ipinfo.io/json
```

All three must return `"ip": "<SERVER_IP>"` and the correct country. If `ipinfo.io` returns the LAN/Mac egress IP, traffic went DIRECT — recheck Step 5 routing pitfall (CT) or Step 7 `tun-excluded-routes` (Mac).

Always use `--socks5-hostname` (sends domain), not `--socks5` (resolves client-side first).

### Verifying the Surge `fallback` group

- On LAN: Surge should select `AWS_JP_LAN`. Confirm in the Surge dashboard's policy view.
- Disconnect from LAN (or block `$CT_IP` temporarily): within `interval` seconds the `AWS_JP` group flips to `AWS_JP_Local`. Surge resumes `AWS_JP_LAN` once it's reachable.

## Generate `vless://` Share Link

For mobile / GUI clients (v2rayN, Stash, Streisand, NekoBox):

```bash
scripts/vless-share-link.py \
  --server "$SERVER_IP" --uuid "$UUID" --pbk "$PBK" --sid "$SHORTID" \
  --sni www.microsoft.com --name "vless_jp_reality"
```

## Rules

- Never use Microsoft Update / Apple internal-CA hostnames as Reality `dest` — see Step 2.
- Probe Reality dest from the server, never from the client.
- Edit Surge `MANAGED-CONFIG` files via a local copy + diff + timestamped backup before pushing back.
- `put-instance-public-ports` is destructive (replaces ALL rules); use `open-instance-public-ports` for incremental adds.
- Attach a Static IP before distributing client configs — without one, every stop/start invalidates every client.
- LXC `pct create` defaults leave Alpine minirootfs without `lo`, `openrc`, or `ifupdown-ng` — the bootstrap script handles all of it.
- sing-box and Xray on the same `Reality{privateKey ↔ publicKey, shortId}` pair are interoperable; pick whichever client is in the target repo.
- For sing-box ≥1.13, drop legacy `sniff` inbound fields and use `{ "action": "sniff" }` route rule (the template already does).
- On a Mac running Surge in TUN mode, always add `SERVER_IP/32` to `tun-excluded-routes` before starting the local sing-box.

## Common Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| Client log: `x509: certificate signed by unknown authority` after TCP connect succeeds | Reality `dest` uses internal CA (Microsoft Update, Apple iCloud) — server falls back to forwarding the real cert which the client cannot validate | Probe with `scripts/reality-probe.sh`; pick a dest with publicly-trusted chain |
| Server log empty despite client errors | `loglevel: warning` hides Reality fallback events | Set `info`/`debug` temporarily; events go to journalctl, NOT `/var/log/xray/error.log` |
| `pct create` fails: `xz: File format not recognized` | Alpine minirootfs is gzip, file extension `.tar.xz` is wrong | Rename to `.tar.gz` |
| `rc-service` warns "you will get unpredictable results" | Missing `/run/openrc/softlevel` in LXC | `scripts/lxc-alpine-bootstrap.sh` writes a persistent `/etc/local.d/00-bootstrap.start` |
| SOCKS5 to `127.0.0.1:10808` from inside CT times out, listener visible in `ss` | `lo` not brought up in container | Same bootstrap script — `ip link set lo up && ip addr add 127.0.0.1/8 dev lo` |
| Routing always direct, log shows `[direct]` for every domain | Local DNS returns fake IPs (e.g. Surge TUN `198.18.x.x`) caught by `geoip:private/cn → direct` | Use `domainStrategy: "AsIs"`; remove IP-only direct rules |
| Lightsail UI has no ICMP option in firewall | Lightsail UI lists only TCP/UDP | Use `aws lightsail open-instance-public-ports --port-info protocol=icmp,...` |
| `openssl s_client` cert verifies but Reality still rejects | Cert issuer is publicly trusted but ALPN h2 not negotiated | Reject candidate; require both public CA AND ALPN h2 |
| sing-box `check` on Mac: `legacy inbound fields … removed in sing-box 1.13.0` | Brew has 1.13+; an old config has inline `sniff`/`sniff_override_destination` | Use `references/singbox-client.json` (1.13-compatible) |
| Mac sing-box: `x509: ...` despite known-good server config | Surge TUN intercepted the upstream and presented its own cert | Add `tun-excluded-routes = <SERVER_IP>/32` in Surge `[General]` |
| Surge `fallback` never flips back to LAN after returning home | `interval`/`timeout` too long, or url-test target itself routed via the dead member | Lower `interval` to 30–60s; use a url-test target not affected by the failing branch |
| Public IP changed silently after a stop/start | No Static IP attached | Attach Lightsail Static IP and refresh client configs |

## Verification Checklist Before Reporting Done

Server:
- [ ] `aws lightsail get-instance` shows `isStaticIp: True`; IP matches every client config
- [ ] `systemctl is-active xray` → `active`; `ss -tlnp | grep :443` shows `xray`
- [ ] `journalctl -u xray --since "5 min ago"` has NO `REALITY: processed invalid connection` lines

CT bridge:
- [ ] `rc-service sing-box status` → `started`
- [ ] `ss -tlnp` shows `0.0.0.0:10808` listening
- [ ] `curl --socks5-hostname $CT_IP:10808 https://ipinfo.io/json` from a third LAN host → returns `SERVER_IP`

Mac bridge:
- [ ] `brew services list | grep sing-box` → `started`
- [ ] `lsof -nP -iTCP -sTCP:LISTEN | grep ':10808'` → `sing-box` on `127.0.0.1`
- [ ] `curl --socks5-hostname 127.0.0.1:10808 https://ipinfo.io/json` on the Mac → returns `SERVER_IP`
- [ ] Surge config `tun-excluded-routes` includes `SERVER_IP/32`

Surge:
- [ ] Config diff applied; timestamped backup exists
- [ ] Both `AWS_JP_LAN` and `AWS_JP_Local` show in Surge UI policy list
- [ ] `AWS_JP` fallback group reports both members healthy on LAN; member-down test flips to `AWS_JP_Local` within `interval` seconds
- [ ] Subscribers reload (`⌘R`) and the new policy names show up

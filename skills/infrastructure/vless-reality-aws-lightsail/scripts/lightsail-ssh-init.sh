#!/usr/bin/env bash
# Fetch a one-shot Lightsail SSH credential and write a ready-to-use key,
# OpenSSH-cert, and known_hosts file in the current (or given) directory.
#
# The cert is valid for ~13 minutes; re-run to refresh.
#
# Usage:
#   lightsail-ssh-init.sh <instance-name> <region> [output-dir]
#
# After it returns, connect with:
#   ssh -i <out>/ec2 -o UserKnownHostsFile=<out>/known_hosts \
#       -o StrictHostKeyChecking=yes <user>@<ip>
#
# OpenSSH auto-loads <keyfile>-cert.pub. The filenames `ec2` and `ec2-cert.pub`
# are NOT decorative — mismatched names cause "Load key: invalid format".

set -euo pipefail

INSTANCE_NAME="${1:?instance name required}"
REGION="${2:?region required}"
OUTDIR="${3:-.}"

mkdir -p "$OUTDIR"
cd "$OUTDIR"

aws lightsail get-instance-access-details \
  --instance-name "$INSTANCE_NAME" --region "$REGION" \
  --protocol ssh --output json > .access.json

python3 - <<'PY'
import json
d = json.load(open('.access.json'))['accessDetails']
open('ec2', 'w').write(d['privateKey'])
open('ec2-cert.pub', 'w').write(d['certKey'])
with open('known_hosts', 'w') as f:
    for hk in d['hostKeys']:
        f.write(f"{d['ipAddress']} {hk['algorithm']} {hk['publicKey']}\n")
print(f"IP:   {d['ipAddress']}")
print(f"User: {d['username']}")
PY

chmod 600 ec2 ec2-cert.pub
rm .access.json

cat <<EOF

SSH ready (cert valid ~13 min). Try:
  ssh -i $OUTDIR/ec2 \\
      -o UserKnownHostsFile=$OUTDIR/known_hosts \\
      -o StrictHostKeyChecking=yes \\
      ec2-user@\$(awk '{print \$1; exit}' $OUTDIR/known_hosts)
EOF

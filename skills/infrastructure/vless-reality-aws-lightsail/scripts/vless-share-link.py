#!/usr/bin/env python3
"""Generate a vless:// share URI for VLESS+Reality+Vision.

Output is the canonical URI that v2rayN, Stash, Streisand, NekoBox, etc. import.

Example:
  vless-share-link.py \\
    --server 13.193.160.227 \\
    --uuid 8450173e-fb8a-4389-ae7c-dd9f3da1b20c \\
    --pbk  qzhsbiwKaL3x4lGlX62FOn8gRammcmqS-nTS_UtttQA \\
    --sid  c5ba9beb8a5d88d3 \\
    --sni  www.microsoft.com \\
    --name vless_jp_reality
"""
from __future__ import annotations
import argparse
import urllib.parse


def build_link(args: argparse.Namespace) -> str:
    params = {
        "type": "tcp",
        "security": "reality",
        "encryption": "none",
        "pbk": args.pbk,
        "fp": args.fp,
        "sni": args.sni,
        "sid": args.sid,
        "spx": "/",
        "flow": "xtls-rprx-vision",
    }
    qs = "&".join(
        f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in params.items()
    )
    return (
        f"vless://{args.uuid}@{args.server}:{args.port}?{qs}"
        f"#{urllib.parse.quote(args.name)}"
    )


def main() -> None:
    p = argparse.ArgumentParser(
        description="Generate a vless:// share URI for VLESS+Reality+Vision."
    )
    p.add_argument("--server", required=True, help="Server IP or hostname")
    p.add_argument("--port", type=int, default=443)
    p.add_argument("--uuid", required=True)
    p.add_argument("--pbk", required=True, help="Reality public key (URL-safe base64)")
    p.add_argument("--sid", required=True, help="Reality short ID (hex)")
    p.add_argument(
        "--sni",
        default="www.microsoft.com",
        help="Reality SNI — must match server's serverNames",
    )
    p.add_argument("--fp", default="chrome", help="uTLS fingerprint")
    p.add_argument(
        "--name", default="vless-reality", help="Friendly client-side name"
    )
    args = p.parse_args()
    print(build_link(args))


if __name__ == "__main__":
    main()

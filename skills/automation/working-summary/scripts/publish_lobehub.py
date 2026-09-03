#!/usr/bin/env python3
"""Publish the working summary markdown into a LobeHub knowledge base via `lh`."""
from __future__ import annotations
import argparse
import json
import os
import re
import subprocess
import sys


def lh(args, env):
    r = subprocess.run(["lh", *args], capture_output=True, text=True, env=env)
    if r.returncode != 0:
        sys.exit(f"lh {' '.join(args)} failed:\n{r.stderr.strip() or r.stdout.strip()}")
    return r.stdout


def kb_items(kb, env):
    return json.loads(lh(["kb", "view", kb, "--json"], env)).get("files", [])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--kb", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--md", required=True, help="markdown file, or - for stdin")
    p.add_argument("--workspace")
    p.add_argument("--folder")
    p.add_argument("--slug", help="workspace slug, used only to build the returned URL")
    p.add_argument("--on-duplicate", choices=["fail", "replace", "allow"], default="fail")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()

    env = dict(os.environ)
    if a.workspace:
        env["LOBEHUB_WORKSPACE_ID"] = a.workspace
    if not env.get("LOBEHUB_WORKSPACE_ID"):
        sys.exit("no workspace scope: pass --workspace or set LOBEHUB_WORKSPACE_ID")

    content = sys.stdin.read() if a.md == "-" else open(a.md, encoding="utf-8").read()

    existing = kb_items(a.kb, env)
    dup = [f for f in existing if f["name"] == a.title and f["fileType"] != "custom/folder"]
    if dup and a.on_duplicate == "fail":
        sys.exit(f"document already exists: {dup[0]['id']} ({a.title})")

    parent = None
    if a.folder:
        hit = [f for f in existing if f["fileType"] == "custom/folder" and f["name"] == a.folder]
        if hit:
            parent = hit[0]["id"]
        elif not a.dry_run:
            parent = re.search(r"(docs_\w+)", lh(["kb", "mkdir", a.kb, "-n", a.folder], env)).group(1)

    if a.dry_run:
        print(json.dumps({"kb": a.kb, "title": a.title, "folder": a.folder, "parent": parent,
                          "bytes": len(content.encode()), "duplicates": [f["id"] for f in dup]},
                         ensure_ascii=False))
        return

    args = ["kb", "create-doc", a.kb, "-t", a.title, "-c", content]
    if parent:
        args += ["--parent", parent]
    doc_id = re.search(r"(docs_\w+)", lh(args, env)).group(1)

    if dup and a.on_duplicate == "replace":
        lh(["kb", "remove-files", a.kb, "--ids", *[f["id"] for f in dup], "--yes"], env)

    print(json.dumps({
        "id": doc_id,
        "title": a.title,
        "parent": parent,
        "url": f"https://app.lobehub.com/{a.slug + '/' if a.slug else ''}resource/library/{a.kb}?file={doc_id}",
    }, ensure_ascii=False))


main()

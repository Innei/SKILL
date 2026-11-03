#!/usr/bin/env python3
"""Project the full weekly report onto the editor summary (KB document).

The full report is one markdown file: narrative sections, then an `## 附录`
section holding the repo table, the PR list and the Linear snapshot. Editors
(LobeHub KB documents) receive the narrative only — the appendix is what the
HTML version's collapsible block is for.

Figures: `![caption](ci-lint.jpg)` is kept when `--upload-images` is given, by
uploading the file with `lh file upload` (LobeHub CLI ≥ 0.0.72) and pointing the
image at `https://app.lobehub.com/f/…`; without it every figure is dropped,
because an editor document cannot resolve a path on this machine.

    render_md.py --md report.md --title "Innei 周报 — 2026-W45" \\
                 --url https://reports.innei.dev/2026-11-w45.html \\
                 --upload-images -o summary.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

APPENDIX = re.compile(r"^##\s+(附录|appendix)\b", re.I)
H1 = re.compile(r"^#\s+.*$", re.M)
IMAGE = re.compile(r"^(\s*)!\[([^\]]*)\]\(([^)]+)\)\s*$", re.M)

CACHE = Path.home() / ".config" / "working-summary" / "image-cache.json"


def _cache_key(path: Path) -> str:
    st = path.stat()
    digest = hashlib.sha1(f"{path.resolve()}:{st.st_size}:{int(st.st_mtime)}".encode()).hexdigest()
    return digest[:16]


def upload_image(path: Path, env: dict) -> str | None:
    """Upload once per file state; reuse the cached URL on later runs."""
    cache: dict = {}
    if CACHE.exists():
        try:
            cache = json.loads(CACHE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cache = {}
    key = _cache_key(path)
    if cache.get(key):
        return cache[key]

    r = subprocess.run(
        ["lh", "file", "upload", "--file", str(path), "--json"],
        capture_output=True, text=True, env=env,
    )
    if r.returncode != 0:
        print(f"upload failed: {path.name}: {(r.stderr or r.stdout).strip()[:200]}", file=sys.stderr)
        return None
    try:
        url = json.loads(r.stdout).get("url")
    except json.JSONDecodeError:
        print(f"upload returned non-JSON for {path.name}", file=sys.stderr)
        return None
    if url:
        cache[key] = url
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    return url


def project(
    text: str,
    title: str,
    url: str | None,
    *,
    assets_dir: Path | None = None,
    upload: bool = False,
    env: dict | None = None,
) -> str:
    kept: list[str] = []
    for line in text.splitlines():
        if APPENDIX.match(line):
            break
        kept.append(line)
    body = "\n".join(kept).rstrip()

    def keep_image(m: re.Match) -> str:
        indent, alt, src = m.group(1), m.group(2), m.group(3)
        if src.startswith(("http://", "https://", "data:")):
            return m.group(0)
        if not upload:
            return ""  # editor documents cannot resolve a local path
        local = (assets_dir or Path(".")) / src
        if not local.is_file():
            print(f"figure not found, dropped: {src}", file=sys.stderr)
            return ""
        remote = upload_image(local, env or dict(os.environ))
        return f"{indent}![{alt}]({remote})" if remote else ""

    body = IMAGE.sub(keep_image, body)
    body = re.sub(r"\n{3,}", "\n\n", body)

    if title:
        if H1.search(body):
            body = H1.sub(f"# {title}", body, count=1)
        else:
            body = f"# {title}\n\n{body}"

    if url:
        body += (
            "\n\n---\n\n"
            f"全文（含证据截图、附录：仓库分布 / PR 清单 / Linear 快照）→ {url}\n"
        )
    return body + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--md", required=True, help="full report markdown, or - for stdin")
    p.add_argument("--title", default="", help="document title replacing the H1")
    p.add_argument("--url", help="public HTML url appended as the full-report line")
    p.add_argument("--upload-images", action="store_true",
                   help="upload figures via `lh file upload` and keep them inline")
    p.add_argument("--assets", help="directory relative image sources resolve against (default: the markdown's)")
    p.add_argument("-o", "--out", default="-")
    a = p.parse_args()

    text = sys.stdin.read() if a.md == "-" else open(a.md, encoding="utf-8").read()
    assets = Path(a.assets).expanduser() if a.assets else (
        Path(a.md).expanduser().parent if a.md != "-" else None
    )
    out = project(text, a.title, a.url, assets_dir=assets, upload=a.upload_images)

    if a.out == "-":
        sys.stdout.write(out)
    else:
        open(a.out, "w", encoding="utf-8").write(out)
        print(f"wrote {a.out} ({len(out)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

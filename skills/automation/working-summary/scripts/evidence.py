#!/usr/bin/env python3
"""The evidence ledger: measurements that do not come from GitHub or Linear.

A weekly report's best numbers often arrive out of band — a CI run comparison,
a Cloudflare zone export, a billing screenshot, taken at 01:59 the day after
the window closed. They must not be lost, and they must not be smuggled into a
report whose window they fall outside of.

So they live here, one JSON object per line, in
`~/.config/working-summary/evidence.jsonl`, with their images beside them:

    {"date": "2026-11-02", "title": "type-check 换 tsrs",
     "detail": "cloud 冷 Bun 122–171s → ~33s；lobe-chat 冷 11.6s → 35–50s",
     "source": "screenshot 2026-11-02 01:59",
     "image": "evidence/2026-11-02-tsrs.jpg"}

`collect.py` reads the entries whose `date` falls inside the report window and
returns them as `evidence`; anything newer stays pending for the next run.

    evidence.py --list
    evidence.py --add --date 2026-11-02 --title "..." --detail "..." \
                --image ~/Desktop/shot.png --source "screenshot"
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path.home() / ".config" / "working-summary"
LEDGER = ROOT / "evidence.jsonl"
IMAGE_DIR = ROOT / "evidence"


def load_evidence(start: str, end: str, ledger: Path | None = None) -> list[dict]:
    """Entries dated inside [start, end], oldest first."""
    path = ledger or LEDGER
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        day = str(entry.get("date") or "")
        if start <= day <= end:
            out.append(entry)
    out.sort(key=lambda e: str(e.get("date") or ""))
    return out


def append_evidence(entry: dict, ledger: Path | None = None) -> Path:
    path = ledger or LEDGER
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="print the ledger")
    ap.add_argument("--add", action="store_true", help="append an entry")
    ap.add_argument("--date", help="YYYY-MM-DD the measurement belongs to")
    ap.add_argument("--title", help="what was measured")
    ap.add_argument("--detail", help="the numbers, with their scenarios")
    ap.add_argument("--source", default="", help="where it came from (run id, snapshot, screenshot)")
    ap.add_argument("--image", help="screenshot to copy next to the ledger")
    a = ap.parse_args()

    if a.list or not a.add:
        for entry in (load_evidence("0000-00-00", "9999-99-99")):
            print(f"{entry.get('date')}  {entry.get('title')}")
            print(f"    {entry.get('detail')}")
            if entry.get("image"):
                print(f"    image: {entry['image']}")
        return 0

    if not (a.date and a.title and a.detail):
        sys.exit("--add needs --date, --title and --detail")
    date.fromisoformat(a.date)  # raises on a malformed date

    image = ""
    if a.image:
        src = Path(a.image).expanduser()
        if not src.is_file():
            sys.exit(f"image not found: {src}")
        IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        dest = IMAGE_DIR / f"{a.date}-{src.stem}{src.suffix}"
        shutil.copyfile(src, dest)
        image = str(dest)

    entry = {
        "date": a.date,
        "title": a.title,
        "detail": a.detail,
        "source": a.source,
        "image": image,
    }
    path = append_evidence(entry)
    print(json.dumps({"ledger": str(path), **entry}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

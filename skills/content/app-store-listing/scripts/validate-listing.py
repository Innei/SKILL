#!/usr/bin/env python3
import re
import sys
from pathlib import Path

LIMITS = {
    "名称": 30,
    "副标题": 30,
    "宣传文本": 170,
    "关键词": 100,
    "Name": 30,
    "Subtitle": 30,
    "Promotional Text": 170,
    "Keywords": 100,
}

BLOCK = re.compile(
    r"\*\*(名称|副标题|宣传文本|关键词|Name|Subtitle|Promotional Text|Keywords)\*\*"
    r".*?\n```\n(.*?)\n```",
    re.S,
)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: validate-listing.py <listing.md>")
    text = Path(sys.argv[1]).read_text()
    blocks = BLOCK.findall(text)
    if not blocks:
        raise SystemExit("no labeled listing fields found")
    failed = False
    for name, body in blocks:
        n = len(body)
        lim = LIMITS[name]
        ok = n <= lim
        extra = ""
        if name in {"关键词", "Keywords"} and ", " in body:
            ok = False
            extra = " spaces-after-commas"
        print(f"{name:20} {n:4}/{lim:<4} {'OK' if ok else 'FAIL'}{extra}")
        if not ok:
            failed = True
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

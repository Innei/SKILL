#!/usr/bin/env python3
"""Insert or check a skill row inside a README domain table.

Line-based: never use DOTALL with `|.*` — that swallows the rest of the file.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

DOMAINS = ("infrastructure", "automation", "writing", "research", "content")
ROW_RE = re.compile(r"\| \[`([^`]+)`\]")
SEP_RE = re.compile(r"\| [-:]+ \| [-:]+ \|")


def heading_for(domain: str) -> str:
    return domain.capitalize()


def find_table(lines: list[str], heading: str) -> tuple[int, int, int]:
    header_at = None
    needle = f"### {heading}"
    for i, line in enumerate(lines):
        if line.rstrip("\n") == needle:
            header_at = i
            break
    if header_at is None:
        raise SystemExit(f"error: domain heading '{needle}' not found")

    sep = None
    for j in range(header_at + 1, len(lines)):
        stripped = lines[j].strip()
        if stripped.startswith("## ") or (
            stripped.startswith("### ") and j != header_at
        ):
            break
        if SEP_RE.match(stripped):
            sep = j
            break
    if sep is None:
        raise SystemExit(f"error: domain table for '{heading}' not found")

    start = sep + 1
    end = start
    while end < len(lines) and lines[end].lstrip().startswith("|"):
        end += 1
    return header_at, start, end


def row_names(lines: list[str], start: int, end: int) -> list[str]:
    names = []
    for line in lines[start:end]:
        m = ROW_RE.match(line.strip())
        if m:
            names.append(m.group(1))
    return names


def make_row(domain: str, name: str, purpose: str) -> str:
    return f"| [`{name}`](skills/{domain}/{name}/SKILL.md) | {purpose} |\n"


def sort_key(line: str) -> str:
    m = ROW_RE.match(line.strip())
    return m.group(1) if m else line


def insert(text: str, domain: str, name: str, purpose: str) -> str:
    if domain not in DOMAINS:
        raise SystemExit(
            f"error: invalid domain '{domain}' (expected one of: {'|'.join(DOMAINS)})"
        )
    lines = text.splitlines(keepends=True)
    _, start, end = find_table(lines, heading_for(domain))
    existing = lines[start:end]
    if name in row_names(lines, start, end):
        print(f"README row for {name} already present under ### {heading_for(domain)}")
        return text
    existing.append(make_row(domain, name, purpose))
    existing.sort(key=sort_key)
    return "".join(lines[:start] + existing + lines[end:])


def check(text: str, domain: str, name: str) -> bool:
    lines = text.splitlines(keepends=True)
    _, start, end = find_table(lines, heading_for(domain))
    return name in row_names(lines, start, end)


def _self_test() -> None:
    sample = (
        "# Root\n\n"
        "### Automation\n\n"
        "> Repeated shell workflows.\n\n"
        "| Skill | Purpose |\n"
        "| ----- | ------- |\n"
        "| [`aaa`](skills/automation/aaa/SKILL.md) | A |\n"
        "\n"
        "### Content\n\n"
        "| Skill | Purpose |\n"
        "| ----- | ------- |\n"
        "| [`bbb`](skills/content/bbb/SKILL.md) | B |\n"
        "\n"
        "## After\n\n"
        "prose that must survive\n"
    )
    out = insert(sample, "automation", "zzz", "Z")
    assert "### Content" in out, out
    assert "## After" in out, out
    assert "prose that must survive" in out, out
    assert "[`zzz`](skills/automation/zzz/SKILL.md)" in out, out
    assert check(out, "automation", "zzz")
    assert check(out, "content", "bbb")
    assert not check(out, "automation", "bbb")

    again = insert(out, "automation", "zzz", "Z")
    assert again == out

    empty = (
        "### Research\n\n"
        "| Skill | Purpose |\n"
        "| ----- | ------- |\n"
        "\n"
        "### Writing\n\n"
        "| Skill | Purpose |\n"
        "| ----- | ------- |\n"
    )
    filled = insert(empty, "research", "chat-export-report", "Analyze chats")
    assert check(filled, "research", "chat-export-report")
    assert "| Skill | Purpose |" in filled.split("### Writing")[1]
    print("self-test ok")


def main(argv: list[str]) -> int:
    if len(argv) >= 1 and argv[0] == "--self-test":
        _self_test()
        return 0
    if len(argv) < 1:
        sys.stderr.write(
            "usage: readme-domain-table.py insert <README> <domain> <name> <purpose>\n"
            "       readme-domain-table.py check  <README> <domain> <name>\n"
            "       readme-domain-table.py --self-test\n"
        )
        return 2
    cmd = argv[0]
    if cmd == "insert":
        if len(argv) != 5:
            sys.stderr.write(
                "usage: readme-domain-table.py insert <README> <domain> <name> <purpose>\n"
            )
            return 2
        path = Path(argv[1])
        path.write_text(insert(path.read_text(), argv[2], argv[3], argv[4]))
        print(f"inserted README row under ### {heading_for(argv[2])}")
        return 0
    if cmd == "check":
        if len(argv) != 4:
            sys.stderr.write(
                "usage: readme-domain-table.py check <README> <domain> <name>\n"
            )
            return 2
        path = Path(argv[1])
        if check(path.read_text(), argv[2], argv[3]):
            return 0
        sys.stderr.write(
            f"README.md missing row for `{argv[3]}` inside ### {heading_for(argv[2])}\n"
        )
        return 1
    sys.stderr.write(f"error: unknown command '{cmd}'\n")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

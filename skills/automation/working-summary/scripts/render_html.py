#!/usr/bin/env -S uv run --quiet --with markdown-it-py --with beautifulsoup4 python
"""Render a working-summary markdown report into themed HTML.

Reads:
  - markdown report (required) — the synthesized weekly/period report
  - collect.py JSON (optional) — for meta grid + stats enrichment

Writes:
  - single self-contained HTML to stdout or --out path
"""
from __future__ import annotations

import argparse
import html as htmllib
import json
import os
import re
import sys
from pathlib import Path
from string import Template
from typing import Optional

from bs4 import BeautifulSoup, NavigableString, Tag
from markdown_it import MarkdownIt

HERE = Path(__file__).resolve().parent
TEMPLATE_PATH = HERE / "templates" / "report.html"
sys.path.insert(0, str(HERE))

from pr_stats import CANONICAL, build_stats  # noqa: E402

CONVENTIONAL = r"feat|fix|refactor|perf|build|ci|chore|docs|test|style|revert"


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--markdown", "-m", required=True, help="Markdown file path or - for stdin")
    p.add_argument("--json", "-j", default=None, help="Optional collect.py JSON for enrichment")
    p.add_argument("--lang", default="zh-CN")
    p.add_argument("--title", default=None, help="Browser tab title (defaults to h1)")
    p.add_argument("--out", "-o", default="-", help="Output HTML path or - for stdout")
    p.add_argument("--user", default=None, help="Shell prompt user (defaults to $USER)")
    p.add_argument("--host", default="reports", help="Shell prompt host")
    return p.parse_args()


# -------------------- IO --------------------

def read_text(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).expanduser().read_text(encoding="utf-8")


def write_out(path: str, content: str) -> None:
    if path == "-":
        sys.stdout.write(content)
    else:
        Path(path).expanduser().write_text(content, encoding="utf-8")
        print(f"wrote {path}", file=sys.stderr)


# -------------------- markdown --------------------

def md_to_html(text: str) -> str:
    md = MarkdownIt("commonmark", {"html": True, "linkify": True, "breaks": False})
    md.enable(["table", "strikethrough"])
    return md.render(text)


# -------------------- header extraction --------------------

META_PAT_PERIOD = re.compile(r"(\d{4}-\d{2}-\d{2})\s*[~～]\s*(\d{4}-\d{2}-\d{2})")
META_PAT_WORKDAYS = re.compile(r"(\d+)\s*工作日")
META_PAT_HOLIDAYS = re.compile(r"(\d+)\s*节假日")
META_PAT_REPOS = re.compile(r"仓库\s*(\d+)")
META_PAT_AUTHOR = re.compile(r"作者\s*([^\s·,，、]+)")
META_PAT_PRS_MERGED = re.compile(r"合入\s*(\d+)\s*个?\s*PR|(\d+)\s*个\s*PR\s*·|^(\d+)\s*PRs?", re.MULTILINE)


def extract_header(soup: BeautifulSoup) -> tuple[dict, Optional[str]]:
    """Pull meta from the first strong-bearing <p> and optional plain blockquote summary.

    Removes the consumed nodes from the tree. Returns (meta_dict, shipped_html_or_none).
    Stops at the first <h2>.
    """
    meta: dict = {}
    shipped: Optional[str] = None
    meta_texts: list[str] = []

    root_children = list(soup.children)
    for node in root_children:
        if not isinstance(node, Tag):
            continue
        if node.name == "h2":
            break
        if node.name == "h1":
            continue  # h1 handled separately
        if node.name == "p" and node.find("strong"):
            meta_texts.append(node.get_text(" ", strip=True))
            node.decompose()
            continue
        if node.name == "blockquote":
            first_p = node.find("p")
            first_text = first_p.get_text() if first_p else node.get_text()
            if re.match(r"\s*\[!\w+\]", first_text):
                continue  # obsidian callout — leave for convert_callouts
            if shipped is None and first_p is not None:
                shipped = "".join(str(c) for c in first_p.contents)
            node.decompose()
            continue
        if node.name == "hr":
            node.decompose()
            continue

    meta_blob = " ".join(meta_texts)
    if (m := META_PAT_PERIOD.search(meta_blob)):
        meta["period"] = (m.group(1), m.group(2))
    if (m := META_PAT_WORKDAYS.search(meta_blob)):
        meta["workdays"] = int(m.group(1))
    if (m := META_PAT_HOLIDAYS.search(meta_blob)):
        meta["holidays"] = int(m.group(1))
    if (m := META_PAT_REPOS.search(meta_blob)):
        meta["repos"] = int(m.group(1))
    if (m := META_PAT_AUTHOR.search(meta_blob)):
        meta["author"] = m.group(1)

    if shipped:
        text_only = re.sub(r"<[^>]+>", "", shipped)
        if (m := re.search(r"(\d+)\s*个\s*PR", text_only)):
            meta.setdefault("prs", int(m.group(1)))
        if (m := re.search(r"(\d+)\s*个\s*开放", text_only)):
            meta.setdefault("prs_open", int(m.group(1)))

    return meta, shipped


def meta_from_json(collect: dict) -> dict:
    meta: dict = {}
    rng = collect.get("range", {})
    if rng.get("start") and rng.get("end"):
        meta["period"] = (rng["start"], rng["end"])
    if "workdays" in rng:
        meta["workdays"] = rng["workdays"]
    if "holidays" in rng:
        meta["holidays"] = rng["holidays"]
    gh = collect.get("github", {}) or {}
    active = [r for r, data in gh.items() if any((data.get(k) for k in ("prs_merged", "commits", "prs_open", "issues")))]
    meta["repos"] = len(active)
    meta["prs"] = sum(len(d.get("prs_merged") or []) for d in gh.values())
    meta["commits"] = sum(len(d.get("commits") or []) for d in gh.values())
    meta["author"] = (collect.get("config") or {}).get("author") or meta.get("author")
    return meta


# -------------------- post-process passes --------------------

def strip_top_hrs(soup: BeautifulSoup) -> None:
    for hr in list(soup.find_all("hr")):
        hr.decompose()


def convert_callouts(soup: BeautifulSoup) -> None:
    """Obsidian `> [!kind]` blockquotes → <div class="callout kind">."""
    for bq in list(soup.find_all("blockquote")):
        first_p = bq.find("p")
        if not first_p:
            continue
        raw = first_p.get_text()
        m = re.match(r"\s*\[!(\w+)\](.*)", raw, re.DOTALL)
        if not m:
            continue
        kind = m.group(1).lower()
        div = soup.new_tag("div")
        div["class"] = f"callout {kind}"
        label = soup.new_tag("span")
        label["class"] = "label"
        label.string = kind
        div.append(label)

        # Strip the [!kind] token from the first text node of first_p
        tn = first_p.find(string=True)
        if tn is not None:
            tn.replace_with(re.sub(r"\s*\[!\w+\]\s*", "", str(tn), count=1))

        for child in list(bq.children):
            div.append(child.extract())
        bq.replace_with(div)


def wrap_repos_into_details(soup: BeautifulSoup) -> None:
    for h2 in list(soup.find_all("h2")):
        text = h2.get_text()
        if "仓库" not in text and not re.search(r"per[- ]?repo|repositor", text, re.I):
            continue
        h3_list: list[Tag] = []
        for sib in h2.find_next_siblings():
            if sib.name == "h2":
                break
            if sib.name == "h3":
                h3_list.append(sib)
        first = True
        for h3 in h3_list:
            details = soup.new_tag("details")
            if first:
                details["open"] = ""
                first = False
            summary = soup.new_tag("summary")

            em = h3.find("em")
            count_text = ""
            if em:
                count_text = em.get_text(strip=True).strip("()")
                em.extract()
            name = h3.get_text(" ", strip=True)
            summary.append(NavigableString(name))
            if count_text:
                cs = soup.new_tag("span")
                cs["class"] = "count"
                cs.string = count_text
                summary.append(cs)

            copy_btn = soup.new_tag("button")
            copy_btn["class"] = "copy-btn print-hide"
            copy_btn.string = "copy"
            summary.append(copy_btn)
            details.append(summary)

            body = soup.new_tag("div")
            body["class"] = "details-body"
            following: list[Tag] = []
            for sib in h3.find_next_siblings():
                if sib.name in ("h2", "h3"):
                    break
                following.append(sib)
            for n in following:
                body.append(n.extract())
            details.append(body)
            h3.replace_with(details)


def _slug_chunk(text: str) -> str:
    ascii_part = re.sub(r"[^a-zA-Z0-9\-_]+", "-", text)
    ascii_part = re.sub(r"-+", "-", ascii_part).strip("-").lower()
    return ascii_part


def wrap_sections(soup: BeautifulSoup) -> None:
    top_h2s = [n for n in soup.children if isinstance(n, Tag) and n.name == "h2"]
    for idx, h2 in enumerate(top_h2s, 1):
        section = soup.new_tag("section")
        slug = _slug_chunk(h2.get_text()) or f"sec-{idx}"
        section["id"] = slug
        h2.insert_before(section)
        section.append(h2.extract())
        for sib in list(section.find_next_siblings()):
            if isinstance(sib, Tag) and sib.name == "h2":
                break
            section.append(sib.extract())


def add_commit_tags(soup: BeautifulSoup) -> None:
    """Detect conventional-commit prefix in any <code> inside the li.

    Many li's have inline code (e.g. `LOADING_FLAT`) before the raw PR title,
    so we scan all code descendants and take the first conventional match.
    """
    tag_re = re.compile(rf"^({CONVENTIONAL})(?:\s*[\(:!]|\s+)")
    for li in soup.find_all("li"):
        kind: Optional[str] = None
        for code in li.find_all("code"):
            m = tag_re.match(code.get_text())
            if m:
                kind = m.group(1).lower()
                break
        if not kind:
            continue
        tag = soup.new_tag("span")
        tag["class"] = f"tag {kind}"
        tag.string = kind
        li.insert(0, tag)
        li.insert(1, NavigableString(" "))


def assign_h3_ids(soup: BeautifulSoup) -> None:
    for section in soup.find_all("section"):
        sid = section.get("id", "sec")
        for i, h3 in enumerate(section.find_all("h3"), 1):
            if h3.find_parent("details"):
                continue
            label = _slug_chunk(h3.get_text())
            h3["id"] = f"{sid}-{label or i}"


def build_toc(soup: BeautifulSoup) -> str:
    lines: list[str] = []
    for section in soup.find_all("section"):
        h2 = section.find("h2")
        if not h2:
            continue
        lines.append(
            f'<li><a href="#{section["id"]}">{htmllib.escape(h2.get_text(strip=True))}</a></li>'
        )
        for h3 in section.find_all("h3"):
            if h3.find_parent("details") or not h3.get("id"):
                continue
            lines.append(
                f'<li class="sub"><a href="#{h3["id"]}">{htmllib.escape(h3.get_text(strip=True))}</a></li>'
            )
    return "\n      ".join(lines)


# -------------------- meta grid / stats --------------------

def render_meta_grid(meta: dict) -> str:
    cells: list[tuple[str, str, str]] = []
    if meta.get("period"):
        start, end = meta["period"]
        cells.append(("Period", f"{start[5:]} – {end[5:]}", ""))
    if "workdays" in meta:
        unit = f"/ {meta.get('holidays', 0)} 节" if "holidays" in meta else ""
        cells.append(("Workdays", str(meta["workdays"]), unit))
    if meta.get("repos") is not None:
        cells.append(("Repos Active", str(meta["repos"]), ""))
    if "prs" in meta:
        unit = f"· {meta['commits']} commits" if "commits" in meta else ""
        cells.append(("PRs Merged", str(meta["prs"]), unit))
    if not cells:
        return ""
    parts = []
    for k, v, u in cells:
        unit_html = f'<span class="unit">{htmllib.escape(u)}</span>' if u else ""
        parts.append(
            f'<div><div class="k">{htmllib.escape(k)}</div>'
            f'<div class="v">{htmllib.escape(v)}{unit_html}</div></div>'
        )
    return '<div class="meta-grid">' + "".join(parts) + "</div>"


def resolve_stats(collect: Optional[dict]) -> dict:
    if not collect:
        return {"prs_merged": 0, "by_type": {}, "by_repo": []}
    stats = collect.get("stats")
    if isinstance(stats, dict) and stats.get("by_repo") is not None:
        return stats
    return build_stats(collect.get("github") or {})


def render_stats(stats: dict) -> str:
    if not stats or not stats.get("prs_merged"):
        return ""
    by_type = stats.get("by_type") or {}
    pills = []
    for key in CANONICAL:
        n = by_type.get(key)
        if not n:
            continue
        pills.append(
            f'<span class="pill {htmllib.escape(key)}">'
            f"<b>{n}</b> {htmllib.escape(key)}</span>"
        )
    pills_html = f'<div class="pills">{"".join(pills)}</div>' if pills else ""

    repos = stats.get("by_repo") or []
    max_prs = max((row.get("prs") or 0 for row in repos), default=0) or 1
    rows = []
    for row in repos:
        prs = row.get("prs") or 0
        if prs <= 0:
            continue
        outer = max(6, int(round(100 * prs / max_prs)))
        segs = []
        mix = row.get("by_type") or {}
        for key in CANONICAL:
            n = mix.get(key) or 0
            if not n:
                continue
            width = 100.0 * n / prs
            segs.append(
                f'<i class="seg {htmllib.escape(key)}" style="width:{width:.2f}%" '
                f'title="{htmllib.escape(key)} {n}"></i>'
            )
        rows.append(
            f'<div class="row">'
            f'<span class="name">{htmllib.escape(row.get("repo") or "")}</span>'
            f'<span class="barwrap"><span class="stack" style="width:{outer}%">'
            f'{"".join(segs)}</span></span>'
            f'<span class="num">{prs}</span>'
            f"</div>"
        )
    return (
        '<section id="stats">\n'
        "  <h2>附：活动构成</h2>\n"
        f"  {pills_html}\n"
        '  <div class="stats">\n    '
        + "\n    ".join(rows)
        + "\n  </div>\n</section>"
    )


# -------------------- prompt line --------------------

def build_prompt_line(user: str, host: str, meta: dict) -> str:
    period = meta.get("period")
    args = f"--from {period[0]} --to {period[1]}" if period else ""
    return (
        f'<span class="user">{htmllib.escape(user)}</span>'
        f"@"
        f'<span class="host">{htmllib.escape(host)}</span>'
        f":~/reports$ working-summary {htmllib.escape(args)}"
    )


# -------------------- main --------------------

def main() -> int:
    args = parse_args()
    md_text = read_text(args.markdown)

    collect: Optional[dict] = None
    if args.json:
        collect = json.loads(Path(args.json).expanduser().read_text(encoding="utf-8"))

    # 1. Markdown → HTML fragment
    html_body = md_to_html(md_text)
    soup = BeautifulSoup(html_body, "html.parser")

    # 2. Extract h1 title
    h1 = soup.find("h1")
    report_title = h1.get_text(strip=True) if h1 else "工作总结"
    if h1:
        h1.decompose()

    # 3. Extract meta from header; optionally override with JSON
    md_meta, shipped = extract_header(soup)
    if collect:
        merged = meta_from_json(collect)
        for k, v in md_meta.items():
            merged.setdefault(k, v)
        meta = merged
    else:
        meta = md_meta

    # 4. Drop stray top-level HRs
    strip_top_hrs(soup)

    # 5. Convert obsidian callouts
    convert_callouts(soup)

    # 6. Per-repo sections → <details>
    wrap_repos_into_details(soup)

    # 7. Wrap each h2 in <section>
    wrap_sections(soup)

    # 8. Assign h3 ids (for TOC sub-items)
    assign_h3_ids(soup)

    # 9. Add conventional-commit tags to list items
    add_commit_tags(soup)

    # 10. Optional: prepend shipped callout at top of first section
    if shipped:
        first_section = soup.find("section")
        if first_section:
            callout = soup.new_tag("div")
            callout["class"] = "callout success print-hide"
            label = soup.new_tag("span")
            label["class"] = "label"
            label.string = "shipped"
            callout.append(label)
            shipped_p = BeautifulSoup(f"<p>{shipped}</p>", "html.parser")
            callout.append(shipped_p)
            first_h2 = first_section.find("h2")
            if first_h2:
                first_h2.insert_after(callout)

    # 11. TOC
    toc_html = build_toc(soup)

    # 12. Meta grid
    meta_grid_html = render_meta_grid(meta)

    stats_html = render_stats(resolve_stats(collect))

    # 14. Prompt line
    user = args.user or meta.get("author") or os.environ.get("USER", "user")
    prompt_line = build_prompt_line(user, args.host, meta)

    # 15. Fill template
    tpl = Template(TEMPLATE_PATH.read_text(encoding="utf-8"))
    type_steps = max(len(report_title), 10)
    html = tpl.safe_substitute(
        lang=args.lang,
        title=htmllib.escape(args.title or report_title),
        report_title=htmllib.escape(report_title),
        prompt_line=prompt_line,
        meta_grid=meta_grid_html,
        toc=toc_html,
        body=str(soup),
        stats=stats_html,
        type_steps=str(type_steps),
    )

    write_out(args.out, html)
    return 0


if __name__ == "__main__":
    sys.exit(main())

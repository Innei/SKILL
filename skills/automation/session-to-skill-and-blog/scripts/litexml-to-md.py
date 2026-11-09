#!/usr/bin/env python3
import sys
import xml.etree.ElementTree as ET

DROP = {
    "img", "image", "embed", "excalidraw", "mermaid", "dynamic", "video",
    "audio", "iframe", "hr", "meta", "state", "summary",
}
HEADINGS = {f"h{n}": n for n in range(1, 7)}
LISTS = {"ul", "ol"}
BLOCK = {"p", "li", "blockquote", "codeblock", "table", "tr", "td", "th",
         "ul", "ol", *HEADINGS}


def inline(el):
    out = [el.text or ""]
    for child in el:
        if child.tag in DROP:
            pass
        elif child.tag == "code":
            out.append("`" + "".join(child.itertext()) + "`")
        elif child.tag == "br":
            out.append("\n")
        elif child.tag not in LISTS:
            out.append(inline(child))
        out.append(child.tail or "")
    return "".join(out).strip()


def has_block_child(el):
    return any(c.tag in BLOCK for c in el)


def blocks(el):
    tag = el.tag
    if tag in DROP:
        return []
    if tag in HEADINGS:
        return ["#" * HEADINGS[tag] + " " + inline(el)]
    if tag == "codeblock":
        return ["```\n" + "".join(el.itertext()).strip("\n") + "\n```"]
    if tag in LISTS:
        lines = []
        for li in el:
            lines.append("- " + inline(li))
            for nested in li:
                if nested.tag in LISTS:
                    lines.extend("  " + b for b in blocks(nested))
        return ["\n".join(lines)]
    if tag == "blockquote":
        inner = [b for c in el for b in blocks(c)] if has_block_child(el) else [inline(el)]
        return ["\n".join("> " + line for b in inner for line in b.splitlines())]
    if tag == "table":
        rows = []
        for tr in el.iter("tr"):
            cells = [inline(c) for c in tr if c.tag in ("td", "th")]
            rows.append("| " + " | ".join(cells) + " |")
        return ["\n".join(rows)]
    if has_block_child(el):
        return [b for c in el for b in blocks(c)]
    text = inline(el)
    return [text] if text else []


def main():
    root = ET.parse(sys.argv[1] if len(sys.argv) > 1 else sys.stdin).getroot()
    content = root if root.tag in ("doc", "content") else root.find(".//content")
    if content is None:
        sys.exit("error: no <content> or <doc> element")
    parts = []
    title = root.find(".//title")
    if title is not None and (title.text or "").strip():
        parts.append("# " + title.text.strip())
    parts.extend(b for c in content for b in blocks(c))
    sys.stdout.write("\n\n".join(p for p in parts if p.strip()) + "\n")


if __name__ == "__main__":
    main()

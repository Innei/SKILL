#!/usr/bin/env python3
"""Render a codebase-value-audit report as a standalone HTML file.

Usage:
    python3 render-report.py <report-data.json> <out.html>

Schema: see references/report-data.example.json. Bar widths are computed
from the max `lines` among rows; the base row (infra) renders without a
bar. Output is self-contained (inline CSS, system fonts, light/dark via
prefers-color-scheme) — open directly in a browser.
"""
import html
import json
import sys

TIERS = {"s": "最值", "a": "值", "c": "打折", "r": "风险", "n": "成本", "x": "不评"}

CSS = """
:root{--bg:#F5F6F4;--ink:#1B211E;--ink2:#57625C;--muted:#8B958F;--line:#E1E6E1;
--lineS:#C8D0C9;--accent:#17594A;--accentSoft:#17594A14;--good:#16624F;--goodBg:#16624F12;
--warn:#96690F;--warnBg:#96690F14;--risk:#6D57B8;--riskBg:#6D57B814;--cost:#5A6B78;
--costBg:#5A6B7814;--bar:#17594A;--track:#1B211E0A}
@media (prefers-color-scheme: dark){:root{--bg:#0F1311;--ink:#E5EAE6;--ink2:#A5B0A9;
--muted:#6E7972;--line:#262D28;--lineS:#37403A;--accent:#52C0A0;--accentSoft:#52C0A01A;
--good:#57B893;--goodBg:#57B8931A;--warn:#C79A3E;--warnBg:#C79A3E1A;--risk:#A18BE0;
--riskBg:#A18BE01A;--cost:#93A4B2;--costBg:#93A4B21A;--bar:#52C0A0;--track:#E5EAE60D}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.8 -apple-system,"PingFang SC",
"Hiragino Sans GB","Noto Sans SC","Microsoft YaHei",sans-serif;-webkit-font-smoothing:antialiased}
.mono,td.num,.stat .v,.sum,.ln{font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
font-variant-numeric:tabular-nums}
.wrap{max-width:1020px;margin:0 auto;padding:0 28px 96px}
header{padding-top:64px}
.eyebrow{display:flex;align-items:center;gap:14px;font-family:ui-monospace,Menlo,monospace;
font-size:12px;letter-spacing:.14em;color:var(--accent)}
.eyebrow .rule{flex:1;height:1px;background:var(--lineS)}
.eyebrow .date{color:var(--muted)}
h1{font-size:clamp(30px,4.6vw,44px);font-weight:800;line-height:1.25;margin:18px 0 6px;text-wrap:balance}
.thesis{font-size:17px;color:var(--ink2);margin:0 0 40px;max-width:640px}
.thesis strong{color:var(--ink)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
border-top:2px solid var(--ink);border-bottom:1px solid var(--line)}
.stat{padding:18px 20px 20px;border-right:1px solid var(--line)}
.stat:first-child{padding-left:0}.stat:last-child{border-right:none}
.stat .v{font-size:clamp(24px,3vw,32px);font-weight:600;line-height:1.2}
.stat.verdict .v{color:var(--accent);font-family:inherit;font-weight:800}
.stat .k{font-size:12px;color:var(--muted);margin-top:4px}
section{margin-top:72px}
.sec{display:flex;align-items:baseline;gap:14px;margin-bottom:8px}
.sec .no{font-family:ui-monospace,Menlo,monospace;font-size:12px;letter-spacing:.14em;color:var(--accent)}
.sec h2{font-size:21px;font-weight:800;margin:0}
.sub{color:var(--ink2);font-size:14px;margin:0 0 24px;max-width:720px}
.scope{font-size:13.5px;color:var(--ink2);border-left:2px solid var(--lineS);
padding:2px 0 2px 18px;max-width:700px}
.scope b,.tier p b,.items b,.waste b{color:var(--ink);font-weight:600}
.tscroll{overflow-x:auto;border-top:2px solid var(--ink)}
table{border-collapse:collapse;width:100%;min-width:780px}
th{text-align:left;font-size:12px;font-weight:600;color:var(--muted);letter-spacing:.06em;
padding:10px 14px 10px 0;border-bottom:1px solid var(--lineS);white-space:nowrap}
th.num,td.num{text-align:right}
td{padding:9px 14px 9px 0;border-bottom:1px solid var(--line);vertical-align:middle}
tbody tr:hover td{background:var(--accentSoft)}
td.rank{color:var(--muted);font-size:12px;width:30px}
td.name{font-weight:600;white-space:nowrap}
td.name small{display:block;font-weight:400;font-size:12px;color:var(--muted);
line-height:1.5;white-space:normal;max-width:340px}
td.num{font-size:13.5px;white-space:nowrap}
td.pct{color:var(--ink2)}
td.barcell{width:26%;min-width:140px}
.bar{height:8px;background:var(--track);border-radius:0 3px 3px 0;position:relative}
.bar i{position:absolute;inset:0 auto 0 0;background:var(--bar);border-radius:0 3px 3px 0}
tr.base td{border-bottom:2px solid var(--ink);background:var(--track)}
.chip{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:600;
white-space:nowrap;padding:2px 9px;border-radius:2px;line-height:1.7}
.chip::before{content:"";width:7px;height:7px;flex:none}
.chip.s{color:var(--good);background:var(--goodBg)}.chip.s::before{background:var(--good)}
.chip.a{color:var(--good);box-shadow:inset 0 0 0 1px var(--lineS)}
.chip.a::before{background:var(--good);border-radius:50%}
.chip.c{color:var(--warn);background:var(--warnBg)}
.chip.c::before{background:var(--warn);clip-path:polygon(50% 0,100% 100%,0 100%)}
.chip.r{color:var(--risk);background:var(--riskBg)}
.chip.r::before{background:var(--risk);clip-path:polygon(50% 0,100% 50%,50% 100%,0 50%)}
.chip.n{color:var(--cost);background:var(--costBg)}
.chip.n::before{border:1.5px solid var(--cost);border-radius:50%;width:5px;height:5px}
.chip.x{color:var(--muted);box-shadow:inset 0 0 0 1px var(--line)}
.chip.x::before{background:var(--muted);height:1.5px}
.tier{border-top:1px solid var(--lineS);padding:26px 0 6px}
.thead{display:flex;flex-wrap:wrap;align-items:baseline;gap:12px;margin-bottom:6px}
.thead h3{font-size:16.5px;font-weight:800;margin:0}
.thead .sum{font-size:12.5px;color:var(--muted);margin-left:auto}
.tier p{color:var(--ink2);font-size:14px;margin:6px 0 14px;max-width:720px}
.items{margin:0 0 20px;padding:0;list-style:none}
.items li{padding:9px 0;border-top:1px dashed var(--line);font-size:14px;color:var(--ink2)}
.items li:first-child{border-top:none}
.ln{color:var(--accent);font-size:13px;margin:0 2px}
.waste{margin:0;padding:0;list-style:none;counter-reset:w;max-width:720px}
.waste li{counter-increment:w;padding:12px 0 12px 44px;position:relative;
border-bottom:1px solid var(--line);font-size:14px;color:var(--ink2)}
.waste li::before{content:counter(w,decimal-leading-zero);position:absolute;left:0;top:14px;
font-family:ui-monospace,Menlo,monospace;font-size:12px;color:var(--warn);letter-spacing:.08em}
.closing{border-top:2px solid var(--ink);padding-top:30px}
.closing .big{font-size:clamp(19px,2.6vw,24px);font-weight:700;line-height:1.65;
max-width:780px;margin:0 0 18px}
.closing .big mark{background:none;color:var(--accent)}
.closing p{color:var(--ink2);max-width:720px;margin:0}
footer{margin-top:88px;padding-top:16px;border-top:1px solid var(--line);display:flex;
flex-wrap:wrap;gap:8px 24px;font-family:ui-monospace,Menlo,monospace;font-size:11.5px;
letter-spacing:.05em;color:var(--muted)}
"""


def e(s):
    return html.escape(str(s), quote=True)


def rich(s):
    return (
        e(s)
        .replace("[[", "<b>").replace("]]", "</b>")
        .replace("((", "<mark>").replace("))", "</mark>")
    )


def render(d):
    rows = d["rows"]
    mx = max(r["lines"] for r in rows)
    out = []
    for i, r in enumerate(rows, 1):
        sub = f'<small>{e(r["sub"])}</small>' if r.get("sub") else ""
        w = round(r["lines"] / mx * 100, 1)
        out.append(
            f'<tr><td class="rank">{i}</td><td class="name">{e(r["name"])}{sub}</td>'
            f'<td><span class="chip {r["tier"]}">{e(r.get("verdict") or TIERS[r["tier"]])}</span></td>'
            f'<td class="num">{r["lines"]:,}</td><td class="num pct">{e(r["share"])}</td>'
            f'<td class="barcell"><div class="bar"><i style="width:{w}%"></i></div></td></tr>'
        )
    base = d.get("base_row")
    if base:
        sub = f'<small>{e(base["sub"])}</small>' if base.get("sub") else ""
        out.append(
            f'<tr class="base"><td class="rank"></td><td class="name">{e(base["name"])}{sub}</td>'
            f'<td><span class="chip n">{e(base.get("verdict", "健康"))}</span></td>'
            f'<td class="num">{base["lines"]:,}</td><td class="num pct">{e(base["share"])}</td>'
            f'<td class="barcell"></td></tr>'
        )
    table = "".join(out)

    stats = "".join(
        f'<div class="stat{" verdict" if s.get("accent") else ""}">'
        f'<div class="v">{e(s["v"])}</div><div class="k">{e(s["k"])}</div></div>'
        for s in d["stats"]
    )

    tiers = []
    for t in d["tiers"]:
        items = ""
        if t.get("items"):
            items = "<ul class=\"items\">" + "".join(
                f'<li><b>{e(i["name"])}</b><span class="ln">{i["lines"]:,}</span>'
                f"—— {rich(i['comment'])}</li>"
                for i in t["items"]
            ) + "</ul>"
        intro = f"<p>{rich(t['intro'])}</p>" if t.get("intro") else ""
        tiers.append(
            f'<div class="tier"><div class="thead"><span class="chip {t["tier"]}">'
            f'{e(t.get("label") or TIERS[t["tier"]])}</span><h3>{e(t["title"])}</h3>'
            f'<span class="sum">{e(t["sum"])}</span></div>{intro}{items}</div>'
        )

    waste = "".join(
        f"<li><b>{rich(w['head'])}</b> —— {rich(w['detail'])}</li>" for w in d["squeeze"]
    )
    foot = "".join(f"<span>{e(f)}</span>" for f in d["footer"])

    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(d["title"])}</title><style>{CSS}</style></head><body>
<div class="wrap">
<header>
<div class="eyebrow"><span>{e(d["eyebrow"])}</span><span class="rule"></span>
<span class="date">{e(d["date"])}</span></div>
<h1>{e(d["title"])}</h1>
<p class="thesis">{rich(d["thesis"])}</p>
<div class="stats">{stats}</div>
</header>
<section><div class="sec"><span class="no">01</span><h2>审计口径</h2></div>
<p class="scope">{rich(d["scope"])}</p></section>
<section><div class="sec"><span class="no">02</span><h2>{e(d["table_title"])}</h2></div>
<p class="sub">{rich(d["table_sub"])}</p>
<div class="tscroll"><table><thead><tr><th></th><th>子产品</th><th>判定</th>
<th class="num">纯代码行</th><th class="num">占比</th><th>规模</th></tr></thead>
<tbody>{table}</tbody></table></div></section>
<section><div class="sec"><span class="no">03</span><h2>分档点评</h2></div>{"".join(tiers)}</section>
<section><div class="sec"><span class="no">04</span><h2>{e(d["squeeze_title"])}</h2></div>
<ol class="waste">{waste}</ol></section>
<section class="closing"><div class="sec"><span class="no">05</span><h2>结论</h2></div>
<p class="big">{rich(d["conclusion"]["big"])}</p>
<p>{rich(d["conclusion"]["rest"])}</p></section>
<footer>{foot}</footer>
</div></body></html>"""


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: render-report.py <report-data.json> <out.html>")
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        f.write(render(data))
    print(sys.argv[2])


if __name__ == "__main__":
    main()

#!/usr/bin/env -S uv run --quiet --with pytest --with markdown-it-py --with beautifulsoup4 python -m pytest
from __future__ import annotations

import json
import sys
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))

from render_html import md_to_html, render_charts


def fence(spec) -> str:
    body = spec if isinstance(spec, str) else json.dumps(spec, ensure_ascii=False)
    return f"intro\n\n```chart\n{body}\n```\n"


def rendered(spec) -> BeautifulSoup:
    soup = BeautifulSoup(md_to_html(fence(spec)), "html.parser")
    render_charts(soup)
    return soup


BAR = {
    "version": 1,
    "type": "bar",
    "title": "日均成本变化",
    "x": "metric",
    "series": [{"key": "landing", "label": "landing-rr"}, {"key": "market", "label": "market"}],
    "data": [
        {"metric": "总成本", "landing": -28.8, "market": -27.9},
        {"metric": "CDN Requests", "landing": -47.0, "market": -29.8},
    ],
    "format": {"unit": "%"},
    "source": "vercel usage",
}

LINE = {
    "version": 1,
    "type": "line",
    "title": "投影请求 / 4h",
    "x": "t",
    "series": [{"key": "req", "label": "请求"}],
    "data": [{"t": "11-06 08", "req": 37967}, {"t": "11-06 12", "req": 6414}, {"t": "11-06 16", "req": 39}],
}


def test_chart_fence_becomes_figure_with_svg_and_title_caption():
    soup = rendered(BAR)
    assert soup.find("pre") is None
    fig = soup.find("figure", class_="chart")
    assert fig is not None
    assert fig.find("svg") is not None
    assert "日均成本变化" in fig.find("figcaption").get_text()
    assert "vercel usage" in fig.find("figcaption").get_text()


def test_bar_chart_draws_one_bar_per_row_and_series():
    bars = rendered(BAR).find("svg").find_all("rect", class_="bar")
    assert len(bars) == 4


def test_negative_bars_hang_below_the_zero_line():
    svg = rendered(BAR).find("svg")
    zero = float(svg.find("line", class_="zero")["y1"])
    for bar in svg.find_all("rect", class_="bar"):
        assert float(bar["y"]) >= zero - 0.01


def test_bar_labels_carry_the_unit():
    text = rendered(BAR).find("svg").get_text(" ")
    assert "-47%" in text


def test_line_chart_draws_one_polyline_per_series_with_every_point():
    svg = rendered(LINE).find("svg")
    lines = svg.find_all("polyline", class_="series")
    assert len(lines) == 1
    assert len(lines[0]["points"].split()) == 3


def test_series_legend_lists_labels():
    text = rendered(BAR).find("svg").get_text(" ")
    assert "landing-rr" in text and "market" in text


def test_invalid_spec_is_left_as_a_code_block():
    soup = rendered("{not json")
    assert soup.find("pre") is not None
    assert soup.find("figure", class_="chart") is None


def test_unsupported_type_is_left_as_a_code_block():
    soup = rendered({**BAR, "type": "pie"})
    assert soup.find("pre") is not None


def test_plain_code_blocks_are_untouched():
    soup = BeautifulSoup(md_to_html("```js\nconst a = 1\n```\n"), "html.parser")
    render_charts(soup)
    assert soup.find("pre") is not None


def test_editor_projection_keeps_chart_fences_verbatim():
    from render_md import project

    md = "# T\n\n## 01 a\n\n" + fence(LINE) + "\n## 附录\n\n- x\n"
    out = project(md, "T", None)
    assert "```chart" in out
    assert json.dumps(LINE, ensure_ascii=False) in out

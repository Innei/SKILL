from __future__ import annotations

import html
import json
import math

SUPPORTED = {"bar", "line", "area"}
PALETTE = ["#79c0ff", "#7ee787", "#d2a8ff", "#ffa657", "#ff7b72", "#a5d6ff"]
PREFIX_UNITS = {"$", "€", "£", "¥", "₹", "₩"}
ATTACHED_UNITS = {"%", "‰", "°"}

W, H = 640, 280
PAD_L, PAD_R, PAD_T, PAD_B = 56, 16, 36, 44
MAX_X_LABELS = 8


def parse_spec(source: str) -> dict | None:
    try:
        spec = json.loads(source)
    except json.JSONDecodeError:
        return None
    if not isinstance(spec, dict) or spec.get("type") not in SUPPORTED:
        return None
    x = spec.get("x")
    series = [s if isinstance(s, dict) else {"key": s} for s in spec.get("series") or []]
    data = spec.get("data") or []
    if not isinstance(x, str) or not x or not series or not data:
        return None
    for row in data:
        if not isinstance(row, dict) or x not in row:
            return None
        for s in series:
            value = row.get(s.get("key"))
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                return None
    return {**spec, "series": series}


def format_value(value: float, fmt: dict) -> str:
    decimals = fmt.get("decimals")
    if fmt.get("compact") and abs(value) >= 1000:
        for size, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "k")):
            if abs(value) >= size:
                text = f"{value / size:.{1 if decimals is None else decimals}f}".rstrip("0").rstrip(".") + suffix
                break
    elif decimals is not None:
        text = f"{value:.{decimals}f}"
    else:
        text = f"{value:.0f}" if abs(value) >= 100 else f"{value:.1f}".rstrip("0").rstrip(".")
    if text in ("-0", "-0.0"):
        text = "0"
    sign = "+" if fmt.get("signed") and value > 0 else ""
    unit = fmt.get("unit") or ""
    if unit in PREFIX_UNITS:
        if text.startswith("-"):
            return f"-{unit}{text[1:]}"
        return f"{sign}{unit}{text}"
    if unit in ATTACHED_UNITS or not unit:
        return f"{sign}{text}{unit}"
    return f"{sign}{text} {unit}"


def nice_bounds(values: list[float], y: dict) -> tuple[float, float]:
    lo = min([0.0, *values])
    hi = max([0.0, *values])
    if isinstance(y.get("min"), (int, float)):
        lo = y["min"]
    if isinstance(y.get("max"), (int, float)):
        hi = y["max"]
    if hi == lo:
        hi = lo + 1
    step = nice_step((hi - lo) / 4)
    return math.floor(lo / step) * step, math.ceil(hi / step) * step


def nice_step(raw: float) -> float:
    magnitude = 10 ** math.floor(math.log10(raw))
    for factor in (1, 2, 2.5, 5, 10):
        if raw <= factor * magnitude:
            return factor * magnitude
    return 10 * magnitude


def esc(text) -> str:
    return html.escape(str(text), quote=True)


def render_svg(spec: dict) -> str:
    series = spec["series"]
    data = spec["data"]
    x_key = spec["x"]
    fmt = spec.get("format") or {}
    values = [row[s["key"]] for row in data for s in series]
    lo, hi = nice_bounds(values, spec.get("y") or {})
    plot_w = W - PAD_L - PAD_R
    plot_h = H - PAD_T - PAD_B

    def y_of(v: float) -> float:
        return PAD_T + (hi - v) / (hi - lo) * plot_h

    band = plot_w / len(data)
    title = esc(spec.get("title") or "chart")
    parts = [
        f'<svg class="chart-svg" viewBox="0 0 {W} {H}" role="img" aria-label="{title}" xmlns="http://www.w3.org/2000/svg">'
    ]

    step = (hi - lo) / 4
    for i in range(5):
        tick = lo + step * i
        ty = y_of(tick)
        parts.append(f'<line class="grid" x1="{PAD_L}" x2="{W - PAD_R}" y1="{ty:.2f}" y2="{ty:.2f}"/>')
        parts.append(f'<text class="tick" x="{PAD_L - 6}" y="{ty + 4:.2f}" text-anchor="end">{esc(format_value(tick, fmt))}</text>')

    zero_y = y_of(0)
    parts.append(f'<line class="zero" x1="{PAD_L}" x2="{W - PAD_R}" y1="{zero_y:.2f}" y2="{zero_y:.2f}"/>')

    every = max(1, math.ceil(len(data) / MAX_X_LABELS))
    for i, row in enumerate(data):
        if i % every:
            continue
        cx = PAD_L + band * (i + 0.5)
        parts.append(f'<text class="xlabel" x="{cx:.2f}" y="{H - PAD_B + 18}" text-anchor="middle">{esc(row[x_key])}</text>')

    if spec["type"] == "bar":
        inner = band * 0.72 / len(series)
        for i, row in enumerate(data):
            start = PAD_L + band * i + band * 0.14
            for j, s in enumerate(series):
                v = row[s["key"]]
                vy = y_of(v)
                top, height = min(vy, zero_y), abs(vy - zero_y)
                bx = start + inner * j
                color = PALETTE[j % len(PALETTE)]
                parts.append(
                    f'<rect class="bar" x="{bx:.2f}" y="{top:.2f}" width="{inner * 0.9:.2f}" height="{height:.2f}" fill="{color}"/>'
                )
                ly = top - 4 if v >= 0 else top + height + 12
                parts.append(
                    f'<text class="value" x="{bx + inner * 0.45:.2f}" y="{ly:.2f}" text-anchor="middle">{esc(format_value(v, fmt))}</text>'
                )
    else:
        for j, s in enumerate(series):
            color = PALETTE[j % len(PALETTE)]
            pts = [(PAD_L + band * (i + 0.5), y_of(row[s["key"]])) for i, row in enumerate(data)]
            points = " ".join(f"{px:.2f},{py:.2f}" for px, py in pts)
            if spec["type"] == "area":
                poly = f"{pts[0][0]:.2f},{zero_y:.2f} {points} {pts[-1][0]:.2f},{zero_y:.2f}"
                parts.append(f'<polygon class="area" points="{poly}" fill="{color}" fill-opacity="0.18"/>')
            parts.append(f'<polyline class="series" points="{points}" fill="none" stroke="{color}" stroke-width="2"/>')
            for px, py in pts:
                parts.append(f'<circle class="dot" cx="{px:.2f}" cy="{py:.2f}" r="2.5" fill="{color}"/>')

    lx = PAD_L
    for j, s in enumerate(series):
        label = s.get("label") or s["key"]
        color = PALETTE[j % len(PALETTE)]
        parts.append(f'<rect class="swatch" x="{lx}" y="12" width="10" height="10" fill="{color}"/>')
        parts.append(f'<text class="legend" x="{lx + 14}" y="21">{esc(label)}</text>')
        lx += 24 + 7 * len(str(label))

    parts.append("</svg>")
    return "".join(parts)


def caption_html(spec: dict) -> str:
    bits = []
    if spec.get("title"):
        bits.append(f"<strong>{esc(spec['title'])}</strong>")
    for key in ("subtitle", "note"):
        if spec.get(key):
            bits.append(esc(spec[key]))
    if spec.get("source"):
        bits.append(f"来源：{esc(spec['source'])}")
    return " · ".join(bits)

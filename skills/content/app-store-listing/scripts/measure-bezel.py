#!/usr/bin/env python3
import json
import subprocess
import sys
from collections import deque
from pathlib import Path


def identify(path: Path) -> tuple[int, int]:
    out = subprocess.check_output(
        ["magick", "identify", "-format", "%w %h", str(path)],
        text=True,
    ).strip()
    w, h = out.split()
    return int(w), int(h)


def alpha_bytes(path: Path, w: int, h: int) -> bytes:
    data = subprocess.check_output(
        ["magick", str(path), "-alpha", "extract", "-depth", "8", "gray:-"]
    )
    if len(data) != w * h:
        raise SystemExit(f"alpha size {len(data)} != {w * h}")
    return data


def hole(data: bytes, w: int, h: int) -> dict:
    def a(x: int, y: int) -> int:
        return data[y * w + x]

    cx, cy = w // 2, h // 2
    if a(cx, cy) >= 8:
        raise SystemExit("bezel screen is not transparent at center")
    seen = bytearray(w * h)
    q = deque([(cx, cy)])
    seen[cy * w + cx] = 1
    minx = maxx = cx
    miny = maxy = cy
    while q:
        x, y = q.popleft()
        if x < minx:
            minx = x
        if x > maxx:
            maxx = x
        if y < miny:
            miny = y
        if y > maxy:
            maxy = y
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            i = ny * w + nx
            if 0 <= nx < w and 0 <= ny < h and not seen[i] and a(nx, ny) < 8:
                seen[i] = 1
                q.append((nx, ny))
    return {
        "x": minx,
        "y": miny,
        "w": maxx - minx + 1,
        "h": maxy - miny + 1,
        "bezelW": w,
        "bezelH": h,
    }


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: measure-bezel.py <bezel.png>")
    path = Path(sys.argv[1])
    w, h = identify(path)
    print(json.dumps(hole(alpha_bytes(path, w, h), w, h)))


if __name__ == "__main__":
    main()

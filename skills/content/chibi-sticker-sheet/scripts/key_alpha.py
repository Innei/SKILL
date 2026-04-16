# /// script
# dependencies = ["Pillow", "numpy", "scipy"]
# ///
"""Edge flood-fill alpha keying for white-background sticker sheets.

Usage:
    uv run key_alpha.py sheet_white.png [out_dir]

Outputs:
    <out_dir>/sheet_transparent.png
    <out_dir>/cells/01_<name>.png … 16_<name>.png  (512×512 each)
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy.ndimage import label

WHITE_TOL = 28    # max per-channel delta from #fff to count as near-white
FEATHER_PX = 1.2  # gaussian blur radius on alpha edge (px)
ROWS, COLS = 4, 4


def key_white_bg(img: Image.Image) -> Image.Image:
    """Return RGBA image with exterior white pixels made transparent.

    Interior white pixels (shirt, skin highlights) are enclosed by foreground
    and never touch the image border, so they remain opaque.
    """
    rgb = np.asarray(img.convert("RGB"), dtype=np.int16)
    dist = np.max(np.abs(rgb - 255), axis=2)   # 0 = pure white
    near_white = dist < WHITE_TOL

    lbl, _ = label(near_white)
    edge_ids: set[int] = set()
    for edge in (lbl[0, :], lbl[-1, :], lbl[:, 0], lbl[:, -1]):
        edge_ids.update(edge.tolist())
    edge_ids.discard(0)
    bg_mask = np.isin(lbl, list(edge_ids))

    alpha = np.where(bg_mask, 0, 255).astype(np.uint8)
    alpha_img = Image.fromarray(alpha, mode="L").filter(
        ImageFilter.GaussianBlur(radius=FEATHER_PX)
    )

    rgba = np.dstack([rgb.astype(np.uint8), np.asarray(alpha_img)])
    return Image.fromarray(rgba, mode="RGBA")


def _find_cuts(profile: np.ndarray, n_cells: int, white_tol: float = 0.98) -> list[int]:
    """Return n_cells+1 cut positions from a per-row/col white-fraction profile.

    Strategy:
    1. Find all contiguous runs where white_fraction >= white_tol (gap bands).
    2. Represent each run by its midpoint.
    3. Always include 0 and len(profile) as outer cuts.
    4. Interior midpoints should be n_cells-1; if more exist (thin intra-sticker
       white bands), keep only the n_cells-1 most spread-out ones via max-spacing
       selection.
    """
    size = len(profile)
    is_gap = profile >= white_tol

    # Collect gap-run midpoints (interior only, not edges)
    mids: list[int] = []
    in_run = False
    run_start = 0
    for i in range(size):
        if is_gap[i] and not in_run:
            run_start = i
            in_run = True
        elif not is_gap[i] and in_run:
            mids.append((run_start + i) // 2)
            in_run = False
    if in_run:
        mids.append((run_start + size) // 2)

    # Remove edge midpoints (too close to 0 or size)
    margin = size // (n_cells * 4)
    mids = [m for m in mids if margin < m < size - margin]

    n_interior = n_cells - 1
    if len(mids) == n_interior:
        interior = mids
    elif len(mids) < n_interior:
        # Fallback: evenly spaced
        interior = [size * (i + 1) // n_cells for i in range(n_interior)]
    else:
        # Too many candidates: pick n_interior with maximum mutual spacing
        # greedy: start from the leftmost, pick next that is farthest from all chosen
        candidates = sorted(mids)
        chosen = [candidates[0]]
        while len(chosen) < n_interior:
            best = max(
                (c for c in candidates if c not in chosen),
                key=lambda c: min(abs(c - x) for x in chosen),
            )
            chosen.append(best)
        interior = sorted(chosen)

    cuts = [0] + interior + [size]
    return cuts


def slice_grid(
    sheet: Image.Image,
    src_rgb: Image.Image | None = None,
    rows: int = ROWS,
    cols: int = COLS,
) -> list[Image.Image]:
    """Slice a rows×cols sticker grid, auto-detecting actual cell boundaries.

    Uses the white-background source image (src_rgb) to detect gap bands.
    Falls back to equal division when src_rgb is not provided.
    Each output cell is square (padded/cropped to the larger axis).
    """
    w, h = sheet.size

    if src_rgb is not None:
        rgb = np.asarray(src_rgb.convert("RGB"), dtype=np.int16)
        dist = np.max(np.abs(rgb - 255), axis=2)      # 0 = pure white
        near_white = dist < WHITE_TOL

        col_profile = near_white.mean(axis=0)          # per-column white fraction
        row_profile = near_white.mean(axis=1)          # per-row   white fraction

        x_cuts = _find_cuts(col_profile, cols)
        y_cuts = _find_cuts(row_profile, rows)
        print(f"  x_cuts: {x_cuts}")
        print(f"  y_cuts: {y_cuts}")
    else:
        cw, ch = w // cols, h // rows
        x_cuts = [c * cw for c in range(cols + 1)]
        y_cuts = [r * ch for r in range(rows + 1)]

    cells: list[Image.Image] = []
    for r in range(rows):
        for c in range(cols):
            x0, x1 = x_cuts[c], x_cuts[c + 1]
            y0, y1 = y_cuts[r], y_cuts[r + 1]
            cell_w, cell_h = x1 - x0, y1 - y0
            side = max(cell_w, cell_h)          # square: pad to larger dimension
            # center-pad to square
            pad_x = (side - cell_w) // 2
            pad_y = (side - cell_h) // 2
            region = sheet.crop((x0, y0, x1, y1))
            square = Image.new("RGBA", (side, side), (255, 255, 255, 0))
            square.paste(region, (pad_x, pad_y))
            cells.append(square)
    return cells


def main() -> None:
    src_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("sheet_white.png")
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else src_path.parent
    cells_dir = out_dir / "cells"
    cells_dir.mkdir(parents=True, exist_ok=True)

    src = Image.open(src_path)
    print(f"source: {src_path.name} {src.size}")

    rgba = key_white_bg(src)
    out_path = out_dir / "sheet_transparent.png"
    rgba.save(out_path)
    a = np.asarray(rgba)[..., 3]
    print(f"alpha: transparent%={(a < 10).mean() * 100:.1f}  -> {out_path.name}")

    for i, cell in enumerate(slice_grid(rgba, src_rgb=src)):
        cell.save(cells_dir / f"{i + 1:02d}.png")
    print(f"sliced {ROWS * COLS} cells ({cells_dir})")


if __name__ == "__main__":
    main()

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
from itertools import combinations
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy.ndimage import binary_dilation, label

WHITE_TOL = 28        # max per-channel delta from #fff to count as near-white
OUTLINE_THRESH = 150  # min per-channel delta from #fff to count as outline (dark pixel)
OUTLINE_DILATE = 2    # dilation iterations to close outline gaps before flood-fill
FEATHER_PX = 1.2      # gaussian blur radius on alpha edge (px)
ROWS, COLS = 4, 4  # defaults; overridden by --rows / --cols CLI args
CUT_DARK_THRESH = 40
CUT_MAX_EMPTY_PIXELS = 0
CUT_EDGE_MARGIN_DIVISOR = 8


def key_white_bg(img: Image.Image) -> Image.Image:
    """Return RGBA image with exterior white pixels made transparent.

    Problem: white clothing has the same dist-from-white as the background.
    If the black outline has any 1-2 px gaps, a naive flood-fill leaks
    through those gaps into white fabric, making the clothing transparent.

    Fix: dilate the dark outline pixels (dist > OUTLINE_THRESH) before
    flood-filling.  This plugs any sub-3-px gaps in the outline, so the
    flood cannot cross the outline boundary into enclosed white areas.
    """
    rgb = np.asarray(img.convert("RGB"), dtype=np.int16)
    dist = np.max(np.abs(rgb - 255), axis=2)   # 0 = pure white

    # Dilate outline to close tiny gaps (≤ OUTLINE_DILATE px)
    outline = dist > OUTLINE_THRESH
    outline_closed = binary_dilation(outline, iterations=OUTLINE_DILATE)

    # Flood candidates: near-white AND NOT blocked by thickened outline
    near_white = dist < WHITE_TOL
    flood_candidates = near_white & ~outline_closed

    lbl, _ = label(flood_candidates)
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


def _collect_runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """Return [start, end) runs where mask is true."""
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for i, flag in enumerate(mask):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            runs.append((start, i))
            start = None
    if start is not None:
        runs.append((start, len(mask)))
    return runs


def _equal_spacing_cuts(size: int, n_cells: int) -> list[int]:
    """Return [0, ..., size] with equal cell spacing."""
    return [int(round(size * i / n_cells)) for i in range(n_cells + 1)]


def _select_best_spread(
    candidates: list[tuple[int, int]],
    size: int,
    target_count: int,
) -> list[int]:
    """Choose the subset whose gaps are maximally spread across the full axis."""
    best_positions: list[int] | None = None
    best_score: tuple[tuple[int, ...], int, tuple[int, ...]] | None = None

    for combo in combinations(candidates, target_count):
        positions = [pos for pos, _ in combo]
        boundaries = [0] + positions + [size]
        gaps = tuple(sorted(boundaries[i + 1] - boundaries[i] for i in range(len(boundaries) - 1)))
        widths = tuple(sorted((width for _, width in combo), reverse=True))
        score = (gaps, sum(widths), widths)
        if best_score is None or score > best_score:
            best_score = score
            best_positions = positions

    return [] if best_positions is None else best_positions


def _fill_missing_cuts(size: int, selected: list[int], target_count: int) -> list[int]:
    """Preserve known cuts, then split the largest remaining gaps to complete the grid."""
    chosen = sorted(selected)
    while len(chosen) < target_count:
        boundaries = [0] + chosen + [size]
        gap_index = max(
            range(len(boundaries) - 1),
            key=lambda i: boundaries[i + 1] - boundaries[i],
        )
        start, end = boundaries[gap_index], boundaries[gap_index + 1]
        midpoint = (start + end) // 2
        if midpoint in chosen or midpoint <= start or midpoint >= end:
            return _equal_spacing_cuts(size, target_count + 1)[1:-1]
        chosen.append(midpoint)
        chosen.sort()
    return chosen


def _find_cuts(
    profile: np.ndarray,
    n_cells: int,
    orthogonal_size: int,
    white_tol: float | None = None,
) -> list[int]:
    """Return n_cells+1 cuts from a dark-occupancy profile.

    Gap rows/columns are detected as contiguous runs whose dark-pixel count is
    effectively zero. White interiors inside stickers remain non-gap because the
    row/column still intersects black outline pixels elsewhere.
    """
    del white_tol  # legacy CLI/API parameter; dark-profile cuts ignore this value

    size = len(profile)
    n_interior = n_cells - 1
    if n_interior <= 0:
        return [0, size]

    del orthogonal_size  # retained for API compatibility; exact-zero runs are the default signal

    empty_limit = CUT_MAX_EMPTY_PIXELS
    edge_margin = max(2, size // max(1, n_cells * CUT_EDGE_MARGIN_DIVISOR))
    empty_runs = _collect_runs(profile <= empty_limit)

    candidates: list[tuple[int, int]] = []
    for start, end in empty_runs:
        if start == 0 or end == size:
            continue
        midpoint = (start + end) // 2
        if midpoint <= edge_margin or midpoint >= size - edge_margin:
            continue
        candidates.append((midpoint, end - start))

    if len(candidates) == n_interior:
        return [0] + [pos for pos, _ in candidates] + [size]
    if not candidates:
        return _equal_spacing_cuts(size, n_cells)
    if len(candidates) > n_interior:
        selected = _select_best_spread(candidates, size=size, target_count=n_interior)
        return [0] + selected + [size]

    selected = _fill_missing_cuts(
        size=size,
        selected=[pos for pos, _ in candidates],
        target_count=n_interior,
    )
    return [0] + selected + [size]


def slice_grid(
    sheet: Image.Image,
    src_rgb: Image.Image | None = None,
    rows: int = ROWS,
    cols: int = COLS,
    cut_tol: float = 0.98,
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
        dark = dist > CUT_DARK_THRESH

        col_profile = dark.sum(axis=0)                # per-column dark outline count
        row_profile = dark.sum(axis=1)                # per-row   dark outline count

        x_cuts = _find_cuts(
            col_profile,
            cols,
            orthogonal_size=h,
            white_tol=cut_tol,
        )
        y_cuts = _find_cuts(
            row_profile,
            rows,
            orthogonal_size=w,
            white_tol=cut_tol,
        )
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
    import argparse

    parser = argparse.ArgumentParser(description="Alpha-key and slice a sticker sheet.")
    parser.add_argument("src", nargs="?", default="sheet_white.png")
    parser.add_argument("out_dir", nargs="?", default=None)
    parser.add_argument("--rows", type=int, default=ROWS)
    parser.add_argument("--cols", type=int, default=COLS)
    parser.add_argument("--cut-tol", type=float, default=0.98,
                        help="Deprecated legacy option retained for CLI compatibility; "
                             "dark-profile cut detection ignores this value.")
    parser.add_argument("--names", default=None,
                        help="Text file with one expression name per line (snake_case); "
                             "used as cell filenames instead of 01, 02 …")
    args = parser.parse_args()

    src_path = Path(args.src)
    out_dir = Path(args.out_dir) if args.out_dir else src_path.parent
    cells_dir = out_dir / "cells"
    cells_dir.mkdir(parents=True, exist_ok=True)

    rows, cols = args.rows, args.cols
    names: list[str] | None = None
    if args.names:
        raw = Path(args.names).read_text(encoding="utf-8").splitlines()
        names = [ln.strip() for ln in raw if ln.strip()]

    src = Image.open(src_path)
    print(f"source: {src_path.name} {src.size}")

    rgba = key_white_bg(src)
    out_path = out_dir / "sheet_transparent.png"
    rgba.save(out_path)
    a = np.asarray(rgba)[..., 3]
    print(f"alpha: transparent%={(a < 10).mean() * 100:.1f}  -> {out_path.name}")

    for i, cell in enumerate(slice_grid(rgba, src_rgb=src, rows=rows, cols=cols, cut_tol=args.cut_tol)):
        if names and i < len(names):
            fname = f"{names[i]}.png"
        else:
            fname = f"{i + 1:02d}.png"
        cell.save(cells_dir / fname)
    print(f"sliced {rows * cols} cells ({cells_dir})")


if __name__ == "__main__":
    main()

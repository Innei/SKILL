#!/usr/bin/env python3
# /// script
# dependencies = ["Pillow", "numpy"]
# ///
from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

CANVAS = (4800, 2700)
CACHE = Path.home() / ".cache" / "product-visuals" / "bezels"
IPHONE_BEZELS = {
    "silver": "iphone-17-pro-silver-portrait.png",
    "deep-blue": "iphone-17-pro-deep-blue-portrait.png",
    "cosmic-orange": "iphone-17-pro-cosmic-orange-portrait.png",
}
MAC_BEZELS = {
    "space-black": "macbook-pro-m5-14-space-black.png",
    "silver": "macbook-pro-m5-14-silver.png",
}


def interior_mask(bezel: Image.Image) -> np.ndarray:
    alpha = np.asarray(bezel.split()[-1])
    h, w = alpha.shape
    trans = alpha < 16
    ext = np.zeros((h, w), dtype=bool)
    q = deque()

    def push(y: int, x: int) -> None:
        if 0 <= y < h and 0 <= x < w and trans[y, x] and not ext[y, x]:
            ext[y, x] = True
            q.append((y, x))

    for x in range(w):
        push(0, x)
        push(h - 1, x)
    for y in range(h):
        push(y, 0)
        push(y, w - 1)
    while q:
        y, x = q.popleft()
        push(y - 1, x)
        push(y + 1, x)
        push(y, x - 1)
        push(y, x + 1)
    return trans & ~ext


def clean_rgba(im: Image.Image) -> Image.Image:
    a = np.asarray(im.convert("RGBA")).copy()
    a[a[:, :, 3] == 0, :3] = 0
    return Image.fromarray(a)


def resize_rgba(im: Image.Image, size: tuple[int, int]) -> Image.Image:
    arr = np.asarray(clean_rgba(im)).astype(np.float32)
    alpha = arr[:, :, 3:4] / 255.0
    arr[:, :, :3] *= alpha
    premul = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    resized = premul.resize(size, Image.Resampling.LANCZOS)
    out = np.asarray(resized).astype(np.float32)
    a = out[:, :, 3:4]
    np.divide(out[:, :, :3], a / 255.0, out=out[:, :, :3], where=a > 0)
    out[a[:, :, 0] == 0, :3] = 0
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def cover(src: Image.Image, box: tuple[int, int, int, int], top: bool = False) -> Image.Image:
    tw, th = box[2] - box[0], box[3] - box[1]
    sw, sh = src.size
    scale = max(tw / sw, th / sh)
    nw, nh = max(1, int(sw * scale)), max(1, int(sh * scale))
    img = src.convert("RGB").resize((nw, nh), Image.Resampling.LANCZOS)
    left = (nw - tw) // 2
    top_off = 0 if top else (nh - th) // 2
    return img.crop((left, top_off, left + tw, top_off + th))


def frame_device(bezel_path: Path, shot_path: Path, top: bool = False) -> Image.Image:
    bezel = clean_rgba(Image.open(bezel_path))
    shot = Image.open(shot_path)
    hole = interior_mask(bezel)
    ys, xs = np.where(hole)
    if len(xs) == 0:
        raise SystemExit(f"no screen hole in {bezel_path}")
    x0, y0 = int(xs.min()), int(ys.min())
    x1, y1 = int(xs.max()) + 1, int(ys.max()) + 1
    screen = cover(shot, (x0, y0, x1, y1), top=top)
    clip = hole[y0:y1, x0:x1]
    screen_rgba = np.dstack(
        [np.asarray(screen), np.where(clip, 255, 0).astype(np.uint8)]
    )
    base = Image.new("RGBA", bezel.size, (0, 0, 0, 0))
    layer = Image.fromarray(screen_rgba)
    base.paste(layer, (x0, y0), layer)
    return Image.alpha_composite(base, bezel)


def contact_shadow(
    device: Image.Image, blur: int = 70, opacity: float = 0.38, spread: float = 0.92
):
    alpha = np.asarray(device.split()[-1])
    ys, xs = np.where(alpha > 200)
    if len(xs) == 0:
        return Image.new("RGBA", device.size, (0, 0, 0, 0)), (0, 0)
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    body_h = y1 - y0
    band = alpha[y1 - max(8, body_h // 7) : y1, x0:x1]
    stamp = Image.fromarray(band)
    tw = max(2, int((x1 - x0) * spread))
    th = max(2, int((y1 - y0) * 0.08))
    stamp = stamp.resize((tw, th), Image.Resampling.LANCZOS)
    pad = blur * 3
    layer = Image.new("L", (tw + pad * 2, th + pad * 2), 0)
    layer.paste(stamp, (pad, pad))
    layer = layer.point(lambda v: int(v * opacity))
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    shadow = Image.merge(
        "RGBA",
        (
            Image.new("L", layer.size, 0),
            Image.new("L", layer.size, 0),
            Image.new("L", layer.size, 0),
            layer,
        ),
    )
    ox = x0 + (x1 - x0 - tw) // 2 - pad
    oy = y1 - th // 2 - pad
    return shadow, (ox, oy)


def scale_to_width(im: Image.Image, width: int) -> Image.Image:
    h = int(im.height * (width / im.width))
    return resize_rgba(im, (width, h))


def scale_to_height(im: Image.Image, height: int) -> Image.Image:
    w = int(im.width * (height / im.height))
    return resize_rgba(im, (w, height))


def studio_bg(size: tuple[int, int]) -> Image.Image:
    w, h = size
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    xn, yn = xs / max(w - 1, 1), ys / max(h - 1, 1)
    base = np.zeros((h, w, 3), dtype=np.float32)
    base[..., 0] = 12 + 8 * yn
    base[..., 1] = 13 + 7 * yn
    base[..., 2] = 20 + 10 * (1 - yn)
    rose = np.exp(-((xn - 0.88) ** 2) / 0.08 - (yn - 0.82) ** 2 / 0.10)
    blue = np.exp(-((xn - 0.18) ** 2) / 0.10 - (yn - 0.16) ** 2 / 0.08)
    base[..., 0] += 70 * rose + 18 * blue
    base[..., 1] += 38 * rose + 42 * blue
    base[..., 2] += 32 * rose + 80 * blue
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")


def load_bg(path: Path | None, size: tuple[int, int], dim: float) -> Image.Image:
    if path is None:
        return studio_bg(size)
    bg = Image.open(path).convert("RGB").resize(size, Image.Resampling.LANCZOS)
    if dim < 1:
        bg = ImageEnhance.Brightness(bg).enhance(dim)
    return bg.convert("RGBA")


def paste(canvas: Image.Image, layer: Image.Image, origin: tuple[int, int]) -> None:
    x, y = origin
    sx = sy = 0
    if x < 0:
        sx = -x
        x = 0
    if y < 0:
        sy = -y
        y = 0
    if sx or sy:
        layer = layer.crop((sx, sy, layer.width, layer.height))
    canvas.alpha_composite(layer, (x, y))


def resolve_bezel(explicit: Path | None, cache_name: str) -> Path:
    if explicit is not None:
        path = explicit.expanduser()
        if not path.is_file():
            raise SystemExit(f"bezel not found: {path}")
        return path
    env = Path.home() / ".cache" / "product-visuals" / "bezels"
    for root in (Path.cwd(), env, CACHE):
        cand = root / cache_name
        if cand.is_file():
            return cand
    raise SystemExit(
        f"missing {cache_name}; run scripts/fetch-bezels.sh (Apple Design Resources)"
    )


def dual_device_hero(args: argparse.Namespace) -> None:
    w, h = args.width, args.height
    sx, sy = w / CANVAS[0], h / CANVAS[1]
    canvas = load_bg(args.bg, (w, h), args.bg_dim)
    mac = scale_to_width(
        frame_device(args.mac_bezel, args.mac, top=True), int(3360 * sx)
    )
    phone = scale_to_height(
        frame_device(args.iphone_bezel, args.phone, top=True), int(1720 * sy)
    )
    mac_pos = (int(150 * sx), int(150 * sy))
    phone_pos = (int(3080 * sx), int(820 * sy))
    mac_shadow, mac_off = contact_shadow(mac, blur=78, opacity=0.34, spread=0.9)
    phone_shadow, phone_off = contact_shadow(phone, blur=54, opacity=0.3, spread=0.82)
    paste(canvas, mac_shadow, (mac_pos[0] + mac_off[0], mac_pos[1] + mac_off[1]))
    paste(canvas, phone_shadow, (phone_pos[0] + phone_off[0], phone_pos[1] + phone_off[1]))
    paste(canvas, mac, mac_pos)
    paste(canvas, phone, phone_pos)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(args.out, "PNG", optimize=True)
    print(args.out)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="compose.py")
    sub = p.add_subparsers(dest="recipe", required=True)

    hero = sub.add_parser("dual-device-hero")
    hero.add_argument("--phone", type=Path, required=True)
    hero.add_argument("--mac", type=Path, required=True)
    hero.add_argument("--out", type=Path, required=True)
    hero.add_argument("--bg", type=Path, default=None)
    hero.add_argument("--bg-dim", type=float, default=1.0)
    hero.add_argument("--iphone-color", choices=IPHONE_BEZELS, default="silver")
    hero.add_argument("--mac-color", choices=MAC_BEZELS, default="space-black")
    hero.add_argument("--iphone-bezel", type=Path, default=None)
    hero.add_argument("--mac-bezel", type=Path, default=None)
    hero.add_argument("--width", type=int, default=CANVAS[0])
    hero.add_argument("--height", type=int, default=CANVAS[1])
    hero.set_defaults(func=dual_device_hero)
    return p


def main() -> None:
    args = build_parser().parse_args()
    if args.recipe == "dual-device-hero":
        args.iphone_bezel = resolve_bezel(
            args.iphone_bezel, IPHONE_BEZELS[args.iphone_color]
        )
        args.mac_bezel = resolve_bezel(args.mac_bezel, MAC_BEZELS[args.mac_color])
        for label, path in (("phone", args.phone), ("mac", args.mac)):
            if not path.expanduser().is_file():
                raise SystemExit(f"{label} screenshot not found: {path}")
            setattr(args, label, path.expanduser())
        if args.bg is not None:
            args.bg = args.bg.expanduser()
            if not args.bg.is_file():
                raise SystemExit(f"background not found: {args.bg}")
        args.out = args.out.expanduser()
    args.func(args)


if __name__ == "__main__":
    main()

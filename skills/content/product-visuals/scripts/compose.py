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
MACOS_UI_CACHE = Path.home() / ".cache" / "product-visuals" / "macos-ui"
DEFAULT_MAC_MENU_BAR = MACOS_UI_CACHE / "macos-27-menu-bar.png"
PHONE_X_IN_MAC = 0.88
PHONE_Y_IN_MAC = 0.24
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


def hide_framebuffer_island(shot: Image.Image) -> Image.Image:
    rgb = np.asarray(shot.convert("RGB")).copy()
    h, w = rgb.shape[:2]
    if h < int(w * 1.8) or w < 200:
        return shot.convert("RGB")
    lum = rgb.mean(axis=2)
    cx = w // 2
    top = min(h, max(96, h // 12))
    dark = lum[:top] < 12
    ys, xs = np.where(dark)
    if len(xs) < 80:
        return Image.fromarray(rgb)
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    if (x1 - x0) < w * 0.18 or (x1 - x0) > w * 0.55:
        return Image.fromarray(rgb)
    if abs((x0 + x1) / 2 - cx) > w * 0.08:
        return Image.fromarray(rgb)
    if (y1 - y0) < 24 or (y1 - y0) > top * 0.9:
        return Image.fromarray(rgb)
    pad = max(8, (x0) // 8)
    sample = rgb[y0:y1, max(0, x0 - pad - 40) : max(0, x0 - 8)]
    if sample.size == 0:
        sample = rgb[y0:y1, min(w, x1 + 8) : min(w, x1 + pad + 40)]
    if sample.size == 0:
        return Image.fromarray(rgb)
    fill = sample.reshape(-1, 3).mean(axis=0)
    rgb[y0:y1, x0:x1] = fill
    return Image.fromarray(rgb)


def screen_bbox(bezel: Image.Image) -> tuple[int, int, int, int]:
    hole = interior_mask(bezel)
    ys, xs = np.where(hole)
    if len(xs) == 0:
        raise SystemExit("device bezel has no screen hole")
    x0, y0 = int(xs.min()), int(ys.min())
    x1, y1 = int(xs.max()) + 1, int(ys.max()) + 1
    return x0, y0, x1, y1


def frame_device_image(
    bezel: Image.Image, shot: Image.Image, top: bool = False
) -> Image.Image:
    bezel = clean_rgba(bezel)
    x0, y0, x1, y1 = screen_bbox(bezel)
    hole = interior_mask(bezel)
    screen = cover(shot, (x0, y0, x1, y1), top=top)
    clip = hole[y0:y1, x0:x1]
    screen_rgba = np.dstack(
        [np.asarray(screen), np.where(clip, 255, 0).astype(np.uint8)]
    )
    base = Image.new("RGBA", bezel.size, (0, 0, 0, 0))
    layer = Image.fromarray(screen_rgba)
    base.paste(layer, (x0, y0), layer)
    return Image.alpha_composite(base, bezel)


def frame_device(bezel_path: Path, shot_path: Path, top: bool = False) -> Image.Image:
    bezel = Image.open(bezel_path)
    shot = hide_framebuffer_island(Image.open(shot_path))
    return frame_device_image(bezel, shot, top=top)


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


def opaque_bbox(im: Image.Image, threshold: int = 8) -> tuple[int, int, int, int]:
    alpha = np.asarray(im.split()[-1])
    ys, xs = np.where(alpha > threshold)
    if len(xs) == 0:
        return (0, 0, im.width, im.height)
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def dual_hero_positions(
    canvas: tuple[int, int], mac: Image.Image, phone: Image.Image
) -> tuple[tuple[int, int], tuple[int, int]]:
    cw, ch = canvas
    mx0, my0, mx1, my1 = opaque_bbox(mac)
    px0, py0, px1, py1 = opaque_bbox(phone)
    mac_ow, mac_oh = mx1 - mx0, my1 - my0
    phone_pos = (
        mx0 + int(mac_ow * PHONE_X_IN_MAC) - px0,
        my0 + int(mac_oh * PHONE_Y_IN_MAC) - py0,
    )
    union_l = min(mx0, phone_pos[0] + px0)
    union_t = min(my0, phone_pos[1] + py0)
    union_r = max(mx1, phone_pos[0] + px1)
    union_b = max(my1, phone_pos[1] + py1)
    dx = (cw - (union_r - union_l)) // 2 - union_l
    dy = (ch - (union_b - union_t)) // 2 - union_t
    return (dx, dy), (phone_pos[0] + dx, phone_pos[1] + dy)


def scale_to_width(im: Image.Image, width: int) -> Image.Image:
    h = int(im.height * (width / im.width))
    return resize_rgba(im, (width, h))


def scale_to_height(im: Image.Image, height: int) -> Image.Image:
    w = int(im.width * (height / im.height))
    return resize_rgba(im, (w, height))


Rgb = tuple[float, float, float]


def shot_palette(paths: list[Path]) -> tuple[Rgb, Rgb, Rgb]:
    chunks = []
    for path in paths:
        im = Image.open(path).convert("RGB")
        im.thumbnail((96, 96), Image.Resampling.BOX)
        chunks.append(np.asarray(im, dtype=np.float32).reshape(-1, 3))
    pix = np.concatenate(chunks, axis=0)
    lum = pix @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    mid = float(np.median(lum))
    dark = pix[lum <= mid]
    light = pix[lum >= mid]
    if len(dark) == 0:
        dark = pix
    if len(light) == 0:
        light = pix
    base = tuple(float(v) for v in dark.mean(axis=0))
    lift = tuple(float(v) for v in light.mean(axis=0))
    chroma = pix.max(axis=1) - pix.min(axis=1)
    sat = chroma > 25
    if sat.any():
        thresh = float(np.percentile(chroma[sat], 70))
        accent = tuple(float(v) for v in pix[chroma >= thresh].mean(axis=0))
    else:
        accent = lift
    return base, lift, accent


def tone_bg(size: tuple[int, int], base: Rgb, lift: Rgb, accent: Rgb) -> Image.Image:
    w, h = size
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    xn, yn = xs / max(w - 1, 1), ys / max(h - 1, 1)
    canvas = np.zeros((h, w, 3), dtype=np.float32)
    t = 0.35 * (1 - yn) + 0.15 * (1 - xn)
    for i in range(3):
        canvas[..., i] = base[i] + (lift[i] - base[i]) * t
    blob = np.exp(-((xn - 0.86) ** 2) / 0.10 - ((yn - 0.82) ** 2) / 0.12)
    mix = blob * 0.18
    canvas += (np.array(accent, dtype=np.float32) - canvas) * mix[..., None]
    return Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8)).convert("RGBA")


def default_mac_wallpaper(size: tuple[int, int]) -> Image.Image:
    """Return a quiet, privacy-safe wallpaper when no public wallpaper is supplied."""
    return tone_bg(
        size,
        (82.0, 62.0, 49.0),
        (218.0, 196.0, 170.0),
        (188.0, 143.0, 91.0),
    )


def load_default_macos_menu_bar() -> Image.Image:
    """Load the official macOS UI Kit Menu Bar exported into the local cache."""
    if not DEFAULT_MAC_MENU_BAR.is_file():
        raise SystemExit(
            "missing official macOS Menu Bar; export Menu Bar.svg from Apple's "
            "macOS UI Kit, then run scripts/cache-macos-menu-bar.sh <MenuBar.svg>"
        )
    with Image.open(DEFAULT_MAC_MENU_BAR) as image:
        return clean_rgba(image)


def compose_mac_desktop(
    window: Image.Image,
    size: tuple[int, int],
    wallpaper: Image.Image | None = None,
    menu_bar: Image.Image | None = None,
) -> Image.Image:
    """Build wallpaper -> menu bar -> real window; never add a window shadow."""
    w, h = size
    if wallpaper is None:
        scene = default_mac_wallpaper(size)
    else:
        scene = cover(wallpaper, (0, 0, w, h), top=False).convert("RGBA")

    bar = load_default_macos_menu_bar() if menu_bar is None else clean_rgba(menu_bar)
    if bar.width != w:
        bar = resize_rgba(bar, (w, max(1, round(bar.height * w / bar.width))))
    scene.alpha_composite(bar, (0, 0))

    window = clean_rgba(window)
    x0, y0, x1, _y1 = opaque_bbox(window, threshold=1)
    visible_w = max(1, x1 - x0)
    target_w = round(w * 0.88)
    scale = target_w / visible_w
    resized = resize_rgba(
        window,
        (max(1, round(window.width * scale)), max(1, round(window.height * scale))),
    )
    visible_top = round(y0 * scale)
    window_x = (w - target_w) // 2 - round(x0 * scale)
    window_y = max(bar.height + round(20 * w / 3024), round(h * 0.07)) - visible_top
    scene.alpha_composite(resized, (window_x, window_y))
    return scene.convert("RGB")


def load_bg(
    path: Path | None,
    size: tuple[int, int],
    dim: float,
    shots: list[Path] | None = None,
) -> Image.Image:
    if path is not None:
        bg = Image.open(path).convert("RGB").resize(size, Image.Resampling.LANCZOS)
    elif shots:
        base, lift, accent = shot_palette(shots)
        bg = tone_bg(size, base, lift, accent)
    else:
        bg = tone_bg(
            size, (20.0, 20.0, 22.0), (38.0, 36.0, 34.0), (38.0, 36.0, 34.0)
        )
    if dim < 1:
        bg = ImageEnhance.Brightness(bg.convert("RGB")).enhance(dim)
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
    canvas = load_bg(
        args.bg, (w, h), args.bg_dim, shots=[args.phone, args.mac]
    )
    mac_bezel = clean_rgba(Image.open(args.mac_bezel))
    mx0, my0, mx1, my1 = screen_bbox(mac_bezel)
    mac_scene = compose_mac_desktop(
        Image.open(args.mac),
        (mx1 - mx0, my1 - my0),
        wallpaper=Image.open(args.mac_wallpaper) if args.mac_wallpaper else None,
        menu_bar=Image.open(args.mac_menu_bar) if args.mac_menu_bar else None,
    )
    mac = scale_to_width(
        frame_device_image(mac_bezel, mac_scene, top=True), int(3360 * sx)
    )
    phone = scale_to_height(
        frame_device(args.iphone_bezel, args.phone, top=True), int(1720 * sy)
    )
    mac_pos, phone_pos = dual_hero_positions((w, h), mac, phone)
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
    hero.add_argument("--mac-wallpaper", type=Path, default=None)
    hero.add_argument("--mac-menu-bar", type=Path, default=None)
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
        for label, path in (
            ("phone", args.phone),
            ("mac", args.mac),
            ("mac wallpaper", args.mac_wallpaper),
            ("mac menu bar", args.mac_menu_bar),
        ):
            if path is None:
                continue
            if not path.expanduser().is_file():
                raise SystemExit(f"{label} screenshot not found: {path}")
            attr = label.replace(" ", "_")
            setattr(args, attr, path.expanduser())
        if args.bg is not None:
            args.bg = args.bg.expanduser()
            if not args.bg.is_file():
                raise SystemExit(f"background not found: {args.bg}")
        args.out = args.out.expanduser()
    args.func(args)


if __name__ == "__main__":
    main()

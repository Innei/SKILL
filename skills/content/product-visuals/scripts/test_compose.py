#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path

from PIL import Image

import tempfile

from compose import (
    CANVAS,
    dual_hero_positions,
    expand_baked_display_corners,
    load_bg,
    opaque_bbox,
    scale_to_height,
    scale_to_width,
    shot_palette,
)

CACHE = Path.home() / ".cache" / "product-visuals" / "bezels"


def _device(size: tuple[int, int], box: tuple[int, int, int, int]) -> Image.Image:
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    x0, y0, x1, y1 = box
    im.paste(Image.new("RGBA", (x1 - x0, y1 - y0), (40, 40, 40, 255)), (x0, y0))
    return im


def _offset(box: tuple[int, int, int, int], origin: tuple[int, int]) -> tuple[int, int, int, int]:
    x, y = origin
    return box[0] + x, box[1] + y, box[2] + x, box[3] + y


def _union(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    return min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])


class OpaqueBboxTests(unittest.TestCase):
    def test_ignores_transparent_padding(self) -> None:
        im = _device((200, 100), (20, 30, 180, 90))
        self.assertEqual(opaque_bbox(im), (20, 30, 180, 90))


class DualHeroPositionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.canvas = CANVAS
        self.mac = _device((3360, 2211), (24, 202, 3336, 2202))
        self.phone = _device((841, 1720), (10, 13, 831, 1706))

    def _boxes(self, mac: Image.Image, phone: Image.Image):
        mac_pos, phone_pos = dual_hero_positions(self.canvas, mac, phone)
        mac_box = _offset(opaque_bbox(mac), mac_pos)
        phone_box = _offset(opaque_bbox(phone), phone_pos)
        return mac_pos, phone_pos, mac_box, phone_box, _union(mac_box, phone_box)

    def _placed(self):
        return self._boxes(self.mac, self.phone)

    def test_opaque_union_is_centered_on_canvas(self) -> None:
        _, _, _, _, union = self._placed()
        left, top, right, bottom = union
        cw, ch = self.canvas
        self.assertLessEqual(abs(left - (cw - right)), 1)
        self.assertLessEqual(abs(top - (ch - bottom)), 1)

    def test_bezel_padding_does_not_shift_the_chassis(self) -> None:
        phone = self.phone
        padded = _device((3360, 2211), (24, 202, 3336, 2202))
        tight = _device((3360, 2019), (24, 10, 3336, 2010))
        _, _, padded_box, _, _ = self._boxes(padded, phone)
        _, _, tight_box, _, _ = self._boxes(tight, phone)
        self.assertLessEqual(abs(padded_box[1] - tight_box[1]), 1)
        self.assertLessEqual(abs(padded_box[0] - tight_box[0]), 1)

    def test_phone_overlaps_lower_right_of_mac(self) -> None:
        _, _, mac_box, phone_box, _ = self._placed()
        self.assertLess(phone_box[0], mac_box[2])
        self.assertGreater(phone_box[2], mac_box[2])
        self.assertGreater(phone_box[1], mac_box[1])
        self.assertGreater(phone_box[3], mac_box[3])


@unittest.skipUnless(
    (CACHE / "macbook-pro-m5-14-space-black.png").is_file()
    and (CACHE / "iphone-17-pro-silver-portrait.png").is_file(),
    "Apple bezels not cached",
)
class RealBezelLayoutTests(unittest.TestCase):
    def test_real_bezel_group_is_centered(self) -> None:
        mac = scale_to_width(
            Image.open(CACHE / "macbook-pro-m5-14-space-black.png"), 3360
        )
        phone = scale_to_height(
            Image.open(CACHE / "iphone-17-pro-silver-portrait.png"), 1720
        )
        mac_pos, phone_pos = dual_hero_positions(CANVAS, mac, phone)
        union = _union(
            _offset(opaque_bbox(mac), mac_pos),
            _offset(opaque_bbox(phone), phone_pos),
        )
        left, top, right, bottom = union
        self.assertLessEqual(abs(left - (CANVAS[0] - right)), 1)
        self.assertLessEqual(abs(top - (CANVAS[1] - bottom)), 1)


class ExpandBakedDisplayCornersTests(unittest.TestCase):
    def test_fills_black_corner_pies_and_keeps_glyphs(self) -> None:
        im = Image.new("RGB", (400, 220), (126, 95, 69))
        px = im.load()
        for y in range(28):
            for x in range(28):
                if x * x + y * y <= 28 * 28:
                    px[x, y] = (0, 0, 0)
                    px[399 - x, y] = (0, 0, 0)
        for x in range(40, 55):
            for y in range(8, 24):
                px[x, y] = (240, 240, 235)
        out = expand_baked_display_corners(im)
        self.assertGreater(sum(out.getpixel((0, 0))), 80)
        self.assertGreater(sum(out.getpixel((399, 0))), 80)
        self.assertGreater(out.getpixel((48, 16))[0], 180)


class ShotPaletteTests(unittest.TestCase):
    def _swatch(self, rgb: tuple[int, int, int], accent: tuple[int, int, int] | None = None) -> Path:
        im = Image.new("RGB", (96, 96), rgb)
        if accent is not None:
            for x in range(12, 36):
                for y in range(12, 36):
                    im.putpixel((x, y), accent)
        path = Path(tempfile.mkdtemp()) / "shot.png"
        im.save(path)
        return path

    def test_ume_on_charcoal_accent_is_warm_not_blue(self) -> None:
        path = self._swatch((20, 20, 22), (197, 100, 115))
        base, _lift, accent = shot_palette([path])
        self.assertLess(sum(base) / 3, 80)
        self.assertGreater(accent[0], accent[2])

    def test_fallback_bg_is_not_cinematic_blue(self) -> None:
        path = self._swatch((20, 20, 22), (197, 100, 115))
        bg = load_bg(None, (240, 135), 1.0, shots=[path])
        arr = __import__("numpy").asarray(bg.convert("RGB"), dtype=float)
        self.assertGreaterEqual(arr[..., 0].mean() + 4, arr[..., 2].mean())


if __name__ == "__main__":
    unittest.main()

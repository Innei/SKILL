# /// script
# dependencies = ["Pillow", "google-genai", "python-dotenv"]
# ///
"""Offline CLI regression checks; only the external Codex process is faked.

Run: uv run test_generation.py
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

SCRIPTS = Path(__file__).resolve().parent


class GenerationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="chibi-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.char = self.root / "character ref.png"
        self.anchor = self.root / "style anchor.png"
        Image.new("RGB", (32, 32), "red").save(self.char)
        Image.new("RGB", (32, 32), "blue").save(self.anchor)
        self.prompt = self.root / "prompt.txt"
        self.prompt.write_text("Create a chibi sticker smoke test.", encoding="utf-8")
        self.env = {
            key: value for key, value in os.environ.items()
            if not key.startswith(("GOOGLE_", "GEMINI_", "VERTEX_"))
        }
        self.env["HOME"] = str(self.root)
        self.env["PYTHONDONTWRITEBYTECODE"] = "1"
        fake_bin = self.root / "bin"
        fake_bin.mkdir()
        fake = fake_bin / "codex"
        fake.write_text(
            f"#!{sys.executable}\n" + '''
import os
import sys
from pathlib import Path
from PIL import Image

args = sys.argv[1:]
prompt = sys.stdin.read()
assert "exec" in args and "image_generation" in args
assert args[args.index("--sandbox") + 1] == "workspace-write"
assert "--dangerously-bypass-approvals-and-sandbox" not in args
assert "image_generation" in prompt
refs = [args[i + 1] for i, arg in enumerate(args) if arg == "--image"]
assert Image.open(refs[0]).getpixel((0, 0)) == (255, 0, 0)
if os.environ.get("EXPECT_ANCHOR"):
    assert len(refs) == 2
    assert Image.open(refs[1]).getpixel((0, 0)) == (0, 0, 255)
mode = os.environ.get("FAKE_CODEX", "success")
if mode == "fail":
    print("image tool unavailable", file=sys.stderr)
    sys.exit(7)
if mode == "missing":
    print("Here is a description, without an image.")
elif mode == "corrupt":
    Path("generated.png").write_text("not a PNG")
else:
    Image.new("RGBA", (160, 90), (24, 48, 72, 255)).save("generated.png")
''',
            encoding="utf-8",
        )
        fake.chmod(0o755)
        self.env["PATH"] = str(fake_bin) + os.pathsep + self.env["PATH"]

    def run_script(self, name: str, *args: object) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPTS / name), *map(str, args)],
            cwd=self.root, env=self.env, text=True, capture_output=True, timeout=30, check=False,
        )

    def assert_success(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_sheet_defaults_to_codex_without_google_credentials_and_passes_anchor(self) -> None:
        self.env["EXPECT_ANCHOR"] = "1"
        output = self.root / "nested" / "sheet.png"
        result = self.run_script(
            "generate.py", self.char, self.prompt, output, "--anchor", self.anchor,
        )
        self.assert_success(result)
        with Image.open(output) as image:
            self.assertEqual(image.size, (160, 90))
            self.assertEqual(image.mode, "RGB")
            self.assertEqual(image.getpixel((0, 0)), (24, 48, 72))

    def test_banner_explicit_codex_keeps_platform_dimensions(self) -> None:
        output = self.root / "banner.png"
        result = self.run_script(
            "generate_banner.py", self.char, "spring", output,
            "--platform", "twitter", "--provider", "codex",
        )
        self.assert_success(result)
        with Image.open(output) as image:
            self.assertEqual(image.size, (1500, 500))

    def test_extras_default_to_codex_and_keep_transparent_cover_and_icon(self) -> None:
        stickers = self.root / "stickers"
        cells = stickers / "cells"
        cells.mkdir(parents=True)
        Image.new("RGBA", (64, 64), (100, 50, 25, 0)).save(cells / "07.png")
        result = self.run_script("generate_extras.py", stickers, self.char, "spring")
        self.assert_success(result)
        for name, size in (("banner", (750, 400)), ("cover", (240, 240)), ("icon", (50, 50))):
            with Image.open(stickers / f"{name}.png") as image:
                self.assertEqual(image.size, size)
                if name != "banner":
                    self.assertEqual(image.mode, "RGBA")
                    self.assertEqual(image.getpixel((0, 0))[3], 0)

    def test_codex_failure_does_not_fall_back_or_replace_existing_output(self) -> None:
        self.env["FAKE_CODEX"] = "fail"
        output = self.root / "existing.png"
        output.write_bytes(b"existing user image")
        result = self.run_script("generate.py", self.char, self.prompt, output)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("image tool unavailable", result.stdout + result.stderr)
        self.assertEqual(output.read_bytes(), b"existing user image")

    def test_text_only_or_corrupt_codex_output_is_not_success(self) -> None:
        for mode in ("missing", "corrupt"):
            with self.subTest(mode=mode):
                self.env["FAKE_CODEX"] = mode
                output = self.root / f"{mode}.png"
                result = self.run_script("generate.py", self.char, self.prompt, output)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Codex", result.stdout + result.stderr)
                self.assertFalse(output.exists())

    def test_explicit_gemini_uses_its_auth_instead_of_codex(self) -> None:
        output = self.root / "gemini.png"
        result = self.run_script(
            "generate.py", self.char, self.prompt, output, "--provider", "gemini",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("No API key", result.stdout + result.stderr)
        self.assertFalse(output.exists())

    def test_gemini_still_decodes_images_and_sends_both_reference_images(self) -> None:
        from generate import generate_sheet
        from generate_banner import PLATFORMS, generate_banner
        from google.genai import types

        payload = io.BytesIO()
        Image.new("RGB", (160, 90), (12, 34, 56)).save(payload, "PNG")
        requests = []

        def respond(**kwargs):
            requests.append(kwargs)
            return types.GenerateContentResponse(candidates=[types.Candidate(
                content=types.Content(parts=[types.Part.from_bytes(
                    data=payload.getvalue(), mime_type="image/png",
                )]),
            )])

        client = SimpleNamespace(models=SimpleNamespace(generate_content=respond))
        with patch.dict(os.environ, {}, clear=True), patch("generate._make_client", return_value=client):
            char, anchor = Image.open(self.char), Image.open(self.anchor)
            sheet = generate_sheet("stickers", char, anchor, provider="gemini")
            banner = generate_banner(char, "spring", PLATFORMS["wechat"], provider="gemini")

        self.assertEqual(sheet.getpixel((0, 0)), (12, 34, 56))
        self.assertEqual(sheet.mode, "RGB")
        self.assertEqual(banner.size, (750, 400))
        self.assertEqual(requests[0]["contents"], [char, anchor, "stickers"])
        self.assertEqual(requests[0]["config"].image_config.aspect_ratio, "1:1")
        self.assertEqual(requests[0]["config"].image_config.image_size, "2K")
        self.assertEqual(requests[1]["config"].image_config.aspect_ratio, "16:9")
        self.assertIsNone(requests[1]["config"].image_config.image_size)


if __name__ == "__main__":
    unittest.main()

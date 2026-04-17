# /// script
# dependencies = ["requests", "python-dotenv", "Pillow"]
# ///
"""Upload a chibi sticker cell directory to Telegram as a sticker set.

Usage:
    uv run upload_telegram.py <cells_dir> <set_name_prefix> <set_title> \\
        [--token BOT_TOKEN] [--user-id USER_ID] [--emoji-map emoji_map.json]
        [--replace-set EXISTING_SET_NAME]

    cells_dir        : directory of named PNG stickers (e.g. /tmp/sticker_sailor/cells)
    set_name_prefix  : short ASCII prefix, e.g. "shione_sailor"  (bot suffix appended auto)
    set_title        : display name, e.g. "汐音 Sailor 表情包"

    --token          : bot token (or set TELEGRAM_BOT_TOKEN env var)
    --user-id        : Telegram user id who owns the set (or set TELEGRAM_USER_ID)
    --emoji-map      : optional JSON file {filename_stem: emoji}; auto-mapped if omitted
    --replace-set    : full existing set name to overwrite (e.g. ShioneSchool);
                       uses replaceStickerInSet to overwrite in-place, preserving the URL

Environment fallback: TELEGRAM_BOT_TOKEN, TELEGRAM_USER_ID, .env / ~/.env

Sticker requirements (Telegram):
    - PNG, ≤512×512, ≤512 KB, transparent background recommended
    - Set name: [a-z0-9_]+_by_<botusername>  (auto-appended)
    - Max 120 stickers per set
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Default emoji mapping (expression_name → emoji)
# ---------------------------------------------------------------------------
DEFAULT_EMOJI_MAP: dict[str, str] = {
    # joy / excitement
    "joy_jump":           "🎉",
    "cheer_fists":        "🙌",
    "thumbs_up_wink":     "👍",
    "victory_peace":      "✌️",
    "determined_fist":    "💪",
    "podium_triumph":     "🏆",
    "sparkle_dance":      "💃",
    "cheerleader_pom":    "📣",
    "final_bow_sparkle":  "✨",
    "cheerful_skip":      "😊",
    "zoom_run":           "🏃",
    "puddle_splash":      "💦",
    "hyper_wave":         "👋",
    "blowing_kiss":       "😘",
    # sadness / crying
    "waterfall_tears":    "😭",
    "face_buried_sob":    "😢",
    "single_tear":        "🥹",
    "tissue_wipe":        "🤧",
    "sobbing_fountain":   "😭",
    "pouty_rain":         "🌧️",
    "head_desk":          "🤦",
    # anger / frustration
    "puffed_rage":        "😤",
    "angry_stomp":        "😠",
    "point_rage":         "😡",
    "screaming_rage":     "🤬",
    "tantrum_stomp":      "👿",
    "grumpy_sideye":      "🙄",
    "smug_ignore":        "😌",
    # surprise / shock
    "home_alone_shock":   "😱",
    "startle_leap":       "😨",
    "tumble_backwards":   "😵",
    "lightbulb_idea":     "💡",
    "gift_receive":       "🎁",
    "scared_ghost":       "👻",
    # shy / embarrassed
    "shy_fingertips":     "🙈",
    "ear_cover_blush":    "😳",
    "melting_embarrassed":"🫠",
    "facepalm":           "🤦",
    "nervous_laugh":      "😅",
    # calm / smug / special
    "smug_cross":         "😏",
    "tea_sip_elegant":    "🍵",
    "lecture_finger":     "☝️",
    "finger_gun":         "👈",
    "hand_mirror_vain":   "🪞",
    "money_eyes":         "🤑",
    "bunny_ears":         "🐰",
    "peek_corner":        "👀",
    "phone_scroll":       "📱",
    "question_mark":      "🤔",
    "curtain_bow":        "🎭",
    # love / cute
    "heart_eyes":         "😍",
    "lovesick_float":     "🥰",
    # tired / sleepy
    "sleepy_zzz":         "😴",
    "exhausted_slump":    "😩",
    "giant_yawn":         "🥱",
    "sleepy_walk":        "🌙",
    # relief / calm
    "relief_sigh":        "😮‍💨",
    "hiding_blanket":     "🛌",
    # other
    "pouty_sulk":         "😒",
    "panic_sprint":       "😰",
    "cold_shiver":        "🥶",
    "proud_chest_puff":   "😤",
    "spinning_dizzy":     "😵‍💫",
    "cookie_nom":         "🍪",
    "lovesick_float":     "🥰",
}

FALLBACK_EMOJI = "😊"


def load_env() -> None:
    for p in [Path.home() / ".env", Path.home() / ".env.local",
              Path.cwd() / ".env", Path.cwd() / ".env.local"]:
        if p.exists():
            load_dotenv(p)


def api(token: str, method: str, **kwargs) -> dict:
    url = f"https://api.telegram.org/bot{token}/{method}"
    for attempt in range(5):
        try:
            r = requests.post(url, timeout=60, **kwargs)
            data = r.json()
            if data.get("ok"):
                return data["result"]
            err = data.get("description", "unknown error")
            if "Too Many Requests" in err or "FLOOD" in err:
                wait = int(data.get("parameters", {}).get("retry_after", 10))
                print(f"  rate-limited, waiting {wait}s…")
                time.sleep(wait)
                continue
            raise RuntimeError(f"Telegram error on {method}: {err}")
        except requests.RequestException as exc:
            if attempt < 4:
                wait = 2 ** attempt * 3
                print(f"  network error ({exc}), retry in {wait}s…")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"{method} failed after retries")


def upload_sticker_file(token: str, user_id: int, png_path: Path) -> str:
    """Resize PNG to exactly 512×512 then upload to Telegram; return file_id."""
    import io
    from PIL import Image

    img = Image.open(png_path).convert("RGBA")
    if img.size != (512, 512):
        img = img.resize((512, 512), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    png_bytes = buf.getvalue()  # bytes survive retries; BytesIO seek would reset incorrectly
    result = api(token, "uploadStickerFile",
                 data={"user_id": user_id, "sticker_format": "static"},
                 files={"sticker": (png_path.name, png_bytes, "image/png")})
    return result["file_id"]


def _create_sticker_set(token: str, user_id: int, set_name: str, set_title: str, stickers: list[dict]) -> None:
    print("── creating sticker set ──")
    first = stickers[0]
    api(token, "createNewStickerSet",
        json={
            "user_id": user_id,
            "name": set_name,
            "title": set_title,
            "sticker_type": "regular",
            "stickers": [{
                "sticker": first["file_id"],
                "format": "static",
                "emoji_list": [first["emoji"]],
            }],
        })
    print(f"  created with first sticker: {first['name']}")

    print("── adding remaining stickers ──")
    for i, s in enumerate(stickers[1:], 2):
        print(f"  [{i:02d}/{len(stickers)}] {s['name']:30s} {s['emoji']}", end="", flush=True)
        api(token, "addStickerToSet",
            json={
                "user_id": user_id,
                "name": set_name,
                "sticker": {
                    "sticker": s["file_id"],
                    "format": "static",
                    "emoji_list": [s["emoji"]],
                },
            })
        print(" ✓")
        time.sleep(0.3)


def _replace_sticker_set(token: str, user_id: int, existing_name: str, stickers: list[dict]) -> None:
    """Overwrite an existing sticker set in-place, preserving its URL."""
    print(f"── fetching existing set: {existing_name} ──")
    existing = api(token, "getStickerSet", data={"name": existing_name})
    old_stickers = existing.get("stickers", [])
    print(f"  existing stickers: {len(old_stickers)}, new stickers: {len(stickers)}")

    overlap = min(len(old_stickers), len(stickers))

    print("── replacing stickers ──")
    for i in range(overlap):
        s = stickers[i]
        old_file_id = old_stickers[i]["file_id"]
        print(f"  [{i+1:02d}/{len(stickers)}] replace → {s['name']:30s} {s['emoji']}", end="", flush=True)
        api(token, "replaceStickerInSet",
            json={
                "user_id": user_id,
                "name": existing_name,
                "old_sticker": old_file_id,
                "sticker": {
                    "sticker": s["file_id"],
                    "format": "static",
                    "emoji_list": [s["emoji"]],
                },
            })
        print(" ✓")
        time.sleep(0.3)

    # If new set has more stickers, add the extras
    if len(stickers) > len(old_stickers):
        print("── adding extra stickers ──")
        for i in range(overlap, len(stickers)):
            s = stickers[i]
            print(f"  [{i+1:02d}/{len(stickers)}] add    → {s['name']:30s} {s['emoji']}", end="", flush=True)
            api(token, "addStickerToSet",
                json={
                    "user_id": user_id,
                    "name": existing_name,
                    "sticker": {
                        "sticker": s["file_id"],
                        "format": "static",
                        "emoji_list": [s["emoji"]],
                    },
                })
            print(" ✓")
            time.sleep(0.3)

    # If old set has more stickers, delete the extras (from the end)
    if len(old_stickers) > len(stickers):
        print("── deleting excess stickers ──")
        for i in range(overlap, len(old_stickers)):
            old_file_id = old_stickers[i]["file_id"]
            print(f"  delete old slot {i+1}", end="", flush=True)
            api(token, "deleteStickerFromSet", data={"sticker": old_file_id})
            print(" ✓")
            time.sleep(0.3)

    print()
    print(f"Done! Open in Telegram: https://t.me/addstickers/{existing_name}")


def main() -> None:
    load_env()

    parser = argparse.ArgumentParser(description="Upload stickers to Telegram.")
    parser.add_argument("cells_dir")
    parser.add_argument("set_name_prefix")
    parser.add_argument("set_title")
    parser.add_argument("--token",   default=os.environ.get("TELEGRAM_BOT_TOKEN"))
    parser.add_argument("--user-id", default=os.environ.get("TELEGRAM_USER_ID"), type=int, dest="user_id")
    parser.add_argument("--emoji-map", default=None, dest="emoji_map")
    parser.add_argument("--replace-set", default=None, dest="replace_set",
                        help="Full existing set name to overwrite in-place (e.g. ShioneSchool)")
    args = parser.parse_args()

    if not args.token:
        sys.exit("Missing bot token: pass --token or set TELEGRAM_BOT_TOKEN")
    if not args.user_id:
        sys.exit("Missing user id: pass --user-id or set TELEGRAM_USER_ID")

    emoji_map: dict[str, str] = dict(DEFAULT_EMOJI_MAP)
    if args.emoji_map:
        emoji_map.update(json.loads(Path(args.emoji_map).read_text()))

    cells_dir = Path(args.cells_dir)
    pngs = sorted(cells_dir.glob("*.png"))
    if not pngs:
        sys.exit(f"No PNG files found in {cells_dir}")

    # Get bot username for set name suffix
    me = api(args.token, "getMe")
    bot_username = me["username"]
    set_name = f"{args.set_name_prefix}_by_{bot_username}"
    print(f"bot          : @{bot_username}")
    print(f"set name     : {set_name}")
    print(f"set title    : {args.set_title}")
    print(f"stickers     : {len(pngs)}")
    print()

    # Upload all files first
    print("── uploading files ──")
    stickers: list[dict] = []
    for i, png in enumerate(pngs, 1):
        stem = png.stem
        emoji = emoji_map.get(stem, FALLBACK_EMOJI)
        print(f"  [{i:02d}/{len(pngs)}] {stem:30s} {emoji}")
        file_id = upload_sticker_file(args.token, args.user_id, png)
        stickers.append({"file_id": file_id, "emoji": emoji, "name": stem})
        time.sleep(0.3)  # gentle rate-limit buffer

    print()

    if args.replace_set:
        _replace_sticker_set(args.token, args.user_id, args.replace_set, stickers)
    else:
        _create_sticker_set(args.token, args.user_id, set_name, args.set_title, stickers)
        print(f"Done! Open in Telegram: https://t.me/addstickers/{set_name}")


if __name__ == "__main__":
    main()

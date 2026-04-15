# /// script
# dependencies = ["google-genai", "Pillow", "python-dotenv"]
# ///
"""Generate an ACG character settei sheet from a template + character reference.

Edit the four constants below, then:  uv run gen_settei.py
"""
import os
import sys
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image

# ---- edit these ------------------------------------------------------------
TEMPLATE_PATH = "/path/to/template_settei.webp"
CHARACTER_PATH = "/path/to/character_reference.png"
OUT_PATH = "/path/to/output_settei.png"

# 2-4 short sentences describing the character identity.
IDENTITY = (
    "young girl with short wavy silver-white bob hair, soft side-swept bangs, "
    "a pink ribbon bow clipped on the right side of her head, large soft "
    "lavender-pink eyes, light pink blush, gentle warm smile."
)

# One sentence outfit, locked across all full-body views.
OUTFIT = (
    "a knee-length short-sleeve pure white sailor-collar dress with light "
    "blue trim on the collar, plain fabric (no print), a soft white waist "
    "sash, and simple white shoes."
)

# Optional: name a key outfit detail to put in the lower-right callout row.
OUTFIT_DETAIL_CALLOUT = "dress collar"

# ---- env -------------------------------------------------------------------
ENV_CANDIDATES = [
    os.environ.get("SKILL_ENV_FILE"),
    os.path.join(os.getcwd(), ".env"),
    os.path.join(os.getcwd(), ".env.local"),
    "/Users/innei/git/innei-repo/SKILL/.env",
]
for p in ENV_CANDIDATES:
    if p and os.path.exists(p):
        load_dotenv(p)
        break

api_key = os.environ.get("GOOGLE_AI_STUDIO_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    sys.exit("missing GOOGLE_AI_STUDIO_API_KEY / GEMINI_API_KEY in env")

# ---- prompt ----------------------------------------------------------------
PROMPT = (
    "Create a horizontal anime character settei sheet matching the EXACT "
    "layout, composition, line weight, soft watercolor shading, and pure "
    "white background of the FIRST reference image:\n"
    "- left: three full-body standing views (front, side, back)\n"
    "- upper right: row of small head-and-shoulder expression variations "
    "(gentle smile, blush, surprised, sleepy, pout, happy)\n"
    f"- lower right: close-up detail callouts (eye, {OUTFIT_DETAIL_CALLOUT}) "
    "and small color-palette swatch dots\n"
    "- thin pencil-style annotation lines and tiny handwritten-style note "
    "marks (decorative, no need to read)\n\n"
    "The character must be the girl from the SECOND reference image: "
    f"{IDENTITY}\n"
    f"She wears {OUTFIT} "
    "Keep the same outfit consistent across all three full-body views.\n\n"
    "Art style: soft anime cel-shading with light watercolor highlights, "
    "clean thin linework, bright airy palette, white paper background — "
    "match the first reference's aesthetic exactly."
)

# ---- call ------------------------------------------------------------------
client = genai.Client(api_key=api_key)
template = Image.open(TEMPLATE_PATH)
character = Image.open(CHARACTER_PATH)

cfg = types.GenerateContentConfig(
    response_modalities=["TEXT", "IMAGE"],
    image_config=types.ImageConfig(aspect_ratio="16:9", image_size="2K"),
)

for attempt in range(6):
    try:
        resp = client.models.generate_content(
            model="gemini-3.1-flash-image-preview",
            contents=[PROMPT, template, character],
            config=cfg,
        )
    except Exception as e:
        msg = str(e)
        if any(s in msg for s in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED")) and attempt < 5:
            time.sleep(2 ** attempt * 5)
            continue
        raise

    saved = False
    for part in resp.parts or []:
        if img := part.as_image():
            img.save(OUT_PATH)
            print(f"saved -> {OUT_PATH}")
            saved = True
            break
    if saved:
        break

    cands = getattr(resp, "candidates", None) or []
    finish = [getattr(c, "finish_reason", None) for c in cands]
    txt = (getattr(resp, "text", None) or "")[:160]
    print(f"no image (attempt {attempt + 1}); finish={finish} text={txt}")
    time.sleep(3)
else:
    sys.exit("failed to generate after retries")

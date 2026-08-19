#!/usr/bin/env python3
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

HERE = Path(__file__).resolve().parent
COMPOSE = HERE / "compose.html"


def run(cmd: list[str]) -> None:
    subprocess.check_call(cmd)


def measure(bezel: Path) -> dict:
    raw = subprocess.check_output(
        [sys.executable, str(HERE / "measure-bezel.py"), str(bezel)],
        text=True,
    )
    return json.loads(raw)


def render(deck_path: Path) -> None:
    deck = json.loads(deck_path.read_text())
    bezel = Path(deck["bezel"]).resolve()
    hole = measure(bezel)
    out_dir = Path(deck["outDir"]).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    session = deck.get("session", "app-store-listing")
    if not shutil.which("agent-browser"):
        raise SystemExit("agent-browser is required to paint slide headlines")
    compose = COMPOSE.resolve().as_uri()
    run(
        [
            "agent-browser",
            "--session",
            session,
            "--allow-file-access",
            "open",
            compose,
        ]
    )
    run(["agent-browser", "--session", session, "set", "viewport", "1290", "2796", "1"])
    try:
        for slide in deck["slides"]:
            dest = out_dir / f"{slide['id']}.png"
            dest.parent.mkdir(parents=True, exist_ok=True)
            q = {
                "kicker": slide.get("kicker", deck.get("kicker", "")),
                "title": slide["title"],
                "sub": slide.get("sub", ""),
                "latin": "1" if slide.get("latin") or deck.get("latin") else "0",
                "img": Path(slide["capture"]).resolve().as_uri(),
                "bezel": bezel.as_uri(),
                "hx": hole["x"],
                "hy": hole["y"],
                "hw": hole["w"],
                "hh": hole["h"],
                "bw": hole["bezelW"],
                "bh": hole["bezelH"],
            }
            for key in ("bg", "bg-top", "fg", "accent"):
                if deck.get(key):
                    q[key] = deck[key]
            run(
                [
                    "agent-browser",
                    "--session",
                    session,
                    "open",
                    f"{compose}?{urlencode(q)}",
                ]
            )
            time.sleep(0.4)
            run(
                [
                    "agent-browser",
                    "--session",
                    session,
                    "set",
                    "viewport",
                    "1290",
                    "2796",
                    "1",
                ]
            )
            run(
                [
                    "agent-browser",
                    "--session",
                    session,
                    "screenshot",
                    "--screenshot-dir",
                    str(dest.parent),
                    dest.name,
                ]
            )
            print(dest)
    finally:
        run(["agent-browser", "--session", session, "close"])


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: render-slides.py <deck.json>")
    render(Path(sys.argv[1]))


if __name__ == "__main__":
    main()

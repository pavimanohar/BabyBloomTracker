"""
generate_assets.py — creates icon.png (512x512) and presplash.png (1080x1920)
for BabyBloom using plain PIL drawing (no network / no external model needed).

Motif: a crescent moon cradling a baby footprint + a small heart, on a
soft pastel gradient — reads as "pregnancy / baby / care" at a glance,
even at launcher-icon size.

Run:  python3 assets/generate_assets.py

WANT REAL AI-GENERATED ART INSTEAD?
Generate a 512x512 PNG with your tool of choice (Midjourney, DALL-E,
Stable Diffusion, etc.) using a prompt like:
    "cute minimal flat icon, pregnant mother silhouette with a heart,
     pastel pink and lavender, baby shower style, app icon, no text"
and save it as assets/icon.png (and a 1080x1920 version as
assets/presplash.png) — buildozer.spec already points at these exact
paths, so no other change is needed.
"""

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from theme import PALETTE  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def vertical_gradient(size, top_hex, bottom_hex):
    w, h = size
    top, bottom = hex_rgb(top_hex), hex_rgb(bottom_hex)
    img = Image.new("RGB", (1, h))
    for y in range(h):
        img.putpixel((0, y), lerp_color(top, bottom, y / max(h - 1, 1)))
    return img.resize((w, h))


def draw_moon_and_footprint(draw, cx, cy, scale, moon_color, print_color, heart_color):
    r = 0.34 * scale
    # Crescent moon: big circle minus offset smaller circle
    moon_bbox = [cx - r, cy - r, cx + r, cy + r]
    draw.ellipse(moon_bbox, fill=moon_color)
    cut_offset = 0.30 * scale
    cut_bbox = [cx - r + cut_offset, cy - r - 0.05 * scale,
                cx + r + cut_offset, cy + r - 0.05 * scale]
    draw.ellipse(cut_bbox, fill=(0, 0, 0, 0))

    # A single baby footprint sitting in the crescent's hollow
    fx, fy = cx - 0.02 * scale, cy + 0.02 * scale
    foot_w, foot_h = 0.12 * scale, 0.20 * scale
    draw.ellipse(
        [fx - foot_w / 2, fy - foot_h / 2, fx + foot_w / 2, fy + foot_h / 2],
        fill=print_color,
    )
    toe_r = 0.028 * scale
    for i, ang in enumerate([-40, -15, 10, 35, 58]):
        rad = math.radians(ang)
        tx = fx + math.sin(rad) * foot_w * 0.55
        ty = fy - foot_h * 0.62 - i * 0.006 * scale
        draw.ellipse([tx - toe_r, ty - toe_r, tx + toe_r, ty + toe_r], fill=print_color)

    # Tiny heart above-right, "expecting with love"
    hx, hy, hr = cx + 0.30 * scale, cy - 0.32 * scale, 0.045 * scale
    draw.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=heart_color)
    draw.ellipse([hx, hy - hr, hx + 2 * hr, hy + hr], fill=heart_color)
    draw.polygon(
        [(hx - hr, hy + hr * 0.4), (hx + 2 * hr, hy + hr * 0.4), (hx + hr * 0.5, hy + 2.1 * hr)],
        fill=heart_color,
    )


def make_icon(path, size=512):
    img = vertical_gradient((size, size), PALETTE["accent"], PALETTE["primary"]).convert("RGBA")

    # rounded-square mask so it looks right as an adaptive icon too
    mask = Image.new("L", (size, size), 0)
    mdraw = ImageDraw.Draw(mask)
    radius = int(size * 0.22)
    mdraw.rounded_rectangle([0, 0, size, size], radius=radius, fill=255)

    overlay = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    odraw = ImageDraw.Draw(overlay)
    draw_moon_and_footprint(
        odraw, size / 2, size / 2, size,
        moon_color=hex_rgb(PALETTE["cream"]) + (255,),
        print_color=hex_rgb(PALETTE["primary_dark"]) + (255,),
        heart_color=hex_rgb(PALETTE["danger"]) + (255,),
    )
    img = Image.alpha_composite(img, overlay)
    img.putalpha(mask)
    img.save(path)
    print(f"wrote {path} ({size}x{size})")


def make_presplash(path, size=(1080, 1920)):
    w, h = size
    img = vertical_gradient(size, PALETTE["cream"], PALETTE["secondary"]).convert("RGBA")
    overlay = Image.new("RGBA", size, (255, 255, 255, 0))
    odraw = ImageDraw.Draw(overlay)
    draw_moon_and_footprint(
        odraw, w / 2, h * 0.42, w * 0.62,
        moon_color=hex_rgb(PALETTE["primary"]) + (255,),
        print_color=hex_rgb("FFFFFF") + (255,),
        heart_color=hex_rgb(PALETTE["danger"]) + (255,),
    )
    img = Image.alpha_composite(img, overlay)

    # soft vignette so a launcher title bar (if any) sits comfortably
    blur = img.filter(ImageFilter.GaussianBlur(0))
    blur.convert("RGB").save(path)
    print(f"wrote {path} ({w}x{h})")


if __name__ == "__main__":
    make_icon(os.path.join(HERE, "icon.png"))
    make_presplash(os.path.join(HERE, "presplash.png"))

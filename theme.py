"""
theme.py — the "babies" visual theme in one place.

Change the palette here and it flows through every screen, plus the
generated icon/splash if you re-run assets/generate_assets.py.
"""

# Soft pastel palette: baby pink, baby blue, lavender, mint, cream.
PALETTE = {
    "primary": "F6A6C1",       # baby pink
    "primary_dark": "E88AAE",
    "secondary": "A9D6E5",     # baby blue
    "accent": "C9B6E4",        # lavender
    "mint": "B8E6D0",
    "cream": "FFF6EE",         # background
    "text": "5A4A55",          # soft plum-grey for readability
    "success": "8FCB9B",
    "warning": "F2C879",
    "danger": "E88A8A",
}


def hex_to_rgba(hex_color, alpha=1.0):
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16) / 255
    g = int(hex_color[2:4], 16) / 255
    b = int(hex_color[4:6], 16) / 255
    return [r, g, b, alpha]


PRIMARY_RGBA = hex_to_rgba(PALETTE["primary"])
PRIMARY_DARK_RGBA = hex_to_rgba(PALETTE["primary_dark"])
SECONDARY_RGBA = hex_to_rgba(PALETTE["secondary"])
ACCENT_RGBA = hex_to_rgba(PALETTE["accent"])
MINT_RGBA = hex_to_rgba(PALETTE["mint"])
CREAM_RGBA = hex_to_rgba(PALETTE["cream"])
TEXT_RGBA = hex_to_rgba(PALETTE["text"])
SUCCESS_RGBA = hex_to_rgba(PALETTE["success"])
WARNING_RGBA = hex_to_rgba(PALETTE["warning"])
DANGER_RGBA = hex_to_rgba(PALETTE["danger"])

APP_TITLE = "BabyBloom — Pregnancy Care Tracker"

# tools/generate_weather_icons.py
# Run this ONCE from the project root to generate weather icon PNGs.
# Requires Pillow (already in requirements.txt).
#
# Usage:
#   cd "A:\Personal coding\Solar Desktop App"
#   python tools/generate_weather_icons.py

import os
from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "icons", "weather")
FINAL_SIZE = 64

ICONS = {
    "clear":           "\u2600\ufe0f",
    "mainly_clear":    "\U0001f324\ufe0f",
    "partly_cloudy":   "\u26c5",
    "overcast":        "\u2601\ufe0f",
    "foggy":           "\U0001f32b\ufe0f",
    "drizzle":         "\U0001f326\ufe0f",
    "rain":            "\U0001f327\ufe0f",
    "snow":            "\u2744\ufe0f",
    "heavy_snow":      "\U0001f328\ufe0f",
    "showers":         "\U0001f326\ufe0f",
    "heavy_showers":   "\U0001f327\ufe0f",
    "storm_showers":   "\U0001f327\ufe0f",
    "thunderstorm":    "\u26c8\ufe0f",
    "unknown":         "\U0001f321\ufe0f",
}

FONT_PATHS = [
    r"C:\Windows\Fonts\seguiemj.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
]

def find_font():
    for path in FONT_PATHS:
        if os.path.exists(path):
            return path
    return None

def render_emoji(emoji, font):
    CANVAS = 256
    img  = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.text((CANVAS // 4, CANVAS // 4), emoji, font=font, embedded_color=True)
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    padded = Image.new("RGBA", (img.width + 8, img.height + 8), (0, 0, 0, 0))
    padded.paste(img, (4, 4))
    padded = padded.resize((FINAL_SIZE, FINAL_SIZE), Image.LANCZOS)
    return padded

def generate():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    font_path = find_font()
    if not font_path:
        print("ERROR: Could not find Segoe UI Emoji font.")
        return
    print(f"Using font: {font_path}")
    font = ImageFont.truetype(font_path, 109)
    for name, emoji in ICONS.items():
        img      = render_emoji(emoji, font)
        out_path = os.path.join(OUTPUT_DIR, f"{name}.png")
        img.save(out_path)
        print(f"  checked {name}.png")
    print(f"\nDone - {len(ICONS)} icons saved to: {OUTPUT_DIR}")

if __name__ == "__main__":
    generate()
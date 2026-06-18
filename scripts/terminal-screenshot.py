#!/usr/bin/env python3
"""✦ Generate terminal screenshot PNGs from ANSI text input.

Usage:
    python scripts/terminal-screenshot.py -c "polaris --logo" -o docs/screenshots/logo.png
    python scripts/terminal-screenshot.py < input.txt -o output.png
"""

import argparse
import os
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ── Terminal appearance ────────────────────────────────────────────────────

BG_COLOR = (15, 23, 42)       # slate-900
FG_COLOR = (248, 250, 252)    # slate-50
FONT_FAMILY = "monospace"
FONT_SIZE = 14
PADDING_X = 24
PADDING_Y = 20
LINE_HEIGHT = 20
CORNER_RADIUS = 8
TITLE_BAR_HEIGHT = 32
DOT_COLORS = [(255, 95, 86), (255, 189, 46), (39, 201, 63)]  # red, yellow, green

# ANSI color table
ANSI_COLORS = {
    "30": (0, 0, 0),       "31": (239, 68, 68),    "32": (34, 197, 94),
    "33": (234, 179, 8),   "34": (59, 130, 246),   "35": (168, 85, 247),
    "36": (6, 182, 212),   "37": (255, 255, 255),
    "90": (100, 116, 139), "91": (252, 165, 165),  "92": (134, 239, 172),
    "93": (253, 224, 71),  "94": (96, 165, 250),   "95": (192, 132, 252),
    "96": (103, 232, 249), "97": (248, 250, 252),
}

# Bold variants (brighter)
ANSI_BOLD = {
    "31": (252, 165, 165), "32": (134, 239, 172), "33": (253, 224, 71),
    "34": (147, 197, 253), "35": (216, 180, 254), "36": (165, 243, 252),
    "37": (255, 255, 255),
}


def find_font() -> str:
    """Find a monospace font on the system."""
    candidates = [
        "/usr/share/fonts/TTF/JetBrainsMono-Regular.ttf",
        "/usr/share/fonts/TTF/FiraCode-Regular.ttf",
        "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
        "/usr/share/fonts/noto/NotoMono-Regular.ttf",
        "/usr/share/fonts/TTF/CascadiaCode.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    # Search
    for root, dirs, files in os.walk("/usr/share/fonts"):
        for f in files:
            if "mono" in f.lower() and f.endswith((".ttf", ".otf")):
                return os.path.join(root, f)
    return None


def parse_ansi(text: str) -> list[list[tuple[str, tuple, bool]]]:
    """Parse ANSI-escaped text into a list of styled lines.

    Returns: list of lines, each line is a list of (char, color, bold)
    """
    lines = text.split("\n")
    result = []

    ansi_re = re.compile(r"\033\[([0-9;]*)m")

    for line in lines:
        chars = []
        # Remove CSI sequences like ESC[2J ESC[H ESC[3J
        clean = re.sub(r"\033\[[0-9;]*[HJ]", "", line)
        parts = ansi_re.split(clean)

        current_color = FG_COLOR
        current_bold = False

        for i, part in enumerate(parts):
            if i % 2 == 0:
                # Text content
                for ch in part:
                    chars.append((ch, current_color, current_bold))
            else:
                # ANSI codes
                codes = part.split(";") if part else ["0"]
                for code in codes:
                    if code == "0":
                        current_color = FG_COLOR
                        current_bold = False
                    elif code == "1":
                        current_bold = True
                    elif code == "2":
                        current_color = ANSI_COLORS.get("90", FG_COLOR)
                    elif code == "4":
                        pass  # underline, ignore
                    elif code in ANSI_COLORS:
                        current_color = ANSI_BOLD.get(code, ANSI_COLORS[code]) if current_bold else ANSI_COLORS[code]

        if chars:
            result.append(chars)
        else:
            result.append([(" ", FG_COLOR, False)])

    return result


def render_terminal(lines: list[list[tuple]], title: str = "") -> Image.Image:
    """Render parsed ANSI lines into a terminal screenshot PIL Image."""
    font_path = find_font()
    if font_path:
        try:
            font = ImageFont.truetype(font_path, FONT_SIZE)
        except Exception:
            font = ImageFont.load_default()
    else:
        font = ImageFont.load_default()

    # Calculate dimensions
    max_line_chars = max((len(line) for line in lines), default=80)
    content_width = max_line_chars * FONT_SIZE * 0.6 + PADDING_X * 2  # approximate
    content_height = len(lines) * LINE_HEIGHT + PADDING_Y * 2

    total_width = int(content_width)
    total_height = int(content_height + TITLE_BAR_HEIGHT)

    # Create image
    img = Image.new("RGBA", (total_width, total_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded rect background
    _rounded_rect(draw, 0, 0, total_width, total_height, BG_COLOR, CORNER_RADIUS)

    # Title bar
    draw.rectangle([0, 0, total_width, TITLE_BAR_HEIGHT], fill=(30, 41, 59))
    _rounded_rect_top(draw, 0, 0, total_width, TITLE_BAR_HEIGHT, (30, 41, 59), CORNER_RADIUS)

    # Dots
    dot_y = TITLE_BAR_HEIGHT // 2
    for i, color in enumerate(DOT_COLORS):
        x = PADDING_X + i * 20
        draw.ellipse([x - 5, dot_y - 5, x + 5, dot_y + 5], fill=color)

    # Title text
    if title:
        try:
            title_font = ImageFont.truetype(font_path, 12) if font_path else font
        except Exception:
            title_font = font
        bbox = draw.textbbox((0, 0), title, font=title_font)
        title_w = bbox[2] - bbox[0]
        draw.text(((total_width - title_w) // 2, (TITLE_BAR_HEIGHT - 14) // 2),
                  title, fill=(148, 163, 184), font=title_font)

    # Render text
    y = TITLE_BAR_HEIGHT + PADDING_Y
    for line in lines:
        x = PADDING_X
        for ch, color, bold in line:
            try:
                ch_font = ImageFont.truetype(font_path, FONT_SIZE + (1 if bold else 0)) if font_path else font
            except Exception:
                ch_font = font
            if ch != " ":
                draw.text((x, y), ch, fill=color, font=ch_font)
            x += FONT_SIZE * 0.6  # monospace approximation
        y += LINE_HEIGHT

    return img


def _rounded_rect(draw, x1, y1, x2, y2, fill, r):
    """Draw a rounded rectangle."""
    draw.rectangle([x1 + r, y1, x2 - r, y2], fill=fill)
    draw.rectangle([x1, y1 + r, x2, y2 - r], fill=fill)
    draw.pieslice([x1, y1, x1 + 2*r, y1 + 2*r], 180, 270, fill=fill)
    draw.pieslice([x2 - 2*r, y1, x2, y1 + 2*r], 270, 360, fill=fill)
    draw.pieslice([x1, y2 - 2*r, x1 + 2*r, y2], 90, 180, fill=fill)
    draw.pieslice([x2 - 2*r, y2 - 2*r, x2, y2], 0, 90, fill=fill)


def _rounded_rect_top(draw, x1, y1, x2, y2, fill, r):
    """Rounded corners only on top."""
    draw.pieslice([x1, y1, x1 + 2*r, y1 + 2*r], 180, 270, fill=fill)
    draw.pieslice([x2 - 2*r, y1, x2, y1 + 2*r], 270, 360, fill=fill)


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="✦ Generate terminal screenshot PNGs")
    parser.add_argument("-c", "--command", help="Run this command and screenshot its output")
    parser.add_argument("-o", "--output", default="screenshot.png", help="Output PNG path")
    parser.add_argument("-t", "--title", default="", help="Terminal title bar text")
    parser.add_argument("--height", type=int, default=600, help="Max image height (crop)")
    args = parser.parse_args()

    if args.command:
        import subprocess
        env = os.environ.copy()
        env["FORCE_COLOR"] = "1"
        env["COLUMNS"] = "80"
        r = subprocess.run(args.command, shell=True, capture_output=True, text=True, env=env, timeout=10)
        text = r.stdout or r.stderr
    else:
        text = sys.stdin.read()

    if not text.strip():
        print("No output captured.", file=sys.stderr)
        sys.exit(1)

    lines = parse_ansi(text)
    img = render_terminal(lines, title=args.title or args.command or "")

    # Ensure output directory exists
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    img.save(args.output, "PNG")
    print(f"✓ Screenshot saved: {args.output} ({img.width}x{img.height})")


if __name__ == "__main__":
    main()

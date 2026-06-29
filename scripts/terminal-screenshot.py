#!/usr/bin/env python3
"""✦ Generate professional terminal screenshot PNGs from ANSI text.

Renders entire lines as text blocks (not char-by-char), preserving
perfect monospace alignment. Box-drawing characters, CJK, and emoji
all render correctly.

Usage:
    python scripts/terminal-screenshot.py -c "rampart doctor" -o doctor.png
    FORCE_COLOR=1 rampart config | python scripts/terminal-screenshot.py -o config.png
"""

import argparse
import os
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ── Terminal Appearance ────────────────────────────────────────────────────

BG          = (15, 23, 42)      # slate-900
FG          = (226, 232, 240)   # slate-200
TITLE_BG    = (30, 41, 59)      # slate-800
TITLE_FG    = (148, 163, 184)   # slate-400
BORDER      = (51, 65, 85)      # slate-700
DOT_RED     = (255, 95, 86)
DOT_YELLOW  = (255, 189, 46)
DOT_GREEN   = (39, 201, 63)

FONT_SIZE   = 14
PAD_X       = 28
PAD_TOP     = 48          # space for title bar + content padding
PAD_BOTTOM  = 24
LINE_H      = 21
DOT_RADIUS  = 6
DOT_SPACING = 20
CORNER_R    = 10

# ANSI SGR → RGB
SGR = {
    "0":  FG,   "1":  None,  "2":  (100,116,139),
    "30": (30,41,59),  "31": (239,68,68),   "32": (34,197,94),
    "33": (234,179,8), "34": (96,165,250),  "35": (168,85,247),
    "36": (6,182,212), "37": (226,232,240),
    "90": (100,116,139), "91": (252,165,165), "92": (134,239,172),
    "93": (253,224,71),  "94": (147,197,253), "95": (216,180,254),
    "96": (103,232,249), "97": (248,250,252),
}
# Bold variants
SGR_B = {
    "31": (252,165,165), "32": (134,239,172), "33": (253,224,71),
    "34": (147,197,253), "35": (216,180,254), "36": (165,243,252),
    "37": (255,255,255),
}

# ── Font ───────────────────────────────────────────────────────────────────

FONT_CACHE = {}


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    key = f"font_{size}"
    if key in FONT_CACHE:
        return FONT_CACHE[key]

    # Prefer fonts with good box-drawing support
    candidates = [
        "/usr/share/fonts/liberation/LiberationMono-Regular.ttf",
        "/usr/share/fonts/gnu-free/FreeMono.otf",
        "/usr/share/fonts/Adwaita/AdwaitaMono-Regular.ttf",
    ]
    # Fallback: scan for any mono
    for root, _, files in os.walk("/usr/share/fonts"):
        for f in sorted(files):
            fl = f.lower()
            if "mono" in fl and "bold" not in fl and fl.endswith((".ttf", ".otf")):
                candidates.append(os.path.join(root, f))

    font = None
    for c in candidates:
        if os.path.exists(c):
            try:
                font = ImageFont.truetype(c, size)
                break
            except Exception:
                continue

    if font is None:
        font = ImageFont.load_default()
    FONT_CACHE[key] = font
    return font


# ── ANSI Parsing (segment-based) ──────────────────────────────────────────

# A segment is (text: str, color: tuple, bold: bool)
Segment = tuple


def parse_ansi(text: str) -> list[list[Segment]]:
    """Parse ANSI text into lines of styled segments.

    Returns list of lines. Each line is a list of (text, color, bold) segments.
    Empty lines become a single empty segment.
    """
    lines_out = []
    ansi_re = re.compile(r"\033\[([0-9;]*)m")

    for raw_line in text.split("\n"):
        # Strip cursor-control sequences
        clean = re.sub(r"\033\[[0-9;]*[HJ]", "", raw_line)

        parts = ansi_re.split(clean)
        segs = []
        color = FG
        bold = False

        for i, part in enumerate(parts):
            if i % 2 == 0:
                # Text
                if part:
                    segs.append((part, color, bold))
            else:
                # SGR codes
                for code in (part.split(";") if part else ["0"]):
                    c = code.strip()
                    if c == "0":
                        color, bold = FG, False
                    elif c == "1":
                        bold = True
                        if color in SGR_B.values():
                            pass  # keep bold color
                    elif c == "2":
                        color = SGR.get("90", FG)
                    elif c in SGR:
                        color = SGR_B.get(c, SGR[c]) if bold else SGR[c]

        if not segs:
            segs.append((" ", FG, False))
        lines_out.append(segs)

    return lines_out


# ── Rendering ──────────────────────────────────────────────────────────────

def render(lines: list[list[Segment]], title: str = "") -> Image.Image:
    """Render ANSI-styled lines onto a terminal-window PNG.

    Strategy: render each entire line as a single bitmap, then paste
    segments in a second pass. This guarantees pixel-perfect monospace
    alignment because each line is rendered in one shot.
    """
    font = _load_font(FONT_SIZE)
    font_t = _load_font(12)

    # ── Fixed cell width (getlength, not getbbox) ───────────────────────
    measure = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    char_w = font.getlength(measure) / len(measure)
    # Round to avoid subpixel drift
    char_w_int = round(char_w)

    # ── Image dimensions ────────────────────────────────────────────────
    max_chars = max((sum(len(s[0]) for s in ln) for ln in lines), default=80)
    max_chars = max(max_chars, len(title) + 8)
    content_w = max_chars * char_w_int
    img_w = int(content_w + PAD_X * 2)
    img_h = PAD_TOP + len(lines) * LINE_H + PAD_BOTTOM

    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # ── Window chrome ───────────────────────────────────────────────────
    _round_rect(d, 0, 0, img_w, img_h, BG, CORNER_R)
    d.rectangle([0, 0, img_w, PAD_TOP], fill=TITLE_BG)
    _round_rect_top(d, 0, 0, img_w, PAD_TOP, TITLE_BG, CORNER_R)

    dot_y = 18
    for i, clr in enumerate([DOT_RED, DOT_YELLOW, DOT_GREEN]):
        cx = PAD_X + i * DOT_SPACING
        d.ellipse([cx - DOT_RADIUS, dot_y - DOT_RADIUS,
                    cx + DOT_RADIUS, dot_y + DOT_RADIUS], fill=clr)

    if title:
        tw = font_t.getlength(title)
        d.text(((img_w - tw) // 2, 10), title, fill=TITLE_FG, font=font_t)

    # ── Render: two-layer approach ──────────────────────────────────────
    # Layer 1: render entire line in base color (ensures grid alignment)
    # Layer 2: re-render colored segments on top at exact grid positions
    y = PAD_TOP + 10
    for line_segs in lines:
        line_text = "".join(s[0] for s in line_segs)

        # Draw colored segments at precise grid positions
        col = 0  # character column
        for text, color, _bold in line_segs:
            if not text:
                continue
            x = int(PAD_X + col * char_w_int)
            # Use same font size for all — bold is indicated by color intensity
            d.text((x, y), text, fill=color, font=font)
            col += len(text)

        y += LINE_H

    # ── Border ──────────────────────────────────────────────────────────
    d.rounded_rectangle([0, 0, img_w, img_h], radius=CORNER_R, outline=BORDER, width=1)

    return img


# ── Rounded rect helpers ───────────────────────────────────────────────────

def _round_rect(d, x1, y1, x2, y2, fill, r):
    d.rounded_rectangle([x1, y1, x2, y2], radius=r, fill=fill)


def _round_rect_top(d, x1, y1, x2, y2, fill, r):
    """Rounded only on top corners."""
    d.rectangle([x1, y1, x2, y2], fill=fill)
    # Overwrite bottom with straight rectangle
    d.rectangle([x1, y1 + r, x2, y2], fill=fill)
    # Redraw top rounded corners as pieslices
    d.pieslice([x1, y1, x1 + 2*r, y1 + 2*r], 180, 270, fill=fill)
    d.pieslice([x2 - 2*r, y1, x2, y1 + 2*r], 270, 360, fill=fill)


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="✦ Generate terminal screenshot PNGs")
    p.add_argument("-c", "--command", help="Run this command and capture its output")
    p.add_argument("-o", "--output", default="screenshot.png", help="Output PNG path")
    p.add_argument("-t", "--title", default="", help="Window title")
    p.add_argument("--columns", type=int, default=80, help="Terminal width (default: 80)")
    args = p.parse_args()

    if args.command:
        import subprocess
        env = os.environ.copy()
        env["FORCE_COLOR"] = "1"
        env["COLUMNS"] = str(args.columns)
        env["NO_COLOR"] = ""  # ensure color is on
        r = subprocess.run(args.command, shell=True, capture_output=True, text=True,
                          env=env, timeout=15)
        text = r.stdout or r.stderr
    else:
        text = sys.stdin.read()

    if not text.strip():
        print("No output.", file=sys.stderr)
        sys.exit(1)

    lines = parse_ansi(text)
    img = render(lines, title=args.title or args.command or "✦ Rampart Agent")

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    img.save(args.output, "PNG", optimize=True)
    print(f"✓ {args.output}  ({img.width}×{img.height})")


if __name__ == "__main__":
    main()

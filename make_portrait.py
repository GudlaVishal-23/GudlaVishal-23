#!/usr/bin/env python3
"""
make_portrait.py - turn a photo into a terminal-style ASCII portrait SVG
for a GitHub profile README.

Usage:
    pip install pillow numpy
    python make_portrait.py passphoto.jpeg avi-ascii.svg
"""
import sys
import numpy as np
from PIL import Image, ImageOps, ImageFilter

# ---- settings you can tweak -------------------------------------------------
COLS        = 180          # characters per row (more = more detail)
CARD_W      = 370          # SVG size: keep W/H matching your info card
CARD_H      = 385
HEADER_H    = 30           # terminal title bar
FOOTER_H    = 28           # whoami line
RAMP        = " .'`^,:;-~=+*cxoO#%&@"   # light -> dense
CROP_TOP    = 0.06         # fraction of image height cropped off the top
CROP_SIDE   = 0.07         # fraction cropped from each side (zoom on face)
BG_THRESH   = 26           # how different from the backdrop = "subject"
FG          = "#c9d1d9"    # ASCII colour
TITLE       = "vishal@github: ~$ ./portrait.sh"
PROMPT      = "vishal@github:~$ whoami"
NAME        = "Vishal Gudla"
# -----------------------------------------------------------------------------

def build(src, dst):
    img = Image.open(src).convert("RGB")
    W, H = img.size

    # Area available for ASCII, and the grid that fits it
    area_w = CARD_W - 16
    area_h = CARD_H - HEADER_H - FOOTER_H - 6
    cw = area_w / COLS                      # char cell width
    font = cw / 0.6                         # monospace glyph ~0.6em wide
    rh = font * 1.18                        # row height
    rows = int(area_h // rh)

    # Crop the photo to the same aspect as the character grid
    aspect = (COLS * cw) / (rows * rh)
    x1, x2 = int(W * CROP_SIDE), int(W * (1 - CROP_SIDE))
    ch = int((x2 - x1) / aspect)
    top = int(H * CROP_TOP)
    img = img.crop((x1, top, x2, min(H, top + ch)))
    small = img.resize((COLS, rows), Image.LANCZOS)
    # sharpen at higher resolution so eyes / brows / lips survive downsampling
    big = img.resize((COLS * 4, rows * 4), Image.LANCZOS).convert("L")
    big = ImageOps.autocontrast(big, cutoff=1)
    big = big.filter(ImageFilter.UnsharpMask(radius=6, percent=260, threshold=2))
    tone = big.resize((COLS, rows), Image.BOX)

    # Subject mask: anything unlike the plain backdrop
    arr = np.asarray(small).astype(float)
    bg = np.median(np.concatenate([arr[:3].reshape(-1, 3),
                                   arr[:, :3].reshape(-1, 3),
                                   arr[:, -3:].reshape(-1, 3)]), axis=0)
    dist = np.sqrt(((arr - bg) ** 2).sum(axis=2))
    mask = Image.fromarray(((dist > BG_THRESH) * 255).astype("uint8"))
    mask = mask.filter(ImageFilter.MedianFilter(3))
    mask = np.asarray(mask) > 127

    # Fill holes: light areas inside the face (eye whites, highlights) are close
    # to the backdrop colour and get wrongly cut out. Anything not connected to
    # the image border is part of the subject, so keep it.
    outside = np.zeros_like(mask)
    stack = [(y, x) for y in range(rows) for x in (0, COLS - 1) if not mask[y, x]]
    stack += [(y, x) for x in range(COLS) for y in (0, rows - 1) if not mask[y, x]]
    while stack:
        y, x = stack.pop()
        if y < 0 or x < 0 or y >= rows or x >= COLS or outside[y, x] or mask[y, x]:
            continue
        outside[y, x] = True
        stack += [(y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)]
    mask = ~outside

    # Tone: stretch contrast, brighten mid-tones so skin reads as skin
    g = np.asarray(ImageOps.autocontrast(tone, cutoff=1)).astype(float) / 255.0
    g = g ** 0.75
    n = len(RAMP) - 1

    lines = []
    for y in range(rows):
        row = []
        for x in range(COLS):
            if not mask[y, x]:
                row.append(" ")
            else:
                row.append(RAMP[max(1, int(g[y, x] * n))])
        lines.append("".join(row).rstrip())

    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    mono = "ui-monospace,SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono','Liberation Mono','Courier New',monospace"
    x0 = 8
    y0 = HEADER_H + 4 + font
    text = []
    for i, ln in enumerate(lines):
        idx = [j for j, c in enumerate(ln) if c != " "]
        if not idx:
            continue
        xs = " ".join(f"{x0 + j * cw:.2f}" for j in idx)
        chars = esc("".join(ln[j] for j in idx))
        # one explicit x per glyph -> identical layout in every font/renderer
        text.append(f'<text x="{xs}" y="{y0 + i * rh:.2f}">{chars}</text>')

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_W}" height="{CARD_H}" viewBox="0 0 {CARD_W} {CARD_H}" fill="none">
  <defs><clipPath id="card"><rect x="0.5" y="0.5" width="{CARD_W-1}" height="{CARD_H-1}" rx="10"/></clipPath></defs>
  <g clip-path="url(#card)">
    <rect width="{CARD_W}" height="{CARD_H}" fill="#0d1117"/>
    <circle cx="14" cy="15" r="4" fill="#ff5f56"/>
    <circle cx="28" cy="15" r="4" fill="#ffbd2e"/>
    <circle cx="42" cy="15" r="4" fill="#27c93f"/>
    <text x="{CARD_W/2+25}" y="19" text-anchor="middle" font-family="{mono}" font-size="10" fill="#8b949e">{esc(TITLE)}</text>
    <line x1="0" y1="{HEADER_H}" x2="{CARD_W}" y2="{HEADER_H}" stroke="#21262d"/>
    <g font-family="{mono}" font-size="{font:.2f}" fill="{FG}">
{chr(10).join(text)}
    </g>
    <line x1="0" y1="{CARD_H-FOOTER_H}" x2="{CARD_W}" y2="{CARD_H-FOOTER_H}" stroke="#21262d"/>
    <text x="12" y="{CARD_H-10}" font-family="{mono}" font-size="10" fill="#8b949e">{esc(PROMPT)} <tspan fill="#e6edf3" font-weight="bold">{esc(NAME)}</tspan></text>
  </g>
  <rect x="0.5" y="0.5" width="{CARD_W-1}" height="{CARD_H-1}" rx="10" stroke="#30363d"/>
</svg>'''
    open(dst, "w", encoding="utf-8").write(svg)
    print(f"wrote {dst}  ({COLS}x{rows} chars, {len(svg)/1024:.1f} KB)")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python make_portrait.py <photo> <output.svg>")
    build(sys.argv[1], sys.argv[2])


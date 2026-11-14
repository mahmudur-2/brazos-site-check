#!/usr/bin/env python3
"""One contact sheet per device folder of a downloaded run: python tools/sheet.py <download dir>
writes <download dir>/sheet-<device>.png (each screenshot with its file name)."""
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

WIDTH, COLS, GAP, LABEL = 280, 8, 12, 22

root = pathlib.Path(sys.argv[1])
font = ImageFont.load_default(size=13)
for folder in sorted(p for p in root.iterdir() if p.is_dir()):
    shots = sorted(folder.glob("*.png"))
    if not shots:
        continue
    thumbs = []
    for path in shots:
        with Image.open(path) as im:
            im = im.convert("RGB")
            thumbs.append((path.stem, im.resize((WIDTH, round(WIDTH * im.height / im.width)), Image.LANCZOS)))
    cell_h = max(t.height for _, t in thumbs) + LABEL
    rows = -(-len(thumbs) // COLS)
    sheet = Image.new("RGB", (GAP + COLS * (WIDTH + GAP), GAP + rows * (cell_h + GAP)), (48, 48, 48))
    draw = ImageDraw.Draw(sheet)
    for i, (name, thumb) in enumerate(thumbs):
        x = GAP + (i % COLS) * (WIDTH + GAP)
        y = GAP + (i // COLS) * (cell_h + GAP)
        draw.text((x, y + 3), name, fill=(235, 235, 235), font=font)
        sheet.paste(thumb, (x, y + LABEL))
    out = root / f"sheet-{folder.name}.png"
    sheet.save(out)
    print(out, len(thumbs))

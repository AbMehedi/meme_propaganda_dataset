"""
Visual verification for OCR_WORD results.

Draws the LINE box (red) and each WORD box (green, with the word text)
back onto a sample of images, so you can eyeball whether:
  - line detection is finding real text regions (not merging/missing text)
  - the word-split (green boxes) roughly lines up with each actual word

Saves annotated copies to ./ocr_check/ -- open a handful and look.
"""

import os
import sqlite3

from PIL import Image, ImageDraw, ImageFont

DB_PATH = "propaganda_dataset.db"
OUT_DIR = "ocr_check"
SAMPLE_SIZE = 15  # how many images to spot-check

os.makedirs(OUT_DIR, exist_ok=True)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
    SELECT DISTINCT i.image_id, i.file_path
    FROM IMAGE i JOIN OCR_WORD o ON i.image_id = o.image_id
    ORDER BY RANDOM() LIMIT ?
""", (SAMPLE_SIZE,))
samples = cur.fetchall()

try:
    font = ImageFont.truetype("DejaVuSans.ttf", 14)
except (OSError, RuntimeError):
    font = ImageFont.load_default()

for image_id, file_path in samples:
    if not os.path.exists(file_path):
        print(f"Missing file, skipping: {file_path}")
        continue

    img = Image.open(file_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    cur.execute("""
        SELECT DISTINCT line_id, line_x1, line_y1, line_x2, line_y2
        FROM OCR_WORD WHERE image_id = ?
    """, (image_id,))
    for line_id, lx1, ly1, lx2, ly2 in cur.fetchall():
        draw.rectangle([lx1, ly1, lx2, ly2], outline="red", width=2)

    cur.execute("""
        SELECT word, x1, y1, x2, y2, bbox_is_estimated
        FROM OCR_WORD WHERE image_id = ?
    """, (image_id,))
    for word, x1, y1, x2, y2, estimated in cur.fetchall():
        color = "orange" if estimated else "green"  # orange = split estimate, green = real detection
        draw.rectangle([x1, y1, x2, y2], outline=color, width=1)
        draw.text((x1, max(0, y1 - 14)), word, fill=color, font=font)

    out_path = os.path.join(OUT_DIR, f"{image_id}.png")
    img.save(out_path)
    print(f"Saved {out_path}")

conn.close()
print(f"\nDone. Check the '{OUT_DIR}' folder -- red = line box, green = confident word box, orange = estimated word split.")
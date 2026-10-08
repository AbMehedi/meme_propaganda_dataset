"""
OCR extraction for the propaganda dataset (Phase 2, Layer 3: OCR_WORD).

Key changes vs. the previous version:
  - Stores the real, detected LINE-level box (line_x1/y1/x2/y2) alongside
    each word, since EasyOCR only ever detects lines/phrases, not words.
  - Flags every word row with bbox_is_estimated=1, so downstream code
    (and future annotators) know the word box is a split estimate, not
    a direct detection.
  - Uses grapheme-cluster counts instead of raw len() to weight the
    proportional split, which is more accurate for Bangla (matras and
    conjuncts add extra Unicode codepoints per rendered character,
    so plain len() overstates width for some words).
  - Uses looser detection thresholds (width_ths/height_ths/slope_ths)
    to push EasyOCR toward finer, more word-sized regions where possible,
    reducing how often the estimate fallback is needed at all.

This script automatically backs up any existing OCR_WORD table (renaming
it to OCR_WORD_OLD_V1, or OLD_V2, V3... if that name is taken) before
creating a fresh one, since the old schema is incompatible (no line_id,
no line-level box, no estimated flag) and its word boxes were computed
with a less accurate width split. Nothing is deleted -- the old data is
just renamed out of the way. Drop it yourself once you've checked the
new run looks good:
    DROP TABLE OCR_WORD_OLD_V1;
"""

import os
import sqlite3

import easyocr
import regex  # pip install regex --break-system-packages  (supports \X grapheme clusters; stdlib `re` does not)
from dotenv import load_dotenv

load_dotenv()


def backup_old_table_if_exists(cur):
    """Rename any existing OCR_WORD table out of the way so it isn't
    lost or mixed with the new schema. Returns the backup name used,
    or None if there was no existing table."""
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='OCR_WORD'")
    if cur.fetchone() is None:
        return None

    n = 1
    while True:
        backup_name = f"OCR_WORD_OLD_V{n}"
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (backup_name,))
        if cur.fetchone() is None:
            break
        n += 1

    cur.execute(f"ALTER TABLE OCR_WORD RENAME TO {backup_name}")
    return backup_name

# ---------- CONFIG ----------
DB_PATH = "propaganda_dataset.db"
IMAGE_DIR = os.getenv("IMAGE_DIR", "raw_images_new")  # folder where download_and_hash.py saved images
LANGUAGES = ['bn', 'en']  # Bangla + English

# Detection tuning: lower thresholds = less merging of nearby text into
# one box, i.e. more (smaller) regions per image. Tune on a handful of
# sample images before running the full batch -- too low can over-split
# a single word into fragments.
DETECT_KWARGS = {"width_ths": 0.4, "height_ths": 0.4, "slope_ths": 0.1}
# -----------------------------

GRAPHEME_RE = regex.compile(r'\X')  # \X = one user-perceived character (grapheme cluster)


def grapheme_len(s: str) -> int:
    """Count rendered characters, not raw Unicode codepoints.
    Matters for Bangla: a conjunct or a base+matra sequence is one
    on-screen character but multiple codepoints under plain len()."""
    return len(GRAPHEME_RE.findall(s))


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    backup_name = backup_old_table_if_exists(cur)
    conn.commit()
    if backup_name:
        print(f"Existing OCR_WORD table found -- backed up as {backup_name}.")
    else:
        print("No existing OCR_WORD table found -- creating fresh.")

    cur.execute("""
    CREATE TABLE OCR_WORD (
        ocr_id INTEGER PRIMARY KEY AUTOINCREMENT,
        image_id TEXT,
        line_id INTEGER,
        word TEXT,
        confidence REAL,
        x1 INTEGER, y1 INTEGER, x2 INTEGER, y2 INTEGER,
        line_x1 INTEGER, line_y1 INTEGER, line_x2 INTEGER, line_y2 INTEGER,
        bbox_is_estimated INTEGER DEFAULT 1,
        FOREIGN KEY (image_id) REFERENCES IMAGE(image_id)
    );
    """)
    conn.commit()

    print(f"Reading images from: {IMAGE_DIR}/")
    reader = easyocr.Reader(LANGUAGES)

    cur.execute("""
        SELECT image_id, file_path FROM IMAGE
        WHERE image_id NOT IN (SELECT DISTINCT image_id FROM OCR_WORD)
    """)
    rows = cur.fetchall()
    print(f"Found {len(rows)} images needing OCR.")

    processed = 0
    failed = 0
    total_words = 0

    for image_id, file_path in rows:
        try:
            result = reader.readtext(file_path, **DETECT_KWARGS)
        except FileNotFoundError:
            print(f"File not found, skipping: {file_path}")
            failed += 1
            continue
        except (RuntimeError, ValueError, OSError) as e:
            print(f"OCR error on {image_id}: {e}")
            failed += 1
            continue

        word_count_this_image = 0

        for line_idx, (bbox, line_text, confidence) in enumerate(result):
            words = line_text.split()
            if not words:
                continue

            xs = [pt[0] for pt in bbox]
            ys = [pt[1] for pt in bbox]
            line_x1, line_x2 = min(xs), max(xs)
            line_y1, line_y2 = min(ys), max(ys)
            line_width = line_x2 - line_x1

            # Single-word line: no split needed, box IS the detection
            # (not an estimate) since there's nothing to divide.
            if len(words) == 1:
                cur.execute("""INSERT INTO OCR_WORD
                    (image_id, line_id, word, confidence, x1, y1, x2, y2,
                     line_x1, line_y1, line_x2, line_y2, bbox_is_estimated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
                    (image_id, line_idx, words[0], confidence,
                     int(line_x1), int(line_y1), int(line_x2), int(line_y2),
                     int(line_x1), int(line_y1), int(line_x2), int(line_y2)))
                word_count_this_image += 1
                continue

            # Multi-word line: split proportionally by grapheme count.
            char_counts = [grapheme_len(w) for w in words]
            total_chars = sum(char_counts)
            num_words = len(words)

            cursor_x = line_x1
            for word, char_count in zip(words, char_counts):
                word_width = (char_count / total_chars) * line_width if total_chars > 0 else line_width / num_words
                w_x1 = cursor_x
                w_x2 = cursor_x + word_width
                cursor_x = w_x2

                cur.execute("""INSERT INTO OCR_WORD
                    (image_id, line_id, word, confidence, x1, y1, x2, y2,
                     line_x1, line_y1, line_x2, line_y2, bbox_is_estimated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                    (image_id, line_idx, word, confidence,
                     int(w_x1), int(line_y1), int(w_x2), int(line_y2),
                     int(line_x1), int(line_y1), int(line_x2), int(line_y2)))
                word_count_this_image += 1

        total_words += word_count_this_image
        processed += 1

        if processed % 25 == 0:
            conn.commit()
            print(f"Processed {processed}/{len(rows)} images...")

    conn.commit()
    conn.close()
    print(f"\nDone. OCR'd {processed} images ({failed} failed), extracted {total_words} words total.")


if __name__ == "__main__":
    main()
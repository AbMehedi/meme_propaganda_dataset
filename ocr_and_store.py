r"""
OCR extraction for the propaganda dataset (Phase 2, Layer 3: OCR_WORD).

Key enhancements (Phase B + D + E):
  - Phase B (Image Preprocessing):
      * Upscales low-res memes (< 1000px) so Bangla matras, conjuncts,
        and diacritics are clearly distinguishable for CRAFT text detector.
      * CLAHE (Contrast Limited Adaptive Histogram Equalization) on L-channel
        to enhance stylized and shadowed text against complex meme backgrounds.
      * Mild bilateral filtering to suppress JPEG compression artifacts
        while keeping character boundaries sharp.
      * Maps bounding box coordinates back to the original image space
        so all stored boxes match original dimensions.
  - Phase D + E (Detection & Word Filtering):
      * Filters out pure noise / artifact detections (confidence < 0.05
        or strings without any letters/numbers).
      * Strips unprintable control characters to prevent downstream
        rendering and PIL buffer corruptions.
  - Grapheme-cluster splitting for multi-word lines:
      * Accurately splits line boxes proportionally using Unicode \X
        grapheme clusters rather than naive character lengths.
  - Non-destructive table backup:
      * Automatically archives any existing OCR_WORD table to OCR_WORD_OLD_V{n}.
"""

import sqlite3
import regex  # pip install regex (supports \X grapheme clusters; stdlib `re` does not)
import easyocr
import cv2
import numpy as np


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
LANGUAGES = ['bn', 'en']  # Bangla + English

# EasyOCR detection tuning parameters
DETECT_KWARGS = dict(
    width_ths=0.4,
    height_ths=0.4,
    slope_ths=0.1
)

# Minimum confidence threshold to reject pure background noise
MIN_CONFIDENCE = 0.05
TARGET_MAX_DIM = 1000.0
# -----------------------------

GRAPHEME_RE = regex.compile(r'\X')  # \X = one user-perceived character (grapheme cluster)
ALPHANUM_RE = regex.compile(r'[\p{L}\p{N}]')  # Matches any Unicode letter or number


def grapheme_len(s: str) -> int:
    """Count rendered characters, not raw Unicode codepoints.
    Crucial for Bangla where conjuncts or base+matra sequences are single
    on-screen characters but multiple codepoints."""
    return len(GRAPHEME_RE.findall(s))


def preprocess_for_ocr(file_path: str):
    """Phase B Image Preprocessing:
    1. Reads image safely (handles Windows paths & Unicode correctly).
    2. Upscales low-res images (< TARGET_MAX_DIM) with Lanczos interpolation.
    3. Enhances contrast using CLAHE in LAB color space.
    4. Applies mild bilateral filtering to remove JPEG noise while preserving text edges.
    5. Returns (preprocessed_rgb_numpy_array, scale_factor).
    """
    try:
        data = np.fromfile(file_path, dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    except Exception:
        img = None

    if img is None:
        return None, 1.0

    h, w = img.shape[:2]
    scale = 1.0
    max_dim = max(h, w)

    # 1. Upscale if smaller than target resolution
    if max_dim < TARGET_MAX_DIM:
        scale = TARGET_MAX_DIM / float(max_dim)
        new_w = int(round(w * scale))
        new_h = int(round(h * scale))
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

    # 2. CLAHE contrast enhancement on luminance (L) channel
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    enhanced_bgr = cv2.cvtColor(cv2.merge((cl, a, b)), cv2.COLOR_LAB2BGR)

    # 3. Bilateral filter: removes compression artifacts without blurring font edges
    denoised_bgr = cv2.bilateralFilter(enhanced_bgr, d=5, sigmaColor=50, sigmaSpace=50)

    # 4. Convert to RGB for EasyOCR
    rgb_img = cv2.cvtColor(denoised_bgr, cv2.COLOR_BGR2RGB)

    return rgb_img, scale


def to_original_coord(coord: float, scale: float) -> int:
    """Scales upscaled coordinates back to original image dimensions."""
    return int(round(coord / scale)) if scale > 0 else int(round(coord))


def clean_word_text(word: str) -> str:
    """Strips unprintable control characters and leading/trailing whitespace."""
    if not word:
        return ""
    return "".join(ch for ch in word if ch.isprintable()).strip()


def is_valid_word(word: str, confidence: float) -> bool:
    """Filter out non-printable text, pure punctuation artifacts, or extreme noise."""
    if confidence < MIN_CONFIDENCE:
        return False
    if not word:
        return False
    # Must contain at least one letter or number
    if not ALPHANUM_RE.search(word):
        return False
    return True


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

    print("Initializing EasyOCR reader with GPU acceleration...")
    reader = easyocr.Reader(LANGUAGES, gpu=True)

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
        # Preprocess image with OpenCV (Phase B)
        preprocessed_img, scale = preprocess_for_ocr(file_path)
        if preprocessed_img is None:
            print(f"Image could not be read, skipping: {file_path}")
            failed += 1
            continue

        try:
            result = reader.readtext(preprocessed_img, **DETECT_KWARGS)
        except Exception as e:
            print(f"OCR error on {image_id}: {e}")
            failed += 1
            continue

        word_count_this_image = 0

        for line_idx, (bbox, line_text, confidence) in enumerate(result):
            raw_words = line_text.split()
            if not raw_words:
                continue

            # Scale line bbox coordinates back to original image space
            xs = [pt[0] for pt in bbox]
            ys = [pt[1] for pt in bbox]
            line_x1 = to_original_coord(min(xs), scale)
            line_x2 = to_original_coord(max(xs), scale)
            line_y1 = to_original_coord(min(ys), scale)
            line_y2 = to_original_coord(max(ys), scale)
            line_width = line_x2 - line_x1

            # Clean and validate words
            words = [clean_word_text(w) for w in raw_words]
            words = [w for w in words if w]
            if not words:
                continue

            # Single-word line: no split needed, box IS the detection
            if len(words) == 1:
                word = words[0]
                if not is_valid_word(word, confidence):
                    continue

                cur.execute("""INSERT INTO OCR_WORD
                    (image_id, line_id, word, confidence, x1, y1, x2, y2,
                     line_x1, line_y1, line_x2, line_y2, bbox_is_estimated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
                    (image_id, line_idx, word, float(confidence),
                     line_x1, line_y1, line_x2, line_y2,
                     line_x1, line_y1, line_x2, line_y2))
                word_count_this_image += 1
                continue

            # Multi-word line: split proportionally by grapheme count
            char_counts = [grapheme_len(w) for w in words]
            total_chars = sum(char_counts)
            num_words = len(words)

            cursor_x = float(line_x1)
            for word, char_count in zip(words, char_counts):
                word_width = (char_count / total_chars) * line_width if total_chars > 0 else line_width / num_words
                w_x1 = int(round(cursor_x))
                w_x2 = int(round(cursor_x + word_width))
                cursor_x += word_width

                if not is_valid_word(word, confidence):
                    continue

                cur.execute("""INSERT INTO OCR_WORD
                    (image_id, line_id, word, confidence, x1, y1, x2, y2,
                     line_x1, line_y1, line_x2, line_y2, bbox_is_estimated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                    (image_id, line_idx, word, float(confidence),
                     w_x1, line_y1, w_x2, line_y2,
                     line_x1, line_y1, line_x2, line_y2))
                word_count_this_image += 1

        total_words += word_count_this_image
        processed += 1

        if processed % 20 == 0:
            conn.commit()
            print(f"Processed {processed}/{len(rows)} images...")

    conn.commit()
    conn.close()
    print(f"\nDone. OCR'd {processed} images ({failed} failed), extracted {total_words} words total.")


if __name__ == "__main__":
    main()
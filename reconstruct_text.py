"""
Reading-order text reconstruction (Phase 2 -> Phase 3 bridge).

For each image, sorts OCR_WORD rows into reading order (line by line,
top-to-bottom; word by word within a line, left-to-right), joins them
into a single string, and records the exact (start_char, end_char) each
word occupies in that string.

This is what lets a human annotator mark a technique's text span on
readable text, while still letting you trace that span back to the
exact OCR_WORD rows (and therefore bounding boxes) it covers -- which
is what the graph model will eventually need.

Adds:
  IMAGE.reconstructed_text      -- the full string annotators will see
  WORD_OFFSET table             -- ocr_id -> (start_char, end_char) in
                                    that string, so a technique span can
                                    be mapped back to specific words/boxes
"""

import sqlite3

DB_PATH = "propaganda_dataset.db"
WORD_SEP = " "
LINE_SEP = "\n"


def build_schema(cur):
    cur.execute("PRAGMA table_info(IMAGE)")
    cols = [row[1] for row in cur.fetchall()]
    if "reconstructed_text" not in cols:
        cur.execute("ALTER TABLE IMAGE ADD COLUMN reconstructed_text TEXT")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS WORD_OFFSET (
        ocr_id INTEGER PRIMARY KEY,
        image_id TEXT,
        start_char INTEGER,
        end_char INTEGER,
        FOREIGN KEY (ocr_id) REFERENCES OCR_WORD(ocr_id),
        FOREIGN KEY (image_id) REFERENCES IMAGE(image_id)
    );
    """)


def reconstruct_for_image(cur, image_id):
    cur.execute("""
        SELECT ocr_id, line_id, word, x1, line_y1
        FROM OCR_WORD
        WHERE image_id = ?
    """, (image_id,))
    rows = cur.fetchall()
    if not rows:
        return None, []

    # Group by line_id, sort lines by their y-position, words within a
    # line by x-position -- gives natural top-to-bottom, left-to-right order.
    lines = {}
    for ocr_id, line_id, word, x1, line_y1 in rows:
        lines.setdefault(line_id, {"y": line_y1, "words": []})
        lines[line_id]["words"].append((x1, ocr_id, word))

    ordered_line_ids = sorted(lines.keys(), key=lambda lid: lines[lid]["y"])

    text_parts = []
    offsets = []  # (ocr_id, start_char, end_char)
    cursor = 0

    for i, line_id in enumerate(ordered_line_ids):
        words_in_line = sorted(lines[line_id]["words"], key=lambda w: w[0])  # sort by x1
        for j, (x1, ocr_id, word) in enumerate(words_in_line):
            start = cursor
            end = cursor + len(word)
            offsets.append((ocr_id, start, end))
            text_parts.append(word)
            cursor = end
            if j < len(words_in_line) - 1:
                text_parts.append(WORD_SEP)
                cursor += len(WORD_SEP)
        if i < len(ordered_line_ids) - 1:
            text_parts.append(LINE_SEP)
            cursor += len(LINE_SEP)

    full_text = "".join(text_parts)
    return full_text, offsets


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    build_schema(cur)
    conn.commit()

    cur.execute("SELECT DISTINCT image_id FROM OCR_WORD")
    image_ids = [row[0] for row in cur.fetchall()]
    print(f"Reconstructing text for {len(image_ids)} images...")

    done = 0
    for image_id in image_ids:
        full_text, offsets = reconstruct_for_image(cur, image_id)
        if full_text is None:
            continue

        cur.execute("UPDATE IMAGE SET reconstructed_text = ? WHERE image_id = ?", (full_text, image_id))

        for ocr_id, start, end in offsets:
            cur.execute("""
                INSERT OR REPLACE INTO WORD_OFFSET (ocr_id, image_id, start_char, end_char)
                VALUES (?, ?, ?, ?)
            """, (ocr_id, image_id, start, end))

        done += 1
        if done % 50 == 0:
            conn.commit()
            print(f"  {done}/{len(image_ids)} done...")

    conn.commit()
    conn.close()
    print(f"Done. Reconstructed text for {done} images.")


if __name__ == "__main__":
    main()

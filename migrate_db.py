"""
migrate_db.py
Ensures the core schema tables (PAGE, POST, IMAGE, OCR_WORD, WORD_OFFSET)
exist in propaganda_dataset.db.
Safe to run multiple times (uses CREATE TABLE IF NOT EXISTS).
"""
import argparse
import sqlite3

DB_PATH = "propaganda_dataset.db"

CORE_SCHEMA = """
CREATE TABLE IF NOT EXISTS PAGE (
    page_id TEXT PRIMARY KEY,
    page_name TEXT,
    page_url TEXT
);

CREATE TABLE IF NOT EXISTS POST (
    post_id TEXT PRIMARY KEY,
    page_id TEXT,
    post_url TEXT,
    timestamp TEXT,
    caption TEXT,
    scraped_at TEXT,
    likes INTEGER,
    comments INTEGER,
    shares INTEGER,
    FOREIGN KEY (page_id) REFERENCES PAGE(page_id)
);

CREATE TABLE IF NOT EXISTS IMAGE (
    image_id TEXT PRIMARY KEY,
    post_id TEXT,
    file_path TEXT,
    width INTEGER,
    height INTEGER,
    image_hash TEXT,
    perceptual_hash TEXT,
    original_image_url TEXT,
    fb_alt_text TEXT,
    reconstructed_text TEXT,
    FOREIGN KEY (post_id) REFERENCES POST(post_id)
);

CREATE TABLE IF NOT EXISTS OCR_WORD (
    ocr_id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_id TEXT,
    line_id INTEGER,
    word TEXT,
    confidence REAL,
    x1 INTEGER,
    y1 INTEGER,
    x2 INTEGER,
    y2 INTEGER,
    line_x1 INTEGER,
    line_y1 INTEGER,
    line_x2 INTEGER,
    line_y2 INTEGER,
    bbox_is_estimated INTEGER,
    FOREIGN KEY (image_id) REFERENCES IMAGE(image_id)
);

CREATE TABLE IF NOT EXISTS WORD_OFFSET (
    ocr_id INTEGER PRIMARY KEY,
    image_id TEXT,
    start_char INTEGER,
    end_char INTEGER,
    FOREIGN KEY (ocr_id) REFERENCES OCR_WORD(ocr_id),
    FOREIGN KEY (image_id) REFERENCES IMAGE(image_id)
);
"""

def main():
    parser = argparse.ArgumentParser(description="Migrate and verify core database schema.")
    parser.add_argument(
        "--drop-annotation-tables",
        action="store_true",
        help="Drop legacy ANNOTATION and LLM_PREANNOTATION tables if they exist",
    )
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if args.drop_annotation_tables:
        print("Dropping legacy annotation tables...")
        cur.execute("DROP TABLE IF EXISTS ANNOTATION")
        cur.execute("DROP TABLE IF EXISTS LLM_PREANNOTATION")
        conn.commit()

    conn.executescript(CORE_SCHEMA)
    conn.commit()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    print("Tables in database:", tables)
    print("Core schema migration complete!")
    conn.close()

if __name__ == "__main__":
    main()

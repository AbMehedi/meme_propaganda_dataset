"""
download_and_hash.py — Apify Dataset Ingestion (Multi-Dataset Support)
=======================================================================
Downloads images and metadata from one or more Apify dataset runs into
propaganda_dataset.db.

All dataset IDs are read from DATASET_IDS in .env (comma-separated).
A single APIFY_TOKEN covers all datasets (same Apify account).

Each dataset is processed sequentially. Duplicate posts and images are
safely skipped (INSERT OR IGNORE), so overlapping datasets will not
create duplicates in the database.

Usage:
    python download_and_hash.py
    python download_and_hash.py --dry-run      # list datasets, no downloads
    python download_and_hash.py --dataset-id <id>   # override with a single ID
"""

import argparse
import hashlib
import os
import sqlite3
from io import BytesIO
from urllib.parse import parse_qs, urlparse

import imagehash
import requests
from apify_client import ApifyClient
from dotenv import load_dotenv
from PIL import Image

# ---------- CONFIG ----------
load_dotenv()
APIFY_TOKEN = os.getenv("APIFY_TOKEN")
# Support both old DATASET_ID (single) and new DATASET_IDS (multi)
_raw_ids = os.getenv("DATASET_IDS") or os.getenv("DATASET_ID", "")
IMAGE_DIR = "raw_images"
DB_PATH = "propaganda_dataset.db"
# ----------------------------

# ─── Parse CLI args ──────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Ingest Apify datasets into DB.")
parser.add_argument(
    "--dry-run",
    action="store_true",
    help="List all dataset IDs to be processed, then exit without downloading.",
)
parser.add_argument(
    "--dataset-id",
    metavar="ID",
    help="Process a single dataset ID (overrides DATASET_IDS from .env).",
)
args = parser.parse_args()

# ─── Resolve dataset IDs ─────────────────────────────────────────────────────
if args.dataset_id:
    DATASET_IDS = [args.dataset_id.strip()]
else:
    DATASET_IDS = [d.strip() for d in _raw_ids.split(",") if d.strip()]

# ─── Validate ────────────────────────────────────────────────────────────────
if not APIFY_TOKEN:
    raise RuntimeError("APIFY_TOKEN is not set. Add it to .env.")
if not DATASET_IDS:
    raise RuntimeError(
        "No dataset IDs found. Set DATASET_IDS=id1,id2,... in .env "
        "or pass --dataset-id <id>."
    )

print(f"Apify account token loaded ✓")
print(f"Datasets to process ({len(DATASET_IDS)}): {DATASET_IDS}")

if args.dry_run:
    print("\n[dry-run] Exiting without downloading.")
    raise SystemExit(0)

# ─── Setup ───────────────────────────────────────────────────────────────────
os.makedirs(IMAGE_DIR, exist_ok=True)
client = ApifyClient(APIFY_TOKEN)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Ensure core schema exists (idempotent)
cur.executescript("""
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
""")
conn.commit()


# ─── Helpers ─────────────────────────────────────────────────────────────────
def extract_ids_from_post_url(post_url):
    """
    Pull post_id (story_fbid) and page_id (id) out of a
    facebook.com/permalink.php?story_fbid=...&id=... URL.
    Falls back to hashing the whole URL if the expected params aren't found.
    """
    if not post_url:
        return None, None

    parsed = urlparse(post_url)
    params = parse_qs(parsed.query)

    post_id = params.get("story_fbid", [None])[0]
    page_id = params.get("id", [None])[0]

    if not post_id:
        # Fallback: /posts/<id>/ or /photo/?fbid=<id> style URLs
        post_id = hashlib.md5(post_url.encode()).hexdigest()

    return post_id, page_id


def process_dataset(dataset_id):
    """Ingest all items from a single Apify dataset into the DB."""
    print(f"\n{'='*60}")
    print(f"Processing dataset: {dataset_id}")
    print(f"{'='*60}")

    item_count = 0
    image_count = 0
    skipped = 0

    for item in client.dataset(dataset_id).iterate_items():
        item_count += 1

        post_url = item.get("url")
        caption = item.get("text", "")
        likes = item.get("likes")
        comments = item.get("comments")
        shares = item.get("shares")
        timestamp = item.get("time") or item.get("timestamp") or item.get("date")

        post_id, page_id = extract_ids_from_post_url(post_url)

        if not post_id:
            print(f"  [SKIP] Could not determine post_id for: {post_url}")
            skipped += 1
            continue

        page_name = item.get("pageName") or item.get("authorName")
        page_url_field = item.get("pageUrl")

        if page_id:
            cur.execute(
                "INSERT OR IGNORE INTO PAGE (page_id, page_name, page_url) VALUES (?, ?, ?)",
                (page_id, page_name, page_url_field),
            )

        cur.execute(
            """INSERT OR IGNORE INTO POST
               (post_id, page_id, post_url, timestamp, caption, scraped_at, likes, comments, shares)
               VALUES (?, ?, ?, ?, ?, datetime('now'), ?, ?, ?)""",
            (post_id, page_id, post_url, timestamp, caption, likes, comments, shares),
        )

        # --- Media handling ---
        media_items = item.get("media") or []
        if isinstance(media_items, dict):
            media_items = [media_items]

        for media in media_items:
            if not isinstance(media, dict):
                continue

            media_type = media.get("__typename")

            if media_type == "Video":
                continue  # Phase 1: image-only
            elif media_type == "Photo":
                img_url = (media.get("photo_image") or {}).get("uri") or media.get("thumbnail")
            else:
                img_url = media.get("thumbnail")

            if not img_url:
                print(f"  [SKIP] No image URL in media for post {post_id}")
                skipped += 1
                continue

            try:
                resp = requests.get(img_url, timeout=15)
                resp.raise_for_status()
            except requests.RequestException as e:
                print(f"  [FAIL] Download failed {img_url}: {e}")
                skipped += 1
                continue

            img_bytes = resp.content

            try:
                img = Image.open(BytesIO(img_bytes)).convert("RGB")
            except (OSError, ValueError) as e:
                print(f"  [FAIL] Could not open image {img_url}: {e}")
                skipped += 1
                continue

            image_id = hashlib.md5(img_url.encode()).hexdigest()
            file_path = os.path.join(IMAGE_DIR, f"{image_id}.jpg")
            img.save(file_path, "JPEG")

            image_hash = hashlib.sha256(img_bytes).hexdigest()
            p_hash = str(imagehash.phash(img))
            fb_alt_text = media.get("ocrText")

            cur.execute(
                """INSERT OR IGNORE INTO IMAGE
                   (image_id, post_id, file_path, width, height,
                    image_hash, perceptual_hash, original_image_url, fb_alt_text)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    image_id, post_id, file_path, img.width, img.height,
                    image_hash, p_hash, img_url, fb_alt_text,
                ),
            )
            image_count += 1

    conn.commit()
    print(f"  → Done: {item_count} posts, {image_count} images saved, {skipped} skipped.")
    return item_count, image_count, skipped


# ─── Main Loop ───────────────────────────────────────────────────────────────
total_posts = 0
total_images = 0
total_skipped = 0

for ds_id in DATASET_IDS:
    posts, images, skipped = process_dataset(ds_id)
    total_posts += posts
    total_images += images
    total_skipped += skipped

conn.close()

print(f"\n{'='*60}")
print(f"ALL DATASETS COMPLETE")
print(f"  Datasets processed : {len(DATASET_IDS)}")
print(f"  Total posts seen   : {total_posts}")
print(f"  Total images saved : {total_images}")
print(f"  Total skipped      : {total_skipped}")
print(f"{'='*60}")
import os
import sqlite3
import requests
import hashlib
import imagehash
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO
from urllib.parse import urlparse, parse_qs
from apify_client import ApifyClient

# ---------- CONFIG ----------
load_dotenv()
APIFY_TOKEN = os.getenv("APIFY_TOKEN")
DATASET_ID = os.getenv("DATASET_ID")
IMAGE_DIR = "raw_images"
DB_PATH = "propaganda_dataset.db"
# -----------------------------

if not APIFY_TOKEN:
    raise RuntimeError("APIFY_TOKEN is not set. Add it to .env or the environment.")
if not DATASET_ID:
    raise RuntimeError("DATASET_ID is not set. Add it to .env or the environment.")

os.makedirs(IMAGE_DIR, exist_ok=True)
client = ApifyClient(APIFY_TOKEN)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# --- Layer 1 tables ---
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
""")

# --- Layer 2 table ---
cur.executescript("""
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
    FOREIGN KEY (post_id) REFERENCES POST(post_id)
);
""")

conn.commit()


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
        # Fallback: some post URLs use /posts/<id>/ or /photo/?fbid=<id> style paths
        post_id = hashlib.md5(post_url.encode()).hexdigest()

    return post_id, page_id


item_count = 0
image_count = 0
skipped = 0

for item in client.dataset(DATASET_ID).iterate_items():
    item_count += 1

    post_url = item.get("url")
    caption = item.get("text", "")
    likes = item.get("likes")
    comments = item.get("comments")
    shares = item.get("shares")

    # Timestamp: not present in the sample output we've seen so far.
    # Trying common alternate field names as a safety net.
    timestamp = item.get("time") or item.get("timestamp") or item.get("date")

    post_id, page_id = extract_ids_from_post_url(post_url)

    if not post_id:
        print(f"Could not determine post_id for item, skipping entirely: {post_url}")
        skipped += 1
        continue

    # Page name/URL: not present in this sample either.
    # Left as None for now — check a raw item yourself for any field
    # like 'pageName', 'authorName', 'ownerName' etc. and wire it in here.
    page_name = item.get("pageName") or item.get("authorName")
    page_url_field = item.get("pageUrl")

    if page_id:
        cur.execute("""INSERT OR IGNORE INTO PAGE (page_id, page_name, page_url)
                       VALUES (?, ?, ?)""", (page_id, page_name, page_url_field))

    cur.execute("""INSERT OR IGNORE INTO POST
                   (post_id, page_id, post_url, timestamp, caption, scraped_at, likes, comments, shares)
                   VALUES (?, ?, ?, ?, ?, datetime('now'), ?, ?, ?)""",
                (post_id, page_id, post_url, timestamp, caption, likes, comments, shares))

    # --- Media handling ---
    media_items = item.get("media") or []
    if isinstance(media_items, dict):
        media_items = [media_items]

    for media in media_items:
        if not isinstance(media, dict):
            continue

        media_type = media.get("__typename")

        if media_type == "Video":
            # Phase 1 spec targets image-based posts — skip videos
            continue
        elif media_type == "Photo":
            img_url = (media.get("photo_image") or {}).get("uri") or media.get("thumbnail")
        else:
            img_url = media.get("thumbnail")

        if not img_url:
            print(f"No usable image URL in media item for post {post_id}, skipping.")
            skipped += 1
            continue

        try:
            resp = requests.get(img_url, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            print(f"Failed to download {img_url}: {e}")
            skipped += 1
            continue

        img_bytes = resp.content

        try:
            img = Image.open(BytesIO(img_bytes)).convert("RGB")
        except Exception as e:
            print(f"Could not open image {img_url}: {e}")
            skipped += 1
            continue

        image_id = hashlib.md5(img_url.encode()).hexdigest()
        file_path = os.path.join(IMAGE_DIR, f"{image_id}.jpg")
        img.save(file_path, "JPEG")

        image_hash = hashlib.sha256(img_bytes).hexdigest()
        p_hash = str(imagehash.phash(img))
        fb_alt_text = media.get("ocrText")  # Facebook's own alt-text, not real OCR

        cur.execute("""INSERT OR IGNORE INTO IMAGE
            (image_id, post_id, file_path, width, height,
             image_hash, perceptual_hash, original_image_url, fb_alt_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (image_id, post_id, file_path, img.width, img.height,
             image_hash, p_hash, img_url, fb_alt_text))

        image_count += 1

conn.commit()
conn.close()

print(f"Done. Processed {item_count} posts, saved {image_count} images, skipped {skipped}.")
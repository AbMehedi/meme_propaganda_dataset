# Bangla Propaganda Dataset — Layer 1 & 2 Setup

This covers scraping raw Facebook data (Layer 1: pages/posts) and downloading + hashing images (Layer 2) using Apify. No OCR or annotation yet — that's Phase 2/3, documented separately.

## What you'll end up with

```
meme_propaganda_dataset/
├── raw_images/                ← downloaded image files (.jpg)
├── propaganda_dataset.db      ← SQLite database (PAGE, POST, IMAGE tables)
├── download_and_hash.py       ← main script
└── migrate_db.py              ← one-time schema migration helper (see Troubleshooting)
```

---

## 1. Prerequisites

- Python 3.9+ installed
- An Apify account (free tier is fine to start) — sign up at apify.com

## 2. Install dependencies

```bash
pip install apify-client pillow imagehash requests
```

## 3. Set up the Apify scraper

1. Log into the Apify Console → **Settings → Integrations** → copy your **Personal API token**.
2. Go to **Store**, search **"Facebook Posts Scraper"**, and open the official `apify/facebook-posts-scraper` actor (developer: Apify, not a third-party clone).
3. Configure the Input (JSON view):

```json
{
  "startUrls": [
    { "url": "https://www.facebook.com/<page-1>" },
    { "url": "https://www.facebook.com/<page-2>" }
  ],
  "resultsLimit": 40
}
```

   - List all 20–30 target pages here (news, political commentary, satire/parody, opinion — per Phase 1 spec).
   - `resultsLimit` = max posts per page. Set high enough that `pages × limit` comfortably clears the 500–1,000 post target.
4. Click **Start**. Once finished, open the **Dataset** tab and copy the **Dataset ID** from the URL (`https://api.apify.com/v2/datasets/<DATASET_ID>`).

**Test small first:** run 2 pages with `resultsLimit: 5` before scaling up, and sanity-check the output JSON — confirm `media`, `url`, `text` fields are present and match what the script below expects.

## 4. Run the download + hash script

1. Open `download_and_hash.py` and fill in:
   ```python
   APIFY_TOKEN = "your_apify_token_here"
   DATASET_ID = "your_dataset_id_here"
   ```
2. Run it:
   ```bash
   py download_and_hash.py
   ```
3. Watch the console output — it prints failed downloads and finishes with a summary:
   ```
   Done. Processed 40 posts, saved 37 images, skipped 1.
   ```

## 5. Verify the results

```bash
sqlite3 propaganda_dataset.db
```

```sql
SELECT COUNT(*) FROM POST;
SELECT COUNT(*) FROM IMAGE;
SELECT post_id, post_url, caption, likes, comments, shares FROM POST LIMIT 5;
SELECT image_id, perceptual_hash, fb_alt_text FROM IMAGE LIMIT 5;
```

Also open a few files in `raw_images/` to confirm they're valid, correct images.

---

## Database schema (current)

**PAGE**
| Column | Notes |
|---|---|
| page_id (PK) | Extracted from post URL's `id` query param |
| page_name | Often `NULL` — this actor's post-list view doesn't always include it |
| page_url | Often `NULL`, same reason |

**POST**
| Column | Notes |
|---|---|
| post_id (PK) | Extracted from post URL's `story_fbid` param (or hashed URL as fallback) |
| page_id | FK → PAGE |
| post_url | Original Facebook post URL — **provenance, never discard** |
| timestamp | Currently `NULL` — this actor's output didn't expose a timestamp field in our samples; flagged for follow-up |
| caption | Post text |
| scraped_at | Auto-set to run time |
| likes / comments / shares | Engagement counts, captured as a bonus (not required by MVP spec) |

**IMAGE**
| Column | Notes |
|---|---|
| image_id (PK) | MD5 hash of the image URL |
| post_id | FK → POST |
| file_path | Local path under `raw_images/` |
| width / height | Pixel dimensions |
| image_hash | SHA-256 of raw image bytes (exact-duplicate detection) |
| perceptual_hash | pHash (near-duplicate detection — crops, text edits, recompression) — **mandatory per spec** |
| original_image_url | Original Facebook CDN image URL — **provenance, never discard** |
| fb_alt_text | Facebook's own auto-generated alt-text (`ocrText` field). **Not real OCR** — just free bonus metadata, often incomplete/garbled. Do not use as a substitute for the Phase 2 OCR pipeline. |

---

## Known limitations / things to double-check

- **No timestamp field found yet.** If a teammate spots a date/time field under a different key in the raw JSON (e.g. `publish_time`, `createdTime`), add it to the `timestamp = item.get(...)` fallback chain in the script.
- **page_name / page_url are usually empty.** The post-list actor output doesn't reliably include page metadata. If this matters later, consider a follow-up scrape of each page's profile info separately.
- **Videos are intentionally skipped** (`__typename == "Video"` in the media list) — Phase 1 targets image-based posts only.
- **A small % of image downloads will fail** even with retries (expired CDN URLs, transient DNS issues) — this is normal at scale; a ~2–3% skip rate is expected and not worth chasing further.

---

## Troubleshooting

### `sqlite3.OperationalError: table POST has no column named X`
This happens if `propaganda_dataset.db` already exists from an earlier run with an older schema — `CREATE TABLE IF NOT EXISTS` won't add new columns to an existing table.

**Fix option A (keep existing data):** run `migrate_db.py` once to add missing columns.

**Fix option B (start fresh, simplest if no data worth keeping):**
```bash
del propaganda_dataset.db      # Windows
# or: rm propaganda_dataset.db   # Mac/Linux
py download_and_hash.py
```

### `Failed to download ...: No connection adapters were found for '{...}'`
Means the script tried to pass a dict (not a URL string) to `requests.get()`. This is already fixed in the current `download_and_hash.py` — if you see this again, check that the `media` parsing block correctly extracts `photo_image.uri` / `thumbnail` before downloading.

### `Failed to resolve '...fbcdn.net' (getaddrinfo failed)`
Transient DNS/network failure — normal at this scale (~1 in 30–40 images). The script retries automatically (3 attempts with backoff) before giving up and skipping. No action needed unless failure rates are unusually high (>10%), in which case check your network/proxy setup.

---

## Next steps (not covered here)

- **Phase 2 / Layer 3 (OCR):** run Google Cloud Vision `document_text_detection` on each saved image, storing word-level text + bounding boxes in a new `OCR_WORD` table.
- **Phase 3 (Annotation):** set up Label Studio for technique/modality/text-span labeling.

Questions or schema changes → update this README alongside the script so it stays in sync.
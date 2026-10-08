# Multimodal Bangla Propaganda Detection Dataset
## Operational Plan — Data Acquisition & OCR Pipeline

This document defines the operational directives for collecting, processing, and structuring a multimodal Bangla meme and post dataset.

The core objective is to collect and structure data that preserves the **visual, textual, and spatial relationships** required for multimodal modeling, while keeping the data collection, database migration, and OCR processing pipeline fast, robust, and reproducible.

---

# Phase 1: Data Collection & Scraping Strategy

The scraping team must focus on **broad and diverse collection rather than filtering for propaganda**.

If the dataset is collected only from known propaganda sources, downstream models may learn biased shortcuts—for example, associating all political images with propaganda. The dataset therefore needs natural negative examples and diverse content.

## 1.1 Collection Target

| Requirement | Target |
|---|---|
| Public Bangla media pages | **20–30 diverse pages** |
| Initial dataset size | **500–1,000 image-based posts** |
| Primary content | Bangla image-based Facebook posts |
| Required media | Image + caption + post metadata |

## 1.2 Content Inclusion

The collection should include a natural mixture of:

- News
- Political commentary
- Satire
- Humor
- General opinion
- Other relevant Bangla online-media content

The goal is to preserve both potentially propagandistic content and **natural negative examples**.

## 1.3 Asset Management

For every collected post:

- Save the **original image file locally** in `raw_images/`.
- Preserve the **original Facebook post URL**.
- Preserve the **original image URL**, when available.
- Preserve the original caption without unnecessary modification.
- Record the collection/scraping timestamp.

The raw files should be retained because future processing and model development require access to the original image.

---

# Phase 2: Database Schema & Automated Processing

The dataset architecture is divided into three processing layers:

1. **Layer 1: Raw Facebook Data (`PAGE`, `POST`)**
2. **Layer 2: Image Processing (`IMAGE`)**
3. **Layer 3: OCR Extraction & Spatial Text Reconstruction (`OCR_WORD`, `WORD_OFFSET`)**

## 2.1 What to Scrape vs. Generate

| Data Type | Action Owner |
|---|---|
| Page ID | **Scraper — Immediate** |
| Page Name | **Scraper — Immediate** |
| Page URL | **Scraper — Immediate** |
| Post ID | **Scraper — Immediate** |
| Post URL | **Scraper — Immediate** |
| Timestamp | **Scraper — Immediate** |
| Caption | **Scraper — Immediate** |
| Original Image File | **Scraper — Immediate** |
| Original Image URL | **Scraper — Immediate** |
| Scraped-at Timestamp | **Scraper — Immediate** |
| Image Hash (MD5) | **Automated Pipeline — Post-scrape (`download_and_hash.py`)** |
| Perceptual Hash (pHash) | **Automated Pipeline — Post-scrape (`download_and_hash.py`)** |
| OCR Words & Confidence | **Automated Pipeline — EasyOCR (`ocr_and_store.py`)** |
| OCR Bounding Boxes | **Automated Pipeline — EasyOCR (`ocr_and_store.py`)** |
| Reconstructed Text & Offsets | **Automated Pipeline — (`reconstruct_text.py`)** |

---

## 2.2 Database Tables

### Table 1: PAGE — Raw Facebook Page Data

Stores information about the public Facebook pages selected for collection.

| Field | Description |
|---|---|
| `page_id` | Unique Facebook page identifier |
| `page_name` | Name of the Facebook page |
| `page_url` | Original Facebook page URL |

```text
PAGE
├── page_id (PK)
├── page_name
└── page_url
```

---

### Table 2: POST — Raw Facebook Post Data

Stores the original metadata collected from each Facebook post.

| Field | Description |
|---|---|
| `post_id` | Unique Facebook post identifier |
| `page_id` | Reference to source PAGE |
| `post_url` | Original Facebook post URL |
| `timestamp` | Original post publication timestamp |
| `caption` | Original post caption/text |
| `scraped_at` | Timestamp when the post was collected |
| `likes` | Like count |
| `comments` | Comment count |
| `shares` | Share count |

```text
POST
├── post_id (PK)
├── page_id (FK -> PAGE.page_id)
├── post_url
├── timestamp
├── caption
├── scraped_at
├── likes
├── comments
└── shares
```

---

### Table 3: IMAGE — Image Processing Data

Stores the original image file and machine-generated image identifiers.

| Field | Description |
|---|---|
| `image_id` | Unique internal image identifier |
| `post_id` | Reference to source POST |
| `file_path` | Local path to the saved image |
| `width` | Original image width |
| `height` | Original image height |
| `image_hash` | MD5 image hash |
| `perceptual_hash` | Perceptual image hash (pHash) for visual deduplication |
| `original_image_url` | Source image URL |
| `fb_alt_text` | Facebook alt-text description (if available) |
| `reconstructed_text` | Full reading-order reconstructed OCR text string |

```text
IMAGE
├── image_id (PK)
├── post_id (FK -> POST.post_id)
├── file_path
├── width
├── height
├── image_hash
├── perceptual_hash
├── original_image_url
├── fb_alt_text
└── reconstructed_text
```

---

### Table 4: OCR_WORD — OCR Output & Bounding Boxes

Stores OCR results at the word level, including spatial coordinates.

| Field | Description |
|---|---|
| `ocr_id` | Unique OCR record identifier |
| `image_id` | Reference to source IMAGE |
| `line_id` | Detected line index |
| `word` | OCR-detected word |
| `confidence` | OCR confidence score |
| `x1`, `y1`, `x2`, `y2` | Estimated word bounding box |
| `line_x1`, `line_y1`, `line_x2`, `line_y2` | Ground-truth detected line box |
| `bbox_is_estimated` | 1 if estimated word split, 0 if single detection |

---

### Table 5: WORD_OFFSET — Character Spans in Reconstructed Text

Maps each `OCR_WORD` to its exact character range in `IMAGE.reconstructed_text`.

| Field | Description |
|---|---|
| `ocr_id` | Reference to OCR_WORD |
| `image_id` | Reference to IMAGE |
| `start_char` | Start character index in reconstructed text |
| `end_char` | End character index in reconstructed text |

---

# Phase 3: Automated Pipeline Workflow

```text
Facebook Public Pages (Apify Scraper)
        │
        ▼
   Scrape Posts & Download Images
   (`download_and_hash.py`)
        │
        ├── Save images to raw_images/
        ├── Deduplicate via MD5 & pHash
        └── Store in PAGE, POST, IMAGE tables
        │
        ▼
   Database Schema Verification
   (`migrate_db.py`)
        │
        ▼
   Automated Bangla + English OCR
   (`ocr_and_store.py`)
        │
        ├── EasyOCR line detection
        ├── Grapheme-cluster word segmentation
        └── Store in OCR_WORD table
        │
        ▼
   Reading-Order Reconstruction
   (`reconstruct_text.py`)
        │
        ├── Line-by-line reading order sorting
        ├── Populate IMAGE.reconstructed_text
        └── Populate WORD_OFFSET table
        │
        ▼
   OCR Quality Verification
   (`verify_ocr.py`)
        │
        └── Generate visual bounding-box overlays in ocr_check/
```

---

# Phase 4: Data Preservation Principle

The central principle of the dataset is:

> **Collect first, preserve spatial coordinates, and avoid irreversible loss.**

In particular:
- Keep the original image files.
- Keep the original caption and URLs.
- Keep timestamps and engagement metrics.
- Keep exact and perceptual hashes.
- Keep word and line-level bounding boxes.
- Keep OCR confidence scores.
- Preserve character offsets mapped to bounding boxes.

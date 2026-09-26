# Multimodal Bangla Propaganda Detection Dataset
## Operational Plan — MVP Phase

This document defines the operational directives for collecting, processing, and annotating a multimodal Bangla propaganda detection dataset.

The core objective is to collect and structure data that preserves the **visual, textual, and spatial relationships** required for future graph-based multimodal modeling (e.g., MViTO-GAT), while keeping the initial data collection and processing pipeline manageable.

---

# Phase 1: Data Collection & Scraping Strategy

The scraping team must focus on **broad and diverse collection rather than filtering for propaganda**.

If the dataset is collected only from known propaganda sources, the model may learn biased shortcuts—for example, associating all political images with propaganda. The dataset therefore needs natural negative examples and diverse content.

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

- Save the **original image file locally**.
- Preserve the **original Facebook post URL**.
- Preserve the **original image URL**, when available.
- Preserve the original caption without unnecessary modification.
- Record the collection/scraping timestamp.

The raw files should be retained because future processing and model development may require access to the original image.

---

# Phase 2: Database Schema & Automated Processing

The dataset architecture is divided into three initial processing layers:

1. **Raw Facebook Data**
2. **Image Processing**
3. **OCR Data**

Human annotation is performed after the automated processing stages.

The scraper is responsible for collecting raw information. Downstream automated scripts are responsible for OCR and image hashing.

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
| Image Hash | **Automated Pipeline — Post-scrape** |
| Perceptual Hash | **Automated Pipeline — Post-scrape** |
| OCR Text | **Automated Pipeline — Post-scrape** |
| OCR Bounding Boxes | **Automated Pipeline — Post-scrape** |
| Visual Objects | **Deferred — Future ML Phase** |
| CLIP Embeddings | **Deferred — Future ML Phase** |
| Technique Labels | **Human Annotators** |
| Modality Labels | **Human Annotators** |
| Text Spans | **Human Annotators** |

---

# 2.2 Database Tables

## Table 1: PAGE — Raw Facebook Page Data

Stores information about the public Facebook pages selected for collection.

| Field | Description |
|---|---|
| `page_id` | Unique Facebook page identifier |
| `page_name` | Name of the Facebook page |
| `page_url` | Original Facebook page URL |

### PAGE Schema

```text
PAGE
├── page_id
├── page_name
└── page_url
```

---

## Table 2: POST — Raw Facebook Post Data

Stores the original metadata collected from each Facebook post.

| Field | Description |
|---|---|
| `post_id` | Unique Facebook post identifier |
| `page_id` | Reference to the source PAGE |
| `post_url` | Original Facebook post URL |
| `timestamp` | Original post publication timestamp |
| `caption` | Original post caption/text |
| `scraped_at` | Timestamp when the post was collected |

### POST Schema

```text
POST
├── post_id
├── page_id
├── post_url
├── timestamp
├── caption
└── scraped_at
```

**Relationship:**

```text
PAGE 1 ──────────── N POST
```

A single page can contain many collected posts.

---

## Table 3: IMAGE — Image Processing Data

Stores the original image file and machine-generated image identifiers.

| Field | Description |
|---|---|
| `image_id` | Unique internal image identifier |
| `post_id` | Reference to the source POST |
| `file_path` | Local path to the saved original image |
| `width` | Original image width |
| `height` | Original image height |
| `image_hash` | Exact/cryptographic image hash |
| `perceptual_hash` | Perceptual image hash for visual similarity |

### IMAGE Schema

```text
IMAGE
├── image_id
├── post_id
├── file_path
├── width
├── height
├── image_hash
└── perceptual_hash
```

**Relationship:**

```text
POST 1 ──────────── N IMAGE
```

The schema allows multiple images to be associated with a post if required.

### Important: Perceptual Hash

The `perceptual_hash` field is **mandatory**.

Perceptual hashing should be used to identify visually similar content, including:

- Reposted memes
- Duplicate images
- Cropped versions
- Resized versions
- Images with small modifications
- Similar visual content across different pages

This information can later support research into repeated content and coordination.

---

## Table 4: OCR_WORD — OCR Output

Stores OCR results at the **word level**, including the spatial location of each detected word.

| Field | Description |
|---|---|
| `ocr_id` | Unique OCR record identifier |
| `image_id` | Reference to the source IMAGE |
| `word` | OCR-detected word/text |
| `confidence` | OCR confidence score |
| `x1` | Left/top bounding-box coordinate |
| `y1` | Top bounding-box coordinate |
| `x2` | Right/bottom bounding-box coordinate |
| `y2` | Bottom/right bounding-box coordinate |

### OCR_WORD Schema

```text
OCR_WORD
├── ocr_id
├── image_id
├── word
├── confidence
├── x1
├── y1
├── x2
└── y2
```

**Relationship:**

```text
IMAGE 1 ──────────── N OCR_WORD
```

---

## 2.3 OCR Storage Rule

**Never discard OCR bounding-box coordinates.**

Saving only a text string is insufficient for the future multimodal architecture.

For example:

```text
OCR output:

"সরকার"  → (x1, y1, x2, y2)
"ব্যর্থ"  → (x1, y1, x2, y2)
"হয়েছে" → (x1, y1, x2, y2)
```

The spatial coordinates allow the OCR text objects to be connected with visual objects in future multimodal graph construction.

### MVP OCR Rule

At this stage:

- Save the raw OCR words.
- Save OCR confidence.
- Save bounding-box coordinates.
- Preserve the relationship between each word and its source image.
- **Do not implement NLP phrase chunking yet.**
- **Do not discard word-level OCR information.**

Phrase construction and advanced NLP processing can be performed later.

---

# Phase 3: Human Annotation Directives

Human annotators will work with the processed images and OCR information to identify propaganda techniques.

The annotation system must support **multi-label classification**, **modality tracking**, and **text-span annotation**.

---

## 3.1 Multi-Label Annotation

A single post/image may contain multiple propaganda techniques.

For example, a meme may contain:

```text
Loaded Language
+
Smears
+
Appeal to Strong Emotions
```

Therefore, the database must allow multiple technique labels to be associated with a single post.

### Annotation Principle

Do **not** force each post into exactly one propaganda category.

A post may have:

- One technique
- Multiple techniques
- No propaganda technique

---

# 3.2 Modality Tracking

For every identified propaganda technique, annotators must specify the modality through which the technique is expressed.

Use exactly three categories:

| Modality | Meaning |
|---|---|
| `TEXT` | The technique is expressed through written/OCR text |
| `IMAGE` | The technique is expressed through visual content |
| `BOTH` | The technique requires both text and image |

### Example

```text
Technique: Loaded Language
Modality: TEXT
```

```text
Technique: Appeal to Fear / Prejudice
Modality: BOTH
```

This information will later support evaluation of multimodal reasoning.

---

# 3.3 Text-Span Annotation

When a propaganda technique is identified within OCR text, annotators must mark the **exact text span**.

Required fields:

```text
start_char
end_char
```

The span should refer to the text representation used for annotation.

### Example

Suppose the text is:

```text
"ওরা দেশের শত্রু"
```

If the technique applies to:

```text
"দেশের শত্রু"
```

the annotation should store the corresponding character positions:

```text
start_char = ...
end_char   = ...
```

The exact character offsets must be preserved so that future token-level or span-level detection models can be trained.

---

# 3.4 No Manual Visual Bounding Boxes

Annotators should **not manually draw bounding boxes** around visual elements such as:

- People
- Flags
- Objects
- Logos
- Buildings
- Faces
- Other visual regions

Visual-region extraction is outside the MVP annotation scope.

In a later ML phase, automated object detectors such as **Faster R-CNN** may be used to extract visual regions.

The current dataset should preserve enough information to support that future processing.

---

# 3.5 Initial Propaganda Technique Taxonomy

The MVP should use a **small and manageable taxonomy** rather than a large technique list.

Use the following initial categories:

1. **Loaded Language**
2. **Name Calling / Labeling**
3. **Smears**
4. **Appeal to Fear / Prejudice**
5. **Exaggeration / Minimisation**
6. **Slogans**
7. **Appeal to Strong Emotions**
8. **No Propaganda Technique**

The taxonomy may be expanded in a future phase after evaluating annotation quality and dataset coverage.

---

# Phase 4: MVP Scope Constraints

The MVP is focused on establishing a reliable **data collection → OCR → annotation pipeline**.

The following components are explicitly **out of scope** for this phase:

- Graph Attention Networks
- MViTO-GAT implementation
- Object detection models
- Faster R-CNN implementation
- CLIP embeddings
- Visual object extraction
- Coordination network analysis
- Advanced NLP phrase chunking
- Final multimodal graph construction

These components can be developed after the dataset has been collected, processed, and validated.

---

# 4.1 MVP Pipeline

The complete MVP pipeline is:

```text
Facebook Public Pages
        │
        ▼
   Scrape Posts
        │
        ├── Page Metadata
        ├── Post Metadata
        ├── Caption
        └── Original Image
        │
        ▼
 Save Raw Dataset
        │
        ▼
 Image Processing
        │
        ├── Image Hash
        ├── Perceptual Hash
        ├── Width / Height
        └── Local File Path
        │
        ▼
 Automated OCR
        │
        ├── Raw Words
        ├── Confidence
        └── Bounding Boxes
        │
        ▼
 Human Annotation
        │
        ├── Propaganda Techniques
        ├── Modality
        └── Text Spans
        │
        ▼
 Validated MVP Dataset
```

---

# 4.2 Data Preservation Principle

The central principle of the MVP is:

> **Collect first, preserve information, and defer complex modeling.**

The dataset must retain the original information needed for future multimodal research.

In particular:

- Keep the original image.
- Keep the original caption.
- Keep the original post URL.
- Keep the original image URL when available.
- Keep timestamps.
- Keep image dimensions.
- Keep exact image hashes.
- Keep perceptual hashes.
- Keep OCR words.
- Keep OCR confidence.
- Keep OCR bounding boxes.
- Keep annotation spans.
- Keep multiple technique labels.
- Keep modality labels.

Avoid irreversible preprocessing during the collection stage.

---

# 4.3 Final MVP Objective

The final output of this phase should be a structured dataset containing:

```text
20–30 diverse Bangla Facebook pages
            ↓
500–1,000 image-based posts
            ↓
Original images + captions + provenance
            ↓
Image hashes + perceptual hashes
            ↓
Bangla OCR words + confidence + coordinates
            ↓
Human propaganda-technique annotations
            ↓
Modality labels
            ↓
Character-level text spans
```

This dataset should provide the foundation for future work involving:

- Multimodal propaganda classification
- Token/span-level propaganda detection
- Visual-textual relationship modeling
- Object-region and OCR-region graph construction
- CLIP-based multimodal representations
- Graph attention networks such as MViTO-GAT
- Repeated-content analysis
- Future coordination analysis

The MVP does **not** attempt to solve these modeling problems yet. Its purpose is to create a reliable, provenance-preserving, spatially aware dataset that makes those future stages possible.

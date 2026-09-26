# GPT & Prompt Design: Getting Started Guide
## Bangla Meme Propaganda — HITL Annotation Workflow

---

## Your Current Dataset State

Your SQLite database (`propaganda_dataset.db`) contains:

| Table | Rows | Purpose |
|---|---|---|
| `POST` | 40 | Facebook posts (caption, timestamp, likes/comments/shares) |
| `IMAGE` | 37 | Images per post (file path, alt text, `reconstructed_text`) |
| `OCR_WORD` | 610 | Word-level OCR results with bounding boxes |
| `WORD_OFFSET` | 610 | Character offsets for each OCR word (maps to `start_char`/`end_char`) |
| `PAGE` | 1 | Source page metadata (Prothom-Alu) |

> [!IMPORTANT]
> The `IMAGE.reconstructed_text` column is your **primary OCR input** for GPT prompts. The `WORD_OFFSET` table gives you character-level spans for `evidence_span` fields. No `ANNOTATION` or `LLM_PREANNOTATION` table exists yet — you need to create these.

---

## Step 0: Add the Missing Tables First

Before calling GPT, add the two tables the HITL workflow requires:

```sql
-- Run this once against propaganda_dataset.db

CREATE TABLE IF NOT EXISTS LLM_PREANNOTATION (
    llm_annotation_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id            TEXT NOT NULL,
    image_id           TEXT,
    model_name         TEXT NOT NULL,           -- e.g. "gpt-4o"
    prompt_version     TEXT NOT NULL,           -- e.g. "v1.0"
    run_id             INTEGER NOT NULL,         -- 1–5 for multi-sample
    predicted_label    TEXT NOT NULL,           -- T01…T08
    modality           TEXT NOT NULL,           -- M1 / M2 / M3
    confidence_score   REAL,                    -- 0.0–1.0
    rationale_span     TEXT,                    -- exact OCR substring
    reasoning          TEXT,
    raw_response       TEXT,                    -- full JSON from API
    created_at         TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (post_id) REFERENCES POST(post_id)
);

CREATE TABLE IF NOT EXISTS ANNOTATION (
    annotation_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id            TEXT NOT NULL,
    image_id           TEXT,
    technique_label    TEXT NOT NULL,           -- T01…T08
    modality           TEXT NOT NULL,           -- M1 / M2 / M3
    start_char         INTEGER,
    end_char           INTEGER,
    evidence_span      TEXT,
    annotation_source  TEXT NOT NULL,           -- 'llm_preannotated' | 'human_annotated'
    verification_status TEXT NOT NULL DEFAULT 'PENDING',  -- PENDING | LLM_PRE | HUMAN_VERIFIED | HUMAN_CORRECTED | ADJUDICATED
    human_annotator_id TEXT,
    adjudication_status TEXT DEFAULT 'NONE',
    llm_preannotation_id INTEGER,              -- FK back to LLM output
    created_at         TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (post_id) REFERENCES POST(post_id),
    FOREIGN KEY (llm_preannotation_id) REFERENCES LLM_PREANNOTATION(llm_annotation_id)
);
```

---

## Step 1: System Prompt (v1.0)

This is the **core prompt** you feed to GPT as the `system` message. It embeds your entire codebook.

```
You are an expert propaganda analyst specializing in Bangla-language social media memes.
Your task is to detect propaganda techniques in Bangla meme posts.

You will be given:
1. OCR_TEXT: The full reconstructed text extracted from the meme image.
2. CAPTION: The Facebook post caption (may be empty).
3. ALT_TEXT: Facebook's auto-generated image description (may be empty).

---

## TAXONOMY (label exactly as shown)

| Code | Technique |
|------|-----------|
| T01  | Loaded Language |
| T02  | Name Calling / Labeling |
| T03  | Smears |
| T04  | Appeal to Fear / Prejudice |
| T05  | Exaggeration / Minimisation |
| T06  | Slogans |
| T07  | Appeal to Strong Emotions |
| T08  | No Propaganda Technique |

## MODALITY CODES

| Code | Meaning |
|------|---------|
| M1   | TEXT — technique is evident from OCR text alone |
| M2   | IMAGE — technique is evident from image alone (no text evidence) |
| M3   | BOTH — text and image together construct the technique |

---

## DECISION RULES

1. Evaluate ALL seven techniques independently. Do not stop at the first match.
2. If T08 applies, it must be used ALONE — never combine T08 with T01–T07.
3. If you cannot determine the technique because there is insufficient information, output a single label: NEEDS_REVIEW.
4. Use T01 (Loaded Language) ONLY when emotionally charged language does not more specifically fit T02–T07.
5. T02 (Name Calling) requires: TARGET + DEROGATORY LABEL explicitly present.
6. T03 (Smears) requires: TARGET + SPECIFIC NEGATIVE CLAIM + REPUTATIONAL DAMAGE.
7. T04 (Appeal to Fear) requires: identifiable THREAT / DANGER / FEAR / PREJUDICE.
8. T05 (Exaggeration/Minimisation) requires: clear contextual evidence of substantial overstatement or downplay.
9. T06 (Slogan) requires: short, rallying, persuasive phrase functioning as substitute for reasoning.
10. T07 (Strong Emotions) requires: intense NON-FEAR emotion deliberately provoked (rage, outrage, pity, pride, admiration, hatred).
11. DO NOT infer author intent. Label only what is observably present.
12. DO NOT fact-check. Label based on propagandistic presentation, not factual accuracy.
13. Banglish (mixed Bangla/English) should be evaluated normally.
14. Sarcasm: if text+image create a sarcastic propaganda meaning, use M3.

## CONFIDENCE SCORE GUIDANCE

Assign a confidence_score (0.0–1.0) per label:
- 0.9–1.0: Strong, unambiguous evidence
- 0.7–0.89: Clear evidence with minor ambiguity
- 0.5–0.69: Evidence present but genuinely uncertain
- Below 0.5: Very uncertain — flag for human review

---

## OUTPUT FORMAT

Return ONLY valid JSON. No markdown. No explanation outside the JSON.

{
  "post_id": "<post_id>",
  "labels": [
    {
      "label": "T01",
      "modality": "M1",
      "confidence_score": 0.92,
      "rationale_span": "<exact substring from OCR_TEXT>",
      "reasoning": "<1-2 sentence explanation>"
    }
  ],
  "overall_confidence": 0.85,
  "needs_review": false,
  "review_reason": null
}

Rules for the JSON:
- "labels" must be a list. For T08, it contains exactly one item: {"label":"T08","modality":"M1","confidence_score":...,"rationale_span":null,"reasoning":"..."}.
- "rationale_span" must be a verbatim substring from OCR_TEXT for M1/M3; null for M2.
- "overall_confidence" is your aggregate confidence across all predictions.
- "needs_review": true if information is insufficient or if you have very low confidence.
- "review_reason": brief string explaining the review need, or null.
```

---

## Step 2: User Message Template (per meme)

```
POST_ID: {post_id}

OCR_TEXT:
{reconstructed_text}

CAPTION:
{caption}

ALT_TEXT:
{fb_alt_text}
```

> [!TIP]
> Keep the `POST_ID` in the user message so the model echoes it back in the JSON, making it easy to insert into the DB without tracking state separately.

---

## Step 3: Python Starter Script

This script pulls memes from your DB, calls GPT, and stores the raw output:

```python
# annotate_with_gpt.py
import sqlite3
import json
import os
from openai import OpenAI

# --- Config ---
DB_PATH = "propaganda_dataset.db"
MODEL = "gpt-4o"
PROMPT_VERSION = "v1.0"
TEMPERATURE = 0.3   # low for structured output; raise to 0.7 for multi-sample runs
N_RUNS = 1          # set to 3–5 for uncertainty scoring (Phase 2.1)

SYSTEM_PROMPT = """<paste your system prompt here>"""

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

def get_unprocessed_posts(conn, limit=5):
    """Get posts not yet pre-annotated."""
    cur = conn.cursor()
    cur.execute("""
        SELECT p.post_id, p.caption,
               i.image_id, i.reconstructed_text, i.fb_alt_text
        FROM POST p
        LEFT JOIN IMAGE i ON p.post_id = i.post_id
        WHERE p.post_id NOT IN (
            SELECT DISTINCT post_id FROM LLM_PREANNOTATION
        )
        LIMIT ?
    """, (limit,))
    return cur.fetchall()

def build_user_message(post_id, reconstructed_text, caption, fb_alt_text):
    return f"""POST_ID: {post_id}

OCR_TEXT:
{reconstructed_text or '(no OCR text available)'}

CAPTION:
{caption or '(no caption)'}

ALT_TEXT:
{fb_alt_text or '(no alt text)'}"""

def call_gpt(user_message, run_id):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ],
        temperature=TEMPERATURE,
        response_format={"type": "json_object"}  # enforces JSON output
    )
    return response.choices[0].message.content

def store_preannotation(conn, post_id, image_id, run_id, raw_json):
    cur = conn.cursor()
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError:
        print(f"  [!] JSON parse error for {post_id} run {run_id}")
        return

    for item in data.get("labels", []):
        cur.execute("""
            INSERT INTO LLM_PREANNOTATION
              (post_id, image_id, model_name, prompt_version, run_id,
               predicted_label, modality, confidence_score,
               rationale_span, reasoning, raw_response)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            post_id, image_id, MODEL, PROMPT_VERSION, run_id,
            item.get("label"),
            item.get("modality"),
            item.get("confidence_score"),
            item.get("rationale_span"),
            item.get("reasoning"),
            raw_json
        ))
    conn.commit()

def main():
    conn = sqlite3.connect(DB_PATH)
    posts = get_unprocessed_posts(conn, limit=10)
    print(f"Processing {len(posts)} posts...")

    for post_id, caption, image_id, reconstructed_text, fb_alt_text in posts:
        user_msg = build_user_message(post_id, reconstructed_text, caption, fb_alt_text)
        for run_id in range(1, N_RUNS + 1):
            print(f"  → {post_id[:30]}... run {run_id}/{N_RUNS}")
            raw = call_gpt(user_msg, run_id)
            store_preannotation(conn, post_id, image_id, run_id, raw)

    conn.close()
    print("Done.")

if __name__ == "__main__":
    main()
```

---

## Step 4: Confidence Tiering (after N_RUNS > 1)

After running 3–5 times per meme, compute label consistency to assign a tier:

```python
# confidence_tier.py
import sqlite3
from collections import Counter

def compute_tiers(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Get all post_ids with multiple runs
    cur.execute("""
        SELECT post_id, predicted_label, COUNT(*) as votes
        FROM LLM_PREANNOTATION
        GROUP BY post_id, predicted_label
    """)
    rows = cur.fetchall()

    # Group by post
    from collections import defaultdict
    post_votes = defaultdict(list)
    for post_id, label, votes in rows:
        post_votes[post_id].append((label, votes))

    for post_id, votes in post_votes.items():
        total_runs = sum(v for _, v in votes)
        top_label, top_count = max(votes, key=lambda x: x[1])
        agreement_ratio = top_count / total_runs

        if agreement_ratio >= 0.8:
            tier = "HIGH"
        elif agreement_ratio >= 0.6:
            tier = "MEDIUM"
        else:
            tier = "LOW"

        print(f"{post_id[:30]:35} | {top_label} ({top_count}/{total_runs}) | Tier: {tier}")

    conn.close()

compute_tiers("propaganda_dataset.db")
```

| Agreement Ratio | Tier | Human Action |
|---|---|---|
| ≥ 80% | **HIGH** | Random spot-check 5–10% |
| 60–79% | **MEDIUM** | Single expert verification |
| < 60% | **LOW** | Dual expert + adjudication |

---

## Step 5: Prompt Iteration Strategy

Follow this loop as you discover failure modes:

```
v1.0 → Pilot run on 10–20 memes
         ↓
     Review outputs manually
         ↓
  Identify failure patterns:
  - GPT confusing T01 vs T02?
  - Missing sarcasm?
  - Wrong modality for visual-only memes?
         ↓
  Add 2–3 few-shot examples to system prompt
         ↓
         v1.1
         ↓
  Repeat until precision/recall acceptable
```

### Few-Shot Example Block (add to System Prompt)

```
## FEW-SHOT EXAMPLES

### Example 1 — Name Calling (T02)
OCR_TEXT: "এই দালাল সরকার দেশ বেচে দিচ্ছে"
Expected output:
{
  "labels": [{"label":"T02","modality":"M1","confidence_score":0.95,
               "rationale_span":"দালাল সরকার","reasoning":"Direct derogatory label applied to target group."}],
  "overall_confidence": 0.95, "needs_review": false, "review_reason": null
}

### Example 2 — No Propaganda (T08)
OCR_TEXT: "আজ সংসদে নতুন বাজেট পেশ হয়েছে।"
Expected output:
{
  "labels": [{"label":"T08","modality":"M1","confidence_score":0.9,
               "rationale_span":null,"reasoning":"Neutral factual reporting of parliamentary event."}],
  "overall_confidence": 0.9, "needs_review": false, "review_reason": null
}

### Example 3 — Multimodal (T04, M3)
OCR_TEXT: "ওরা ক্ষমতায় এলে দেশে আর মসজিদ থাকবে না!"
ALT_TEXT: "Burning building with crowd"
Expected output:
{
  "labels": [{"label":"T04","modality":"M3","confidence_score":0.91,
               "rationale_span":"দেশে আর মসজিদ থাকবে না",
               "reasoning":"Fear/prejudice constructed by combining threat text with burning building image."}],
  "overall_confidence": 0.91, "needs_review": false, "review_reason": null
}
```

---

## Step 6: Model Choice Recommendations

| Use Case | Recommended Model |
|---|---|
| Best accuracy (multimodal) | **gpt-4o** (can also take the image directly) |
| Cost-efficient text-only | **gpt-4o-mini** |
| Multi-model ensemble (Phase 2.2) | GPT-4o + Claude 3.5 Sonnet |
| Structured JSON output | Use `response_format={"type": "json_object"}` |

> [!TIP]
> Since your images are stored locally at `IMAGE.file_path`, you can pass images **directly** to `gpt-4o` using the Vision API (`content: [{"type":"image_url",...}]`). This lets the model evaluate M2/M3 without relying solely on `fb_alt_text`. This is the recommended approach for multimodal memes.

---

## Immediate Next Steps

1. **[ ]** Run the `CREATE TABLE` SQL to add `LLM_PREANNOTATION` and `ANNOTATION` to your DB.
2. **[ ]** Set `OPENAI_API_KEY` as an environment variable.
3. **[ ]** Paste the System Prompt (Step 1) into `annotate_with_gpt.py`.
4. **[ ]** Run on 10–20 memes with `N_RUNS=1` to sanity-check output quality.
5. **[ ]** Review the JSON outputs manually against the codebook.
6. **[ ]** Add 2–3 few-shot examples based on any errors found (Step 5).
7. **[ ]** Switch to `N_RUNS=3` for uncertainty scoring on the full batch.
8. **[ ]** Compute confidence tiers using the tiering script (Step 4).
9. **[ ]** Begin human verification, starting with LOW-tier items.

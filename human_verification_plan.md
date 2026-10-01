# Human Verification Plan
## LLM Pre-Annotation to Human-Verified Ground Truth

---

## Why We Need Human Verification

The LLM (annotate_ollama.py) has already run over all posts and stored its predictions in the LLM_PREANNOTATION table. These predictions are **not ground truth.** They are educated first-guesses by a language model.

### The Problem with Raw LLM Annotations

| LLM Error Type | Example |
|---|---|
| Hallucinated Confidence | Model says confidence=0.92 but the reasoning is wrong |
| Literal misreading | Model reads Bangla sarcasm as sincere |
| Code-switching confusion | Banglish misidentified or mislabeled |
| Technique conflation | Confuses T01 (Loaded Language) with T07 (Appeal to Strong Emotions) |
| Span boundary errors | Identifies the wrong words as the evidence span |
| Modality errors | Assigns M1 (text-only) when the propaganda is in the image |
| Systematic bias | Consistently over-labels T04 (Fear) for government-critical content |

**Rule:** LLM predictions stored in LLM_PREANNOTATION are inputs for human annotators, not the final dataset.

---

## What the Verification Process Produces

Every verified post writes its output into the ANNOTATION table, which becomes the ground truth of the dataset.

`
LLM_PREANNOTATION (raw prediction)
        |
        v
Human Annotator reviews
        |
        v
ANNOTATION table (verified ground truth)
        |
   |-- verification_status = VERIFIED  (accepted or corrected)
   |-- verification_status = REJECTED  (completely wrong, human re-labelled)
   -- verification_status = PENDING   (not yet reviewed)
`

---

## Verification Overview: 3-Tier System

Based on LLM confidence and consistency, each post falls into one of three tiers:

`
               ALL POSTS
                  |
      .-----------+-----------.
      |           |           |
   TIER 1      TIER 2      TIER 3
   HIGH        MEDIUM        LOW
 CONFIDENCE  CONFIDENCE  CONFIDENCE
      |           |           |
  Spot-check  1 Annotator  2 Annotators
  (10-15%)    reviews     review + discuss
`

---

## Step-by-Step Verification Process

### Step 1: Generate the Review Queue

`ash
# See all posts that need human review
python view_results.py --review-queue

# Full annotation summary by label
python view_results.py --summary

# Filter by specific model
python view_results.py --model qwen2.5:3b --review-queue

# Lower confidence threshold (flag more posts)
python view_results.py --conf-threshold 0.70 --review-queue
`

A post is automatically placed in the review queue if ANY of these are true:

| Auto-Flag Condition | Why It Matters |
|---|---|
| needs_review = 1 | The model itself was uncertain |
| confidence_score < 0.65 | Borderline prediction |
| Only T08 predicted but long OCR text exists | Possible false negative |
| T08 mixed with other techniques | Codebook violation - T08 is mutually exclusive |
| Multiple runs produced different labels | Model self-inconsistency |

---

### Step 2: Review Each Post (The Annotator's Job)

#### 2.1 Read the Full Context
1. Meme image - what is visually shown?
2. OCR text - what words does the meme contain?
3. Post caption - what did the page author write?
4. LLM Rationale - what did the model say and why?

#### 2.2 Apply the Codebook Decision Tree

`
START
  |
  v
Is there enough image/text to judge?
  |-- NO  -> Mark NEEDS_REVIEW
  |
  v
Does the meme use a manipulative technique?
  |-- NO  -> ONLY T08 (No Propaganda)
  |
  v
Evaluate each technique independently:
  |-- T01: Loaded Language?
  |-- T02: Name Calling?
  |-- T03: Smears?
  |-- T04: Appeal to Fear?
  |-- T05: Exaggeration?
  |-- T06: Slogans?
  -- T07: Appeal to Emotions?
`

#### 2.3 Decision Actions

| Action | When to Use | DB Result |
|---|---|---|
| ACCEPT | LLM label, span, modality all correct | ANNOTATION with verification_status=VERIFIED, source=llm_preannotated_human_verified |
| EDIT | Correct technique, wrong span/modality | ANNOTATION with corrections, status=VERIFIED |
| REJECT + RELABEL | Completely wrong label | Correct labels to ANNOTATION, source=human |
| REJECT + T08 | LLM found propaganda but there is none | T08 to ANNOTATION, source=human |
| NEEDS_REVIEW | Cannot judge (bad image, no text) | status=PENDING, escalate |

---

### Step 3: Tier-Based Review Depth

#### Tier 1: High Confidence (Spot-Check 10-15%)
Criteria: confidence_score >= 0.85, needs_review = 0, all runs agreed.
- Human randomly samples 10-15%.
- Fast review: check label + rationale span only.
- If error rate > 5%: escalate rest to Tier 2.
- Goal: Catch systematic LLM bias even when confident.

#### Tier 2: Medium Confidence (Full Single-Expert Review)
Criteria: 0.65 <= confidence_score < 0.85.
- One annotator reads full context and decides (ACCEPT / EDIT / REJECT).
- Uses codebook strictly.
- Goal: Correct borderline cases.

#### Tier 3: Low Confidence / Disagreement (Dual-Expert + Adjudication)
Criteria: confidence_score < 0.65 OR needs_review = 1 OR inconsistent runs.
- Two independent annotators review the same post separately.
- If they agree: write to ANNOTATION, adjudication_status = AGREED.
- If they disagree: escalate to senior annotator -> ADJUDICATED.
- Goal: Maximum scrutiny on the hardest cases.

---

### Step 4: What the Annotator Writes

For every verified post, fill the ANNOTATION table:

| Field | What to Fill |
|---|---|
| post_id | Same post ID |
| technique_label | Final verified code (T01-T08) |
| modality | M1 (Text), M2 (Image), M3 (Both) |
| start_char / end_char | Character offset in reconstructed_text |
| evidence_span | Exact text proving the technique |
| annotation_source | llm_preannotated_human_verified or human |
| verification_status | VERIFIED or PENDING |
| human_annotator_id | Who verified (e.g., omor, mehedi) |
| adjudication_status | NONE, AGREED, or ADJUDICATED |
| llm_preannotation_id | FK to original LLM prediction |

---

### Step 5: Inter-Annotator Agreement (IAA)

Measure after every batch using Cohen's Kappa:

| Kappa Value | Interpretation | Action |
|---|---|---|
| < 0.40 | Poor | Stop batch, review codebook, retrain annotators |
| 0.40 - 0.60 | Moderate | Identify patterns, refine boundary rules |
| 0.60 - 0.80 | Substantial | Acceptable, continue with adjudication |
| >= 0.80 | Near-perfect | Strong, proceed confidently |

Track separately for: Label agreement, Span agreement, Modality agreement.

---

### Step 6: Error Analysis and Prompt Improvement Loop

`
Batch Annotated
      |
      v
Analyze LLM errors (where humans rejected/edited)
      |
      v
Identify failure pattern:
  |-- Sarcasm misread?      -> Add example to prompt
  |-- Banglish confusion?   -> Add Banglish examples to prompt
  |-- Span boundary wrong?  -> Tighten span instruction
  -- Wrong technique?      -> Add negative examples to codebook
      |
      v
Update annotate_ollama.py prompt
      |
      v
Run next batch with improved prompt
`

---

## Annotation Tool Options

### Option 1: Label Studio (Recommended)
Free, open-source annotation platform at labelstud.io.
- Displays meme image + OCR text side-by-side.
- Supports span-level labeling in text.
- Tracks annotator IDs.
- Exports JSON/CSV to import back into propaganda_dataset.db.

Workflow:
1. Export posts from propaganda_dataset.db to JSON.
2. Import into Label Studio with LLM predictions as pre-filled suggestions.
3. Annotators review and approve/edit/reject.
4. Export verified labels.
5. Write final labels back into ANNOTATION table.

### Option 2: Custom verify_annotation.py Script
A lightweight terminal script that:
- Shows one post at a time (image path, OCR text, LLM prediction).
- Prompts for ACCEPT / EDIT / REJECT.
- Writes directly to ANNOTATION table.

---

## Dataset Splits After Verification

`
All Verified Posts
        |
   .----+--------------------.
   |                         |
TRAINING SET            TEST / GOLD SET
(70-80%)                (20-30%)
   |                         |
LLM preannotated        100% human-annotated
+ human verified        or human-verified ONLY
(acceptable)            (NO unverified LLM labels)
`

CRITICAL: The test set must contain zero unverified LLM labels.
Evaluating a trained model against labels from another model is circular and scientifically invalid.

---

## Quick Reference: Who Does What

| Role | Task |
|---|---|
| LLM (automated) | Generates first-pass predictions, stored in LLM_PREANNOTATION |
| Tier 1 Annotator | Spot-checks high-confidence posts (10-15%), catches systematic bias |
| Tier 2 Annotator | Full review of medium-confidence posts, ACCEPT/EDIT/REJECT |
| Tier 3 Annotator A | Independent review of uncertain/flagged posts |
| Tier 3 Annotator B | Independent review of same posts as Annotator A |
| Senior Adjudicator | Resolves Tier 3 disagreements, makes final binding decision |
| Project Lead | Measures IAA after each batch, updates codebook and LLM prompt |

---

## Summary: Why This Works

| Problem | Solution |
|---|---|
| LLM is wrong or overconfident | Human verification catches errors before they enter ground truth |
| Manual annotation is too slow | LLM pre-fills 80%+ of labels, human only accepts/edits |
| Inconsistent annotators | IAA measurement and codebook anchor consistency |
| Hard edge cases missed | Tier 3 dual-expert + adjudication |
| LLM improves over time | Error analysis feeds back into prompt refinement |
| Dataset quality is auditable | Provenance fields in ANNOTATION track every decision |

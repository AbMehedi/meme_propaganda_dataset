# Human Verification Plan (UI-Based)
## LLM Pre-Annotation + Non-Technical Human Verification via Web Interface

---

## Why We Need Human Verification

The LLM (annotate_ollama.py) already labeled all posts and stored them in LLM_PREANNOTATION.
These are first-guess labels — NOT final ground truth. Humans must verify them because:

- LLMs misread Bangla sarcasm as sincere
- LLMs confuse similar techniques (T01 vs T07)
- LLMs mark wrong evidence spans
- LLMs cannot see the image — they miss visual propaganda
- LLMs can be confidently wrong

**Why a UI (not CLI)?**
Annotators are linguists, Bangla speakers, and domain experts — not programmers.
They need a web page in a browser. Nothing more.

---

## Big Picture: How It Works

```
[LLM runs annotate_ollama.py]
           |
           v
[LLM_PREANNOTATION table in SQLite DB]
           |
           v
[Flask Web App served at http://localhost:5000]
           |
    .------+------.
    |              |
[Annotator A]  [Annotator B]
opens browser  opens browser
    |              |
sees meme + OCR + AI prediction
    |              |
clicks ACCEPT / EDIT / REJECT
    |              |
    v              v
[ANNOTATION table — final ground truth]
```

---

## What an Annotator Sees (One Post at a Time)

```
+------------------------------------------------------------------+
|  POST 42 of 200          [<< PREV]              [NEXT >>]       |
|  Confidence: HIGH                          [omor] [logout]      |
+------------------------------------------------------------------+
|                                                                  |
|  +--------------------+   OCR TEXT:                             |
|  |                    |   এই দালাল সরকার দেশ বেচে দিচ্ছে       |
|  |   [MEME IMAGE]     |                                         |
|  |                    |   POST CAPTION:                         |
|  +--------------------+   শেয়ার করুন সবাই জানুক                |
|                                                                  |
+------------------------------------------------------------------+
|  AI PREDICTION:                                                  |
|  Technique : T02 - Name Calling / Labeling                      |
|  Evidence  : "দালাল সরকার"                                      |
|  Confidence: 0.91                                               |
|  AI Reason : Derogatory label applied to government as target.  |
+------------------------------------------------------------------+
|  YOUR DECISION:                                                  |
|                                                                  |
|    [ ACCEPT ]    [ EDIT ]    [ REJECT ]    [ SKIP ]             |
|                                                                  |
+------------------------------------------------------------------+
```

No terminal. No code. Just read and click.

---

## Annotator Decision Guide

| Button | When to Click | What Happens |
|--------|--------------|--------------|
| ACCEPT | AI label, span, and modality are all correct | Saved as verified |
| EDIT | Correct technique but wrong span or modality | Edit form appears — fix and submit |
| REJECT | AI is completely wrong | Relabel form appears — pick correct label |
| SKIP | Too blurry, no text, cannot judge | Flagged for senior review |

### If EDIT is clicked, the annotator sees:
- Technique dropdown (T01 to T08)
- Text input to correct the evidence span
- Radio buttons: Text-only / Image-only / Both

### If REJECT is clicked, same form but all blank — annotator labels from scratch.

---

## Simplified Workflow (Step by Step)

```
STEP 1: Project lead starts the server
        docker compose up -d
        OR: python annotation_ui/app.py

STEP 2: Project lead shares URL with team
        http://localhost:5000

STEP 3: Annotator opens URL in browser
        Logs in with their name (e.g. "mehedi")

STEP 4: See a meme post
        Image on left, OCR text and AI prediction on right

STEP 5: Read the AI reasoning
        Does the AI make sense?

STEP 6: Click ACCEPT / EDIT / REJECT / SKIP

STEP 7: Automatically moves to next post
        Progress bar: 42 / 200 done

STEP 8: Done for the day — just close the browser
        Progress is saved automatically
```

---

## The 3 Review Tiers (Handled Automatically by the UI)

Annotators do NOT need to know about tiers. The UI handles assignment.

| Badge Color | Tier | Criteria | Who Reviews |
|-------------|------|----------|-------------|
| GREEN | High Confidence | confidence >= 0.85 | Random 10-15% spot-check only |
| YELLOW | Medium Confidence | 0.65 <= confidence < 0.85 | Every annotator sees and decides |
| RED | Needs Review | confidence < 0.65 or needs_review=1 | 2 annotators assigned independently |

For RED posts, both annotators review the same post without seeing each other's answer.
If they agree — done. If they disagree — senior adjudicator sees both answers and decides.

---

## Adjudication (When Annotators Disagree)

The senior reviewer has a special view showing:

```
+------------------------------------------------------------------+
|  POST #87 — DISAGREEMENT                                        |
+------------------------------------------------------------------+
|  [MEME IMAGE]   OCR: "তোর বাপ চোর..."                          |
+------------------------------------------------------------------+
|  Annotator A (omor):     T03 - Smears                           |
|  Evidence span: "তোর বাপ চোর"                                  |
|  Reason: Damaging claim about family member                      |
|                                                                  |
|  Annotator B (mehedi):   T02 - Name Calling                     |
|  Evidence span: "তোর বাপ"                                       |
|  Reason: Derogatory labeling of a person                        |
+------------------------------------------------------------------+
|  SENIOR DECISION:                                               |
|  [ T01 ] [ T02 ] [ T03 ] [ T04 ] [ T05 ] [ T06 ] [ T07 ] [T08]|
|  Evidence span: [________________]                              |
|  [ SUBMIT FINAL DECISION ]                                      |
+------------------------------------------------------------------+
```

---

## Admin Dashboard (Project Lead Only)

Accessible at http://localhost:5000/admin

Shows:
- Total posts: 200 | Verified: 142 (71%) | Pending: 58
- Posts needing adjudication: 7
- Per-annotator progress (who reviewed how many)
- Label distribution (how many T01, T02, T03...)
- LLM accuracy: what % the AI got right vs human
- IAA score (Cohen Kappa — annotator agreement)
- Export button: download final ANNOTATION as CSV or JSON

---

## What to Build: Flask + Vanilla JS

```
annotation_ui/
  app.py              <- Flask backend
    - GET  /          : login page
    - GET  /annotate  : fetch next post for this annotator
    - POST /submit    : save ACCEPT/EDIT/REJECT to ANNOTATION table
    - GET  /admin     : dashboard
    - GET  /adjudicate: adjudication queue for senior reviewer

  templates/
    login.html        <- Name/ID entry, no password needed
    annotate.html     <- Main page: image + OCR + AI prediction + buttons
    adjudicate.html   <- Side-by-side disagreement view
    admin.html        <- Progress dashboard

  static/
    style.css         <- Clean readable styling
    annotate.js       <- ACCEPT/EDIT/REJECT button logic
```

Database reads from: LLM_PREANNOTATION, POST, IMAGE, OCR_WORD
Database writes to:  ANNOTATION

---

## Implementation Phases

### Phase 1 — Core Annotation (Week 1)
- [ ] Flask app.py with login and annotation routes
- [ ] annotate.html showing image, OCR, AI prediction, and 4 buttons
- [ ] Submit ACCEPT writes directly to ANNOTATION table
- [ ] Submit REJECT/EDIT shows inline form and saves corrections
- [ ] Progress tracking (posts done per annotator)

### Phase 2 — Adjudication (Week 2)
- [ ] Tier 3 logic: assign same post to two annotators
- [ ] Detect disagreements after both submit
- [ ] adjudicate.html: senior reviewer side-by-side view
- [ ] Write final adjudicated decision to ANNOTATION

### Phase 3 — Dashboard and Export (Week 3)
- [ ] admin.html: live progress, label distribution, IAA score
- [ ] Export ANNOTATION to CSV and JSON
- [ ] Add annotation_ui as a Docker service in docker-compose.yml

---

## What Already Exists vs What to Build

| Component | Status |
|-----------|--------|
| LLM predictions (annotate_ollama.py) | DONE |
| LLM_PREANNOTATION table | DONE — has data |
| ANNOTATION table schema | DONE — migrate_db.py created it |
| view_results.py (CLI only) | DONE — but CLI, not for non-technical users |
| annotation_ui/app.py | TO BUILD |
| annotation_ui/templates/ | TO BUILD |
| Admin dashboard | TO BUILD |
| Docker service for annotation_ui | TO BUILD |

---

## Final Summary

```
[DONE]  LLM labeled all posts -> stored in LLM_PREANNOTATION

[BUILD] Flask web app at http://localhost:5000

[DONE]  ANNOTATION table schema ready to receive verified labels

ANNOTATOR FLOW (no technical knowledge needed):
  Open browser -> Log in -> See meme -> Click ACCEPT/EDIT/REJECT -> Done

PROJECT LEAD FLOW:
  Check admin dashboard -> Export final verified CSV when complete

OUTPUT:
  ANNOTATION table = final human-verified ground truth
  Ready for model training and evaluation
```

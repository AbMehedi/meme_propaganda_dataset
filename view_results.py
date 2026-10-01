"""
view_results.py — Review LLM pre-annotation results from the DB.
Usage:
    py -3 view_results.py                # show all results, grouped by post
    py -3 view_results.py --summary      # show summary table only
    py -3 view_results.py --review-queue # show ONLY posts needing human review
    py -3 view_results.py --model qwen2.5:3b  # filter by model
"""
import argparse
import sqlite3
import sys

# Fix Windows console encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DB_PATH = "propaganda_dataset.db"

LABEL_NAMES = {
    "T01": "Loaded Language",
    "T02": "Name Calling",
    "T03": "Smears",
    "T04": "Appeal to Fear/Prejudice",
    "T05": "Exaggeration/Minimisation",
    "T06": "Slogans",
    "T07": "Appeal to Strong Emotions",
    "T08": "No Propaganda",
    "NEEDS_REVIEW": "NEEDS REVIEW",
    "UNKNOWN": "UNKNOWN",
}

# ─────────────────────────────────────────────────────────────────────────────
# HUMAN REVIEW HEURISTICS
# A post is sent to the human review queue if ANY of these are true:
#   1. Model itself set needs_review=1 (explicit model self-flag)
#   2. overall_confidence < threshold (model was globally uncertain)
#   3. All labels are T08 but substantial OCR text is present (possible miss)
#   4. T08 mixed with other labels (codebook violation: T08 must appear alone)
# ─────────────────────────────────────────────────────────────────────────────
CONF_THRESHOLD_DEFAULT = 0.65


def post_needs_human(labels, ocr_text, conf_threshold):
    """Return (needs_human: bool, reasons: list[str])."""
    reasons = []

    # 1. Model explicitly flagged
    flagged = [l for l in labels if l["needs_review"]]
    if flagged:
        model_reasons = "; ".join(
            l["review_reason"] for l in flagged if l["review_reason"]
        )
        reasons.append("Model flagged: " + (model_reasons or "(no reason given)"))

    # 2. Low confidence labels
    low_conf = [l for l in labels if (l["confidence_score"] or 1.0) < conf_threshold]
    if low_conf:
        reasons.append(f"{len(low_conf)} label(s) have confidence < {conf_threshold}")

    # 3. All T08 but rich OCR text present
    all_t08 = all(l["predicted_label"] == "T08" for l in labels)
    has_text = len((ocr_text or "").strip()) >= 10
    if all_t08 and has_text:
        reasons.append("All T08 but OCR text present — possible undetected propaganda")

    # 4. T08 + other labels (codebook violation)
    label_set = {l["predicted_label"] for l in labels}
    if "T08" in label_set and len(label_set) > 1:
        others = ", ".join(sorted(label_set - {"T08"}))
        reasons.append(f"Schema violation: T08 mixed with {others}")

    return bool(reasons), reasons


def main():
    parser = argparse.ArgumentParser(description="View LLM pre-annotation results")
    parser.add_argument("--summary", action="store_true", help="Summary table only")
    parser.add_argument("--review-queue", action="store_true",
                        help="Show ONLY posts that need human review")
    parser.add_argument("--model", default=None,
                        help="Filter by model name (e.g. qwen2.5:3b)")
    parser.add_argument("--conf-threshold", type=float, default=CONF_THRESHOLD_DEFAULT,
                        help=f"Confidence threshold for review queue (default: {CONF_THRESHOLD_DEFAULT})")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    mf_sql = "AND model_name = ?" if args.model else ""
    mf_val = [args.model] if args.model else []

    # ── Summary ──────────────────────────────────────────────────────────────
    cur.execute(f"""
        SELECT predicted_label, COUNT(*) as cnt,
               ROUND(AVG(confidence_score), 3) as avg_conf,
               SUM(needs_review) as needs_review_count
        FROM LLM_PREANNOTATION WHERE 1=1 {mf_sql}
        GROUP BY predicted_label ORDER BY cnt DESC
    """, mf_val)
    summary_rows = cur.fetchall()

    cur.execute(f"SELECT COUNT(DISTINCT post_id) FROM LLM_PREANNOTATION WHERE 1=1 {mf_sql}", mf_val)
    total_posts = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(*) FROM LLM_PREANNOTATION WHERE 1=1 {mf_sql}", mf_val)
    total_labels = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM POST")
    all_posts = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(DISTINCT post_id) FROM LLM_PREANNOTATION WHERE needs_review=1 {mf_sql}", mf_val)
    model_flagged = cur.fetchone()[0]

    sep = "=" * 65
    print(f"\n{sep}")
    model_tag = f"  [model: {args.model}]" if args.model else ""
    print(f"  LLM_PREANNOTATION SUMMARY{model_tag}")
    print(sep)
    print(f"  {'Label':<8} {'Name':<30} {'Count':>6} {'Avg Conf':>9} {'Review':>7}")
    print(f"  {'-'*8} {'-'*30} {'-'*6} {'-'*9} {'-'*7}")
    for r in summary_rows:
        name = LABEL_NAMES.get(r["predicted_label"], r["predicted_label"])
        flag = " ⚠" if r["needs_review_count"] else ""
        print(f"  {r['predicted_label']:<8} {name:<30} {r['cnt']:>6} {r['avg_conf']:>9.3f} {r['needs_review_count']:>7}{flag}")
    print(f"\n  Annotated : {total_labels} label(s) across {total_posts}/{all_posts} posts")
    print(f"  Model flagged needs_review=True : {model_flagged} post(s)")
    print(f"  Review queue threshold (conf)   : < {args.conf_threshold}")
    print(sep)

    if args.summary:
        conn.close()
        return

    # ── Per-post detail ───────────────────────────────────────────────────────
    cur.execute(f"""
        SELECT DISTINCT post_id FROM LLM_PREANNOTATION WHERE 1=1 {mf_sql} ORDER BY post_id
    """, mf_val)
    post_ids = [r[0] for r in cur.fetchall()]

    mode_label = "HUMAN REVIEW QUEUE" if args.review_queue else "PER-POST DETAIL"
    print(f"\n{sep}")
    print(f"  {mode_label}")
    print(sep)

    shown = 0
    for post_id in post_ids:
        cur.execute("SELECT caption FROM POST WHERE post_id=?", (post_id,))
        cap_row = cur.fetchone()
        caption = (cap_row["caption"] or "") if cap_row else ""

        cur.execute("SELECT reconstructed_text FROM IMAGE WHERE post_id=?", (post_id,))
        ocr_rows = cur.fetchall()
        ocr = " | ".join(
            (r["reconstructed_text"] or "").strip()
            for r in ocr_rows if r["reconstructed_text"]
        )

        cur.execute(f"""
            SELECT predicted_label, modality, confidence_score,
                   rationale_span, reasoning, needs_review, review_reason,
                   overall_confidence, model_name
            FROM LLM_PREANNOTATION
            WHERE post_id=? {mf_sql}
            ORDER BY confidence_score DESC
        """, [post_id] + mf_val)
        labels = cur.fetchall()

        needs_human, reasons = post_needs_human(labels, ocr, args.conf_threshold)

        if args.review_queue and not needs_human:
            continue

        shown += 1
        review_tag = "  🔴 HUMAN REVIEW" if needs_human else ""
        print(f"\n  POST: {post_id[:50]}...{review_tag}")
        if ocr:
            print(f"  OCR:  {ocr[:100]}")
        if caption:
            print(f"  CAP:  {caption[:100]}")
        if needs_human:
            for reason in reasons:
                print(f"  ⚠  {reason}")

        for lbl in labels:
            name = LABEL_NAMES.get(lbl["predicted_label"], lbl["predicted_label"])
            conf = lbl["confidence_score"] or 0.0
            low_marker = " ❗low" if conf < args.conf_threshold else ""
            model_tag = f" [{lbl['model_name']}]" if not args.model else ""
            print(f"  ├─ {lbl['predicted_label']} ({name}) | {lbl['modality']} | conf={conf:.2f}{low_marker}{model_tag}")
            if lbl["rationale_span"]:
                print(f"  │    span: \"{lbl['rationale_span']}\"")
            if lbl["reasoning"]:
                print(f"  │    why:  {(lbl['reasoning'] or '')[:120]}")
            if lbl["needs_review"] and lbl["review_reason"]:
                print(f"  │    ⚠ model says: {lbl['review_reason']}")
        print(f"  {'─'*60}")

    if args.review_queue:
        print(f"\n  {shown} post(s) need human review (out of {len(post_ids)} annotated).")
    print()
    conn.close()


if __name__ == "__main__":
    main()



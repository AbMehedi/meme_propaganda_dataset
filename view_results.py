"""
view_results.py — Review LLM pre-annotation results from the DB.
Usage:
    py -3 view_results.py            # show all results, grouped by post
    py -3 view_results.py --summary  # show summary table only
"""
import sqlite3
import sys
import argparse

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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", action="store_true", help="Summary table only")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # ── Summary ──────────────────────────────────────────────────────────────
    cur.execute("""
        SELECT predicted_label, COUNT(*) as cnt,
               ROUND(AVG(confidence_score), 3) as avg_conf,
               SUM(needs_review) as needs_review_count
        FROM LLM_PREANNOTATION
        GROUP BY predicted_label
        ORDER BY cnt DESC
    """)
    rows = cur.fetchall()

    print("\n" + "="*65)
    print(f"  LLM_PREANNOTATION SUMMARY")
    print("="*65)
    print(f"  {'Label':<8} {'Name':<30} {'Count':>6} {'Avg Conf':>9} {'Review':>7}")
    print(f"  {'-'*8} {'-'*30} {'-'*6} {'-'*9} {'-'*7}")
    for r in rows:
        name = LABEL_NAMES.get(r["predicted_label"], r["predicted_label"])
        print(f"  {r['predicted_label']:<8} {name:<30} {r['cnt']:>6} {r['avg_conf']:>9.3f} {r['needs_review_count']:>7}")

    cur.execute("SELECT COUNT(DISTINCT post_id) FROM LLM_PREANNOTATION")
    total_posts = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM LLM_PREANNOTATION")
    total_labels = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM POST")
    all_posts = cur.fetchone()[0]
    print(f"\n  Total: {total_labels} label(s) across {total_posts}/{all_posts} posts annotated")
    print("="*65)

    if args.summary:
        conn.close()
        return

    # ── Per-post detail ───────────────────────────────────────────────────────
    cur.execute("""
        SELECT DISTINCT post_id FROM LLM_PREANNOTATION ORDER BY post_id
    """)
    post_ids = [r[0] for r in cur.fetchall()]

    print("\n" + "="*65)
    print("  PER-POST DETAIL")
    print("="*65)

    for post_id in post_ids:
        # Get post caption
        cur.execute("SELECT caption FROM POST WHERE post_id=?", (post_id,))
        caption_row = cur.fetchone()
        caption = (caption_row["caption"] or "")[:80] if caption_row else ""

        # Get OCR text
        cur.execute("SELECT reconstructed_text FROM IMAGE WHERE post_id=?", (post_id,))
        ocr_row = cur.fetchone()
        ocr = (ocr_row["reconstructed_text"] or "")[:80] if ocr_row else ""

        print(f"\n  POST: {post_id[:40]}...")
        if ocr:
            print(f"  OCR:  {ocr}")
        if caption:
            print(f"  CAP:  {caption}")

        cur.execute("""
            SELECT predicted_label, modality, confidence_score,
                   rationale_span, reasoning, needs_review, review_reason
            FROM LLM_PREANNOTATION
            WHERE post_id=?
            ORDER BY confidence_score DESC
        """, (post_id,))
        labels = cur.fetchall()

        for l in labels:
            name = LABEL_NAMES.get(l["predicted_label"], l["predicted_label"])
            review_flag = " ⚠ NEEDS REVIEW" if l["needs_review"] else ""
            print(f"  ├─ {l['predicted_label']} ({name}) | {l['modality']} | conf={l['confidence_score']:.2f}{review_flag}")
            if l["rationale_span"]:
                print(f"  │    span: \"{l['rationale_span']}\"")
            if l["reasoning"]:
                print(f"  │    why:  {l['reasoning'][:120]}")
            if l["review_reason"]:
                print(f"  │    ⚠ reason: {l['review_reason']}")
        print(f"  {'─'*60}")

    conn.close()

if __name__ == "__main__":
    main()

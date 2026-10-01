import os
import sqlite3
import sys

from flask import (
    Flask,
    abort,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

# Ensure UTF-8 output on Windows console to prevent charmap encoding errors
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Base paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DB_PATH = os.path.join(PROJECT_ROOT, "propaganda_dataset.db")
RAW_IMAGES_DIR = os.path.join(PROJECT_ROOT, "raw_images")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "bangla-meme-propaganda-secret-key-2026")

# Taxonomy & Labels
TECHNIQUES = {
    "T01": {"code": "T01", "name": "Loaded Language", "desc": "Emotionally charged words provoking approval/disapproval"},
    "T02": {"code": "T02", "name": "Name Calling / Labeling", "desc": "TARGET + DEROGATORY LABEL explicitly present"},
    "T03": {"code": "T03", "name": "Smears", "desc": "TARGET + SPECIFIC NEGATIVE CLAIM + REPUTATIONAL DAMAGE"},
    "T04": {"code": "T04", "name": "Appeal to Fear / Prejudice", "desc": "Deliberate THREAT / DANGER / FEAR / PREJUDICE construction"},
    "T05": {"code": "T05", "name": "Exaggeration / Minimisation", "desc": "Substantial overstatement OR downplay of fact/event"},
    "T06": {"code": "T06", "name": "Slogans", "desc": "Short rallying phrase substituting for reasoning"},
    "T07": {"code": "T07", "name": "Appeal to Strong Emotions", "desc": "Intense NON-FEAR emotion deliberately provoked"},
    "T08": {"code": "T08", "name": "No Propaganda Technique", "desc": "None of T01-T07 apply"},
}

MODALITIES = {
    "M1": "Text only",
    "M2": "Image only",
    "M3": "Text + Image",
}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_confidence_meta(score, needs_review=False):
    val = score if score is not None else 0.5
    pct = int(val * 100)
    if val >= 0.85:
        tier = "high"
        label = "HIGH CONFIDENCE"
        color = "var(--conf-high)"
        badge_class = "badge-high"
    elif val >= 0.65:
        tier = "mid"
        label = "MED CONFIDENCE"
        color = "var(--conf-mid)"
        badge_class = "badge-mid"
    else:
        tier = "low"
        label = "LOW CONFIDENCE"
        color = "var(--accent)"
        badge_class = "badge-low"

    return {
        "tier": tier,
        "label": label,
        "color": color,
        "badge_class": badge_class,
        "pct": pct,
        "needs_review": bool(needs_review),
    }


@app.context_processor
def inject_global_data():
    annotator_id = session.get("annotator_id")
    verified_count = 0
    total_count = 0
    total_annotated_count = 0
    non_annotated_count = 0
    needs_review_remaining = 0
    pending_adjudication_count = 0
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM LLM_PREANNOTATION")
        total_count = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(DISTINCT llm_preannotation_id) FROM ANNOTATION WHERE verification_status != 'SKIPPED'"
        )
        total_annotated_count = cur.fetchone()[0]
        non_annotated_count = max(0, total_count - total_annotated_count)

        cur.execute(
            """
            SELECT COUNT(*) FROM LLM_PREANNOTATION
            WHERE needs_review = 1
              AND llm_annotation_id NOT IN (
                  SELECT llm_preannotation_id FROM ANNOTATION WHERE verification_status != 'SKIPPED'
              )
            """
        )
        needs_review_remaining = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(DISTINCT llm_preannotation_id) FROM ANNOTATION WHERE adjudication_status = 'PENDING'"
        )
        pending_adjudication_count = cur.fetchone()[0]

        if annotator_id:
            cur.execute(
                "SELECT COUNT(DISTINCT llm_preannotation_id) FROM ANNOTATION WHERE human_annotator_id = ?",
                (annotator_id,),
            )
            verified_count = cur.fetchone()[0]
        conn.close()
    except (sqlite3.Error, OSError) as e:
        app.logger.debug("Database read in inject_global_data: %s", e)
    return {
        "current_annotator": annotator_id,
        "verified_count": verified_count,
        "total_count": total_count,
        "total_annotated_count": total_annotated_count,
        "non_annotated_count": non_annotated_count,
        "needs_review_remaining": needs_review_remaining,
        "pending_adjudication_count": pending_adjudication_count,
        "techniques": TECHNIQUES,
        "modalities": MODALITIES,
    }


# ──────────────────────────────────────────────────────────────────────────────
# ROUTES
# ──────────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if session.get("annotator_id"):
        return redirect(url_for("annotate"))
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM LLM_PREANNOTATION")
    total_predictions = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT llm_preannotation_id) FROM ANNOTATION")
    total_verified = cur.fetchone()[0]
    awaiting_review = max(0, total_predictions - total_verified)
    conn.close()

    return render_template(
        "login.html",
        total_predictions=total_predictions,
        total_verified=total_verified,
        awaiting_review=awaiting_review,
    )


@app.route("/login", methods=["POST"])
def login():
    annotator_name = request.form.get("annotator_id", "").strip().lower()
    if not annotator_name:
        return redirect(url_for("index"))
    session["annotator_id"] = annotator_name
    return redirect(url_for("annotate"))


@app.route("/logout")
def logout():
    session.pop("annotator_id", None)
    return redirect(url_for("index"))


@app.route("/image/<image_id>")
def serve_image(image_id):
    """
    Serve raw image from raw_images/ directory securely.
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT file_path FROM IMAGE WHERE image_id = ?", (image_id,))
    row = cur.fetchone()
    conn.close()

    target_path = None
    if row and row["file_path"]:
        norm = os.path.normpath(os.path.join(PROJECT_ROOT, row["file_path"]))
        if os.path.exists(norm):
            target_path = norm

    # Fallback direct lookup in raw_images/<image_id>.*
    if not target_path:
        for ext in [".jpg", ".jpeg", ".png", ".webp"]:
            candidate = os.path.join(RAW_IMAGES_DIR, f"{image_id}{ext}")
            if os.path.exists(candidate):
                target_path = candidate
                break

    if target_path and os.path.exists(target_path):
        return send_file(target_path)
    
    abort(404, description="Image not found")


@app.route("/annotate")
def annotate():
    annotator_id = session.get("annotator_id")
    if not annotator_id:
        return redirect(url_for("index"))

    req_id = request.args.get("id")
    conn = get_db()
    cur = conn.cursor()

    base_query = """
    SELECT
      llp.llm_annotation_id,
      llp.post_id,
      llp.image_id,
      llp.predicted_label,
      llp.modality,
      llp.confidence_score,
      llp.rationale_span,
      llp.reasoning,
      llp.needs_review,
      llp.review_reason,
      llp.model_name,
      p.caption,
      p.post_url,
      COALESCE(i1.image_id, i2.image_id) AS resolved_image_id,
      COALESCE(i1.file_path, i2.file_path) AS resolved_file_path,
      COALESCE(i1.reconstructed_text, i2.reconstructed_text) AS resolved_reconstructed_text,
      COALESCE(i1.width, i2.width) AS image_width,
      COALESCE(i1.height, i2.height) AS image_height
    FROM LLM_PREANNOTATION llp
    LEFT JOIN POST p ON llp.post_id = p.post_id
    LEFT JOIN IMAGE i1 ON llp.image_id = i1.image_id
    LEFT JOIN (
        SELECT post_id, image_id, file_path, reconstructed_text, width, height
        FROM IMAGE
        GROUP BY post_id
    ) i2 ON (llp.image_id IS NULL AND llp.post_id = i2.post_id)
    """

    item = None
    if req_id:
        # Load specific prediction
        cur.execute(f"{base_query} WHERE llp.llm_annotation_id = ? LIMIT 1", (req_id,))
        row = cur.fetchone()
        if row:
            item = dict(row)
    else:
        # Load lowest confidence prediction that this annotator hasn't yet submitted
        query = f"""
        {base_query}
        LEFT JOIN ANNOTATION a
          ON llp.llm_annotation_id = a.llm_preannotation_id
          AND a.human_annotator_id = ?
        WHERE a.annotation_id IS NULL
        ORDER BY llp.confidence_score ASC, llp.llm_annotation_id ASC
        LIMIT 1;
        """
        cur.execute(query, (annotator_id,))
        row = cur.fetchone()
        if row:
            item = dict(row)

    if not item:
        # Check if there are any remaining at all
        conn.close()
        return render_template("annotate.html", item=None, completed=True)

    # Resolve OCR text fallback if reconstructed_text is missing
    reconstructed = item.get("resolved_reconstructed_text")
    if not reconstructed and item.get("resolved_image_id"):
        cur.execute(
            "SELECT word FROM OCR_WORD WHERE image_id = ? ORDER BY line_id, x1",
            (item["resolved_image_id"],),
        )
        words = [r[0] for r in cur.fetchall() if r[0]]
        if words:
            reconstructed = " ".join(words)
            item["resolved_reconstructed_text"] = reconstructed

    # Calculate previous and next IDs for navigation
    current_id = item["llm_annotation_id"]
    cur.execute(
        "SELECT MAX(llm_annotation_id) FROM LLM_PREANNOTATION WHERE llm_annotation_id < ?",
        (current_id,),
    )
    prev_id = cur.fetchone()[0]

    cur.execute(
        "SELECT MIN(llm_annotation_id) FROM LLM_PREANNOTATION WHERE llm_annotation_id > ?",
        (current_id,),
    )
    next_id = cur.fetchone()[0]

    # Check if this annotator already annotated this specific item
    cur.execute(
        "SELECT * FROM ANNOTATION WHERE llm_preannotation_id = ? AND human_annotator_id = ?",
        (current_id, annotator_id),
    )
    existing_annotation = cur.fetchone()
    if existing_annotation:
        item["existing_decision"] = dict(existing_annotation)

    conn.close()

    conf_meta = get_confidence_meta(item.get("confidence_score"), item.get("needs_review"))
    technique_meta = TECHNIQUES.get(
        item.get("predicted_label"),
        {"code": item.get("predicted_label"), "name": "Unknown Technique", "desc": ""},
    )

    return render_template(
        "annotate.html",
        item=item,
        conf_meta=conf_meta,
        technique_meta=technique_meta,
        prev_id=prev_id,
        next_id=next_id,
        completed=False,
    )


@app.route("/submit", methods=["POST"])
def submit():
    annotator_id = session.get("annotator_id")
    if not annotator_id:
        return redirect(url_for("index"))

    action = request.form.get("action", "").lower()
    llm_annotation_id = request.form.get("llm_annotation_id")
    post_id = request.form.get("post_id")
    image_id = request.form.get("image_id") or None

    if not llm_annotation_id or not post_id:
        return redirect(url_for("annotate"))

    conn = get_db()
    cur = conn.cursor()

    # Fetch original LLM record
    cur.execute(
        "SELECT * FROM LLM_PREANNOTATION WHERE llm_annotation_id = ?",
        (llm_annotation_id,),
    )
    orig = cur.fetchone()
    if not orig:
        conn.close()
        return redirect(url_for("annotate"))

    if action == "accept":
        technique_label = orig["predicted_label"]
        modality = orig["modality"]
        evidence_span = orig["rationale_span"]
        verification_status = "VERIFIED"
        annotation_source = "human_verified"
    elif action == "edit":
        technique_label = request.form.get("technique_label", orig["predicted_label"]).strip()
        modality = request.form.get("modality", orig["modality"]).strip()
        evidence_span = request.form.get("evidence_span", "").strip() or None
        verification_status = "CORRECTED"
        annotation_source = "human_corrected"
    elif action == "reject":
        technique_label = request.form.get("technique_label", "T08").strip()
        modality = request.form.get("modality", orig["modality"]).strip()
        evidence_span = request.form.get("evidence_span", "").strip() or None
        verification_status = "REJECTED"
        annotation_source = "human_rejected"
    elif action == "skip":
        technique_label = orig["predicted_label"]
        modality = orig["modality"]
        evidence_span = orig["rationale_span"]
        verification_status = "SKIPPED"
        annotation_source = "human_skipped"
    else:
        conn.close()
        return redirect(url_for("annotate"))

    # Upsert into ANNOTATION table for this annotator + llm_preannotation_id
    cur.execute(
        """
        SELECT annotation_id FROM ANNOTATION
        WHERE llm_preannotation_id = ? AND human_annotator_id = ?
        """,
        (llm_annotation_id, annotator_id),
    )
    existing = cur.fetchone()

    if existing:
        cur.execute(
            """
            UPDATE ANNOTATION
            SET technique_label = ?,
                modality = ?,
                evidence_span = ?,
                annotation_source = ?,
                verification_status = ?,
                created_at = datetime('now')
            WHERE annotation_id = ?
            """,
            (
                technique_label,
                modality,
                evidence_span,
                annotation_source,
                verification_status,
                existing["annotation_id"],
            ),
        )
    else:
        cur.execute(
            """
            INSERT INTO ANNOTATION (
                post_id,
                image_id,
                technique_label,
                modality,
                evidence_span,
                annotation_source,
                verification_status,
                human_annotator_id,
                adjudication_status,
                llm_preannotation_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'NONE', ?)
            """,
            (
                post_id,
                image_id,
                technique_label,
                modality,
                evidence_span,
                annotation_source,
                verification_status,
                annotator_id,
                llm_annotation_id,
            ),
        )

    # Disagreement auto-detection across multi-annotator submissions
    cur.execute(
        """
        SELECT COUNT(DISTINCT technique_label), COUNT(DISTINCT human_annotator_id)
        FROM ANNOTATION
        WHERE llm_preannotation_id = ? AND verification_status != 'SKIPPED'
        """,
        (llm_annotation_id,),
    )
    dispute_stats = cur.fetchone()
    if dispute_stats:
        unique_labels, unique_annotators = dispute_stats[0], dispute_stats[1]
        if unique_annotators > 1 and unique_labels > 1:
            cur.execute(
                """
                UPDATE ANNOTATION
                SET adjudication_status = 'PENDING'
                WHERE llm_preannotation_id = ? AND adjudication_status != 'ADJUDICATED'
                """,
                (llm_annotation_id,),
            )
        elif unique_annotators > 1 and unique_labels == 1:
            cur.execute(
                """
                UPDATE ANNOTATION
                SET adjudication_status = 'AGREED'
                WHERE llm_preannotation_id = ? AND adjudication_status = 'PENDING'
                """,
                (llm_annotation_id,),
            )

    conn.commit()
    conn.close()

    # Advance to next unverified item
    return redirect(url_for("annotate"))


@app.route("/history")
def history():
    annotator_id = session.get("annotator_id")
    if not annotator_id:
        return redirect(url_for("index"))

    conn = get_db()
    cur = conn.cursor()

    query = """
    SELECT
      a.annotation_id,
      a.llm_preannotation_id,
      a.post_id,
      a.image_id,
      a.technique_label AS your_label,
      a.modality AS your_modality,
      a.evidence_span,
      a.verification_status,
      a.created_at,
      llp.predicted_label AS ai_label,
      llp.modality AS ai_modality,
      llp.confidence_score,
      llp.needs_review,
      llp.review_reason,
      p.caption,
      COALESCE(i1.image_id, i2.image_id) AS resolved_image_id
    FROM ANNOTATION a
    JOIN LLM_PREANNOTATION llp ON a.llm_preannotation_id = llp.llm_annotation_id
    LEFT JOIN POST p ON a.post_id = p.post_id
    LEFT JOIN IMAGE i1 ON a.image_id = i1.image_id
    LEFT JOIN (
        SELECT post_id, image_id FROM IMAGE GROUP BY post_id
    ) i2 ON (a.image_id IS NULL AND a.post_id = i2.post_id)
    WHERE a.human_annotator_id = ?
    ORDER BY a.created_at DESC
    """
    cur.execute(query, (annotator_id,))
    raw_history = [dict(r) for r in cur.fetchall()]

    # Decorate history items with confidence and technique metadata
    for item in raw_history:
        item["conf_meta"] = get_confidence_meta(item.get("confidence_score"), item.get("needs_review"))
        item["ai_technique"] = TECHNIQUES.get(item.get("ai_label"), {"name": item.get("ai_label", "Unknown")})
        item["your_technique"] = TECHNIQUES.get(item.get("your_label"), {"name": item.get("your_label", "Unknown")})

    # Summary metrics for current annotator
    summary = {
        "all": len(raw_history),
        "verified": sum(1 for h in raw_history if h.get("verification_status") == "VERIFIED"),
        "corrected": sum(1 for h in raw_history if h.get("verification_status") == "CORRECTED"),
        "rejected": sum(1 for h in raw_history if h.get("verification_status") == "REJECTED"),
        "skipped": sum(1 for h in raw_history if h.get("verification_status") == "SKIPPED"),
        "needs_review": sum(1 for h in raw_history if h.get("needs_review") == 1),
    }

    conn.close()

    return render_template(
        "history.html",
        history=raw_history,
        summary=summary,
    )


@app.route("/dataset")
def dataset():
    annotator_id = session.get("annotator_id")
    if not annotator_id:
        return redirect(url_for("index"))

    page = request.args.get("page", 1, type=int)
    active_filter = request.args.get("filter", "all").strip().lower()
    search = request.args.get("search", "").strip()
    sort = request.args.get("sort", "id_asc").strip().lower()
    per_page = 50

    conn = get_db()
    cur = conn.cursor()

    # Summary Counts across entire dataset
    counts_sql = """
    WITH summary_cte AS (
        SELECT
            llp.llm_annotation_id,
            llp.needs_review,
            COUNT(DISTINCT a.annotation_id) AS ann_count
        FROM LLM_PREANNOTATION llp
        LEFT JOIN ANNOTATION a ON a.llm_preannotation_id = llp.llm_annotation_id
        GROUP BY llp.llm_annotation_id
    )
    SELECT
        COUNT(*) AS total_count,
        SUM(CASE WHEN ann_count > 0 THEN 1 ELSE 0 END) AS annotated_count,
        SUM(CASE WHEN ann_count = 0 THEN 1 ELSE 0 END) AS unannotated_count,
        SUM(CASE WHEN needs_review = 1 THEN 1 ELSE 0 END) AS review_count
    FROM summary_cte
    """
    cur.execute(counts_sql)
    c_row = cur.fetchone()
    counts = {
        "total": c_row[0] or 0,
        "annotated": c_row[1] or 0,
        "unannotated": c_row[2] or 0,
        "review": c_row[3] or 0,
    }

    # Base CTE for dataset view
    base_cte = """
    WITH dataset_view AS (
        SELECT
            llp.llm_annotation_id,
            llp.post_id,
            llp.predicted_label,
            llp.confidence_score,
            llp.needs_review,
            llp.review_reason,
            llp.modality,
            p.caption,
            GROUP_CONCAT(DISTINCT a.human_annotator_id) AS annotators,
            GROUP_CONCAT(a.verification_status, ', ') AS statuses,
            COUNT(DISTINCT a.annotation_id) AS annotation_count
        FROM LLM_PREANNOTATION llp
        LEFT JOIN POST p ON llp.post_id = p.post_id
        LEFT JOIN ANNOTATION a ON a.llm_preannotation_id = llp.llm_annotation_id
        GROUP BY llp.llm_annotation_id
    )
    """

    where_clauses = []
    params = []

    if active_filter == "annotated":
        where_clauses.append("annotation_count > 0")
    elif active_filter == "unannotated":
        where_clauses.append("annotation_count = 0")
    elif active_filter == "review":
        where_clauses.append("needs_review = 1")

    if search:
        search_pattern = f"%{search}%"
        where_clauses.append(
            "(CAST(llm_annotation_id AS TEXT) LIKE ? OR post_id LIKE ? OR predicted_label LIKE ? OR caption LIKE ? OR annotators LIKE ?)"
        )
        params.extend([search_pattern, search_pattern, search_pattern, search_pattern, search_pattern])

    where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    # Count filtered rows
    count_query = f"{base_cte} SELECT COUNT(*) FROM dataset_view {where_sql}"
    cur.execute(count_query, params)
    total_filtered = cur.fetchone()[0]

    # Calculate pagination
    total_pages = max(1, (total_filtered + per_page - 1) // per_page)
    current_page = min(max(1, page), total_pages)
    offset = (current_page - 1) * per_page

    # Sort ordering
    if sort == "id_desc":
        order_sql = "ORDER BY llm_annotation_id DESC"
    elif sort == "conf_desc":
        order_sql = "ORDER BY confidence_score DESC, llm_annotation_id ASC"
    elif sort == "conf_asc":
        order_sql = "ORDER BY confidence_score ASC, llm_annotation_id ASC"
    else:  # id_asc default
        order_sql = "ORDER BY llm_annotation_id ASC"

    # Data query
    data_query = f"{base_cte} SELECT * FROM dataset_view {where_sql} {order_sql} LIMIT ? OFFSET ?"
    cur.execute(data_query, params + [per_page, offset])
    raw_rows = [dict(r) for r in cur.fetchall()]

    for r in raw_rows:
        r["conf_meta"] = get_confidence_meta(r.get("confidence_score"), r.get("needs_review"))
        r["technique_name"] = TECHNIQUES.get(r.get("predicted_label"), {}).get("name", "Unknown Technique")
        r["annotator_list"] = [a.strip() for a in (r.get("annotators") or "").split(",") if a.strip()]

    # Generate page window numbers
    page_numbers = []
    if total_pages <= 7:
        page_numbers = list(range(1, total_pages + 1))
    else:
        if current_page <= 4:
            page_numbers = [1, 2, 3, 4, 5, "...", total_pages]
        elif current_page >= total_pages - 3:
            page_numbers = [1, "...", total_pages - 4, total_pages - 3, total_pages - 2, total_pages - 1, total_pages]
        else:
            page_numbers = [1, "...", current_page - 1, current_page, current_page + 1, "...", total_pages]

    start_idx = offset + 1 if total_filtered > 0 else 0
    end_idx = min(offset + per_page, total_filtered)

    conn.close()

    return render_template(
        "dataset.html",
        items=raw_rows,
        counts=counts,
        total_records=counts["total"],
        total_filtered=total_filtered,
        current_page=current_page,
        total_pages=total_pages,
        page_numbers=page_numbers,
        start_idx=start_idx,
        end_idx=end_idx,
        active_filter=active_filter,
        search=search,
        sort=sort,
    )


@app.route("/adjudicate")
def adjudicate():
    annotator_id = session.get("annotator_id")
    if not annotator_id:
        return redirect(url_for("index"))

    tab = request.args.get("tab", "pending").strip().lower()
    conn = get_db()
    cur = conn.cursor()

    # Find pending disputes
    cur.execute("""
        SELECT DISTINCT llm_preannotation_id
        FROM ANNOTATION
        WHERE adjudication_status = 'PENDING'
    """)
    pending_pred_ids = [r[0] for r in cur.fetchall() if r[0] is not None]

    # Find resolved disputes
    cur.execute("""
        SELECT DISTINCT llm_preannotation_id
        FROM ANNOTATION
        WHERE adjudication_status = 'ADJUDICATED'
          AND llm_preannotation_id NOT IN (
              SELECT DISTINCT llm_preannotation_id FROM ANNOTATION WHERE adjudication_status = 'PENDING'
          )
    """)
    resolved_pred_ids = [r[0] for r in cur.fetchall() if r[0] is not None]

    def build_dispute_objects(pred_ids):
        objects = []
        for pid in pred_ids:
            cur.execute("""
                SELECT
                    llp.llm_annotation_id,
                    llp.post_id,
                    llp.image_id,
                    llp.predicted_label,
                    llp.confidence_score,
                    llp.needs_review,
                    llp.reasoning,
                    p.caption,
                    COALESCE(i1.image_id, i2.image_id) AS resolved_image_id,
                    COALESCE(i1.reconstructed_text, i2.reconstructed_text) AS reconstructed_text
                FROM LLM_PREANNOTATION llp
                LEFT JOIN POST p ON llp.post_id = p.post_id
                LEFT JOIN IMAGE i1 ON llp.image_id = i1.image_id
                LEFT JOIN (
                    SELECT post_id, image_id, reconstructed_text FROM IMAGE GROUP BY post_id
                ) i2 ON (llp.image_id IS NULL AND llp.post_id = i2.post_id)
                WHERE llp.llm_annotation_id = ?
            """, (pid,))
            p_row = cur.fetchone()
            if not p_row:
                continue

            obj = dict(p_row)
            obj["conf_meta"] = get_confidence_meta(obj.get("confidence_score"), obj.get("needs_review"))

            # Fetch all annotations for this prediction
            cur.execute("""
                SELECT * FROM ANNOTATION
                WHERE llm_preannotation_id = ? AND verification_status != 'SKIPPED'
                ORDER BY created_at ASC
            """, (pid,))
            all_anns = [dict(a) for a in cur.fetchall()]

            gold_ann = next((a for a in all_anns if a.get("annotation_source") == "gold_adjudicated" or a.get("adjudication_status") == "ADJUDICATED"), None)
            contending = [a for a in all_anns if a.get("annotation_source") != "gold_adjudicated"]

            obj["annotators"] = contending
            obj["gold_annotation"] = gold_ann
            objects.append(obj)
        return objects

    pending_conflicts = build_dispute_objects(pending_pred_ids)
    resolved_conflicts = build_dispute_objects(resolved_pred_ids)
    total_conflicts_count = len(pending_pred_ids) + len(resolved_pred_ids)

    conn.close()

    return render_template(
        "adjudicate.html",
        active_tab=tab,
        pending_conflicts=pending_conflicts,
        resolved_conflicts=resolved_conflicts,
        total_conflicts_count=total_conflicts_count,
    )


@app.route("/adjudicate/resolve", methods=["POST"])
def resolve_adjudication():
    annotator_id = session.get("annotator_id")
    if not annotator_id:
        return redirect(url_for("index"))

    llm_annotation_id = request.form.get("llm_annotation_id")
    gold_label = request.form.get("gold_label")
    modality = request.form.get("modality", "M1")
    evidence_span = request.form.get("evidence_span", "").strip() or None
    adjudication_notes = request.form.get("adjudication_notes", "").strip()

    if not llm_annotation_id or not gold_label:
        return redirect(url_for("adjudicate"))

    if adjudication_notes:
        app.logger.info("Adjudication notes for pred #%s: %s", llm_annotation_id, adjudication_notes)

    conn = get_db()
    cur = conn.cursor()

    # 1. Update existing conflicting annotations to ADJUDICATED
    cur.execute(
        """
        UPDATE ANNOTATION
        SET adjudication_status = 'ADJUDICATED'
        WHERE llm_preannotation_id = ?
        """,
        (llm_annotation_id,),
    )

    # 2. Get post_id and image_id
    cur.execute(
        "SELECT post_id, image_id FROM LLM_PREANNOTATION WHERE llm_annotation_id = ?",
        (llm_annotation_id,),
    )
    orig = cur.fetchone()
    if orig:
        cur.execute(
            """
            SELECT annotation_id FROM ANNOTATION
            WHERE llm_preannotation_id = ? AND annotation_source = 'gold_adjudicated'
            """,
            (llm_annotation_id,),
        )
        existing_gold = cur.fetchone()

        if existing_gold:
            cur.execute(
                """
                UPDATE ANNOTATION
                SET technique_label = ?,
                    modality = ?,
                    evidence_span = ?,
                    human_annotator_id = ?,
                    verification_status = 'VERIFIED',
                    adjudication_status = 'ADJUDICATED',
                    created_at = datetime('now')
                WHERE annotation_id = ?
                """,
                (gold_label, modality, evidence_span, annotator_id, existing_gold["annotation_id"]),
            )
        else:
            cur.execute(
                """
                INSERT INTO ANNOTATION (
                    post_id,
                    image_id,
                    technique_label,
                    modality,
                    evidence_span,
                    annotation_source,
                    verification_status,
                    human_annotator_id,
                    adjudication_status,
                    llm_preannotation_id,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, 'gold_adjudicated', 'VERIFIED', ?, 'ADJUDICATED', ?, datetime('now'))
                """,
                (
                    orig["post_id"],
                    orig["image_id"],
                    gold_label,
                    modality,
                    evidence_span,
                    annotator_id,
                    llm_annotation_id,
                ),
            )

    conn.commit()
    conn.close()

    return redirect(url_for("adjudicate", tab="resolved"))



@app.route("/admin")
def admin():
    """Dataset Status and Administrator Dashboard."""
    conn = get_db()
    cur = conn.cursor()

    # Total LLM predictions
    cur.execute("SELECT COUNT(*) FROM LLM_PREANNOTATION")
    total_preds = cur.fetchone()[0]

    # Human annotated (non-skipped)
    cur.execute("SELECT COUNT(DISTINCT llm_preannotation_id) FROM ANNOTATION WHERE verification_status != 'SKIPPED'")
    total_annotated = cur.fetchone()[0]

    # Non-annotated remaining
    total_non_annotated = max(0, total_preds - total_annotated)

    # Needs review overall and remaining
    cur.execute("SELECT COUNT(*) FROM LLM_PREANNOTATION WHERE needs_review = 1")
    total_needs_review = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) FROM LLM_PREANNOTATION
        WHERE needs_review = 1
          AND llm_annotation_id NOT IN (
              SELECT llm_preannotation_id FROM ANNOTATION WHERE verification_status != 'SKIPPED'
          )
    """)
    needs_review_remaining = cur.fetchone()[0]

    # Skipped count
    cur.execute("SELECT COUNT(*) FROM ANNOTATION WHERE verification_status = 'SKIPPED'")
    total_skipped = cur.fetchone()[0]

    # Annotator breakdown with 5 metrics
    cur.execute("""
        SELECT
            human_annotator_id,
            SUM(CASE WHEN verification_status = 'VERIFIED' THEN 1 ELSE 0 END) AS verified,
            SUM(CASE WHEN verification_status = 'CORRECTED' THEN 1 ELSE 0 END) AS corrected,
            SUM(CASE WHEN verification_status = 'REJECTED' THEN 1 ELSE 0 END) AS rejected,
            SUM(CASE WHEN verification_status = 'SKIPPED' THEN 1 ELSE 0 END) AS skipped,
            COUNT(*) AS total
        FROM ANNOTATION
        GROUP BY human_annotator_id
        ORDER BY total DESC
    """)
    annotator_stats = [dict(r) for r in cur.fetchall()]

    # Label distribution from verified human annotations
    cur.execute("""
        SELECT technique_label, COUNT(*) AS count
        FROM ANNOTATION
        WHERE verification_status != 'SKIPPED'
        GROUP BY technique_label
        ORDER BY count DESC
    """)
    human_labels_raw = dict(cur.fetchall())

    # Label distribution from model predictions
    cur.execute("""
        SELECT predicted_label, COUNT(*) AS count
        FROM LLM_PREANNOTATION
        GROUP BY predicted_label
        ORDER BY count DESC
    """)
    ai_labels_raw = dict(cur.fetchall())

    # Form label distribution combined list
    label_distribution = []
    for code, t in TECHNIQUES.items():
        human_cnt = human_labels_raw.get(code, 0)
        ai_cnt = ai_labels_raw.get(code, 0)
        label_distribution.append({
            "code": code,
            "name": t["name"],
            "human_count": human_cnt,
            "ai_count": ai_cnt,
        })

    completion_rate = round((total_annotated / total_preds * 100), 1) if total_preds > 0 else 0.0

    conn.close()

    return render_template(
        "admin.html",
        total_preds=total_preds,
        total_annotated=total_annotated,
        total_non_annotated=total_non_annotated,
        total_needs_review=total_needs_review,
        needs_review_remaining=needs_review_remaining,
        total_skipped=total_skipped,
        completion_rate=completion_rate,
        annotator_stats=annotator_stats,
        label_distribution=label_distribution,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "True").lower() in ("true", "1")
    print(f"Starting Bangla Meme Propaganda Annotation UI on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)

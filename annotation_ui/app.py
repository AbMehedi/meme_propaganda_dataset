import os
import sys
import sqlite3
import json
from flask import Flask, render_template, request, redirect, url_for, session, send_file, abort, jsonify

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


def get_confidence_meta(score, needs_review):
    if needs_review:
        return {
            "tier": "low",
            "label": "NEEDS REVIEW",
            "color": "var(--accent)",
            "badge_class": "badge-low",
            "pct": int((score or 0.5) * 100),
        }
    val = score if score is not None else 0.5
    pct = int(val * 100)
    if val >= 0.85:
        return {
            "tier": "high",
            "label": "HIGH CONFIDENCE",
            "color": "var(--conf-high)",
            "badge_class": "badge-high",
            "pct": pct,
        }
    elif val >= 0.65:
        return {
            "tier": "mid",
            "label": "MED CONFIDENCE",
            "color": "var(--conf-mid)",
            "badge_class": "badge-mid",
            "pct": pct,
        }
    else:
        return {
            "tier": "low",
            "label": "LOW CONFIDENCE",
            "color": "var(--accent)",
            "badge_class": "badge-low",
            "pct": pct,
        }


@app.context_processor
def inject_global_data():
    annotator_id = session.get("annotator_id")
    verified_count = 0
    total_count = 0
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM LLM_PREANNOTATION")
        total_count = cur.fetchone()[0]
        if annotator_id:
            cur.execute(
                "SELECT COUNT(DISTINCT llm_preannotation_id) FROM ANNOTATION WHERE human_annotator_id = ?",
                (annotator_id,),
            )
            verified_count = cur.fetchone()[0]
        conn.close()
    except Exception:
        pass
    return {
        "current_annotator": annotator_id,
        "verified_count": verified_count,
        "total_count": total_count,
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
    JOIN POST p ON llp.post_id = p.post_id
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

    conn.commit()
    conn.close()

    # Advance to next unverified item
    return redirect(url_for("annotate"))


@app.route("/adjudicate")
def adjudicate():
    """Phase 2 route placeholder."""
    return render_template(
        "base.html",
        custom_content="<div style='padding: 4rem 0;'><span class='label-mono'>PHASE 2</span><h1 style='font-size:3rem; margin:1rem 0;'>ADJUDICATION QUEUE</h1><p style='color:var(--muted-fg);'>Adjudication module activates when cross-annotator disagreements are flagged.</p><br><a href='/annotate' class='btn-primary'>Return to Annotation &rarr;</a></div>"
    )


@app.route("/admin")
def admin():
    """Phase 3 route placeholder with key summary stats."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM LLM_PREANNOTATION")
    total_preds = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM ANNOTATION WHERE verification_status != 'SKIPPED'")
    total_verified = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM ANNOTATION WHERE verification_status = 'SKIPPED'")
    total_skipped = cur.fetchone()[0]
    cur.execute("SELECT human_annotator_id, COUNT(*) as cnt FROM ANNOTATION GROUP BY human_annotator_id")
    annotator_stats = [dict(r) for r in cur.fetchall()]
    conn.close()

    return render_template(
        "admin.html",
        total_preds=total_preds,
        total_verified=total_verified,
        total_skipped=total_skipped,
        annotator_stats=annotator_stats,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "True").lower() in ("true", "1")
    print(f"Starting Bangla Meme Propaganda Annotation UI on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)

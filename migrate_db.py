"""
migrate_db.py
Adds the LLM_PREANNOTATION and ANNOTATION tables to propaganda_dataset.db.
Safe to run multiple times (uses CREATE TABLE IF NOT EXISTS).
"""
import sqlite3

DB_PATH = "propaganda_dataset.db"

SQL = """
CREATE TABLE IF NOT EXISTS LLM_PREANNOTATION (
    llm_annotation_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id            TEXT NOT NULL,
    image_id           TEXT,
    model_name         TEXT NOT NULL,
    prompt_version     TEXT NOT NULL,
    run_id             INTEGER NOT NULL DEFAULT 1,
    predicted_label    TEXT NOT NULL,
    modality           TEXT NOT NULL,
    confidence_score   REAL,
    rationale_span     TEXT,
    reasoning          TEXT,
    raw_response       TEXT,
    needs_review       INTEGER DEFAULT 0,
    review_reason      TEXT,
    overall_confidence REAL,
    created_at         TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (post_id) REFERENCES POST(post_id)
);

CREATE TABLE IF NOT EXISTS ANNOTATION (
    annotation_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id              TEXT NOT NULL,
    image_id             TEXT,
    technique_label      TEXT NOT NULL,
    modality             TEXT NOT NULL,
    start_char           INTEGER,
    end_char             INTEGER,
    evidence_span        TEXT,
    annotation_source    TEXT NOT NULL DEFAULT 'llm_preannotated',
    verification_status  TEXT NOT NULL DEFAULT 'PENDING',
    human_annotator_id   TEXT,
    adjudication_status  TEXT DEFAULT 'NONE',
    llm_preannotation_id INTEGER,
    created_at           TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (post_id) REFERENCES POST(post_id),
    FOREIGN KEY (llm_preannotation_id) REFERENCES LLM_PREANNOTATION(llm_annotation_id)
);
"""

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SQL)
    conn.commit()

    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    print("All tables:", tables)
    print("Migration complete!")
    conn.close()

if __name__ == "__main__":
    main()

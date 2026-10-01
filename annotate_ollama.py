"""
annotate_ollama.py — Bangla Meme Propaganda HITL Pre-Annotator (Ollama/Local)
=============================================================================
Hardware-adaptive: auto-selects the best model for your machine's RAM/VRAM.

Requirements:
    1. Ollama installed and running  ->  https://ollama.com/download
    2. Model pulled                  ->  ollama pull <model>
    3. Python SDK installed          ->  py -3 -m pip install ollama

Usage:
    py -3 annotate_ollama.py                     # annotate all unprocessed posts
    py -3 annotate_ollama.py --auto              # auto-detect hardware, pick best model
    py -3 annotate_ollama.py --limit 5           # annotate only 5 posts
    py -3 annotate_ollama.py --dry-run           # print prompts, no model calls
    py -3 annotate_ollama.py --model qwen2.5:7b  # manually override model
    py -3 annotate_ollama.py --runs 3            # 3 runs per post (uncertainty scoring)
    py -3 annotate_ollama.py --info              # show hardware info and recommended model, then exit
"""

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request

# Fix Windows console encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ──────────────────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────────────────
DB_PATH = "propaganda_dataset.db"
DEFAULT_MODEL = "qwen2.5:3b"
PROMPT_VERSION = "v1.0-ollama"
TEMPERATURE = 0.1   # low for deterministic structured output
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

# ──────────────────────────────────────────────────────────────────────────────
# JSON SCHEMA — enforced at token level by Ollama
# ──────────────────────────────────────────────────────────────────────────────
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "labels": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string", "enum": ["T01", "T02", "T03", "T04", "T05", "T06", "T07", "T08"]},
                    "modality": {"type": "string", "enum": ["M1", "M2", "M3"]},
                    "confidence_score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "rationale_span": {"type": ["string", "null"]},
                    "reasoning": {"type": "string"}
                },
                "required": ["label", "modality", "confidence_score", "reasoning"]
            },
            "minItems": 1
        },
        "overall_confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "needs_review": {"type": "boolean"},
        "review_reason": {"type": ["string", "null"]}
    },
    "required": ["labels", "overall_confidence", "needs_review", "review_reason"]
}

# ──────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT (codebook embedded — v1.0)
# ──────────────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an expert propaganda analyst specializing in Bangla-language social media memes.
Detect propaganda techniques using the strict codebook below.

You receive:
  - OCR_TEXT: full reconstructed text from the meme (Bangla / English / Banglish)
  - CAPTION: Facebook post caption (may be empty)
  - ALT_TEXT: Facebook auto-generated image description (may be empty)

TAXONOMY — use EXACTLY these codes:
  T01 Loaded Language         : Emotionally charged words provoking approval/disapproval
  T02 Name Calling / Labeling : TARGET + DEROGATORY LABEL explicitly present
  T03 Smears                  : TARGET + SPECIFIC NEGATIVE CLAIM + REPUTATIONAL DAMAGE
  T04 Appeal to Fear/Prejudice: Deliberate THREAT / DANGER / FEAR / PREJUDICE construction
  T05 Exaggeration/Minimisation: Substantial overstatement OR downplay of fact/event
  T06 Slogans                 : Short rallying phrase substituting for reasoning
  T07 Appeal to Strong Emotions: Intense NON-FEAR emotion deliberately provoked
  T08 No Propaganda Technique : None of T01-T07 apply

MODALITY:
  M1 TEXT  — technique evident from OCR text alone
  M2 IMAGE — technique evident from image alone
  M3 BOTH  — text AND image together construct the technique

STRICT RULES:
1. Evaluate ALL 7 techniques independently. Do not stop at the first match.
2. T08 is used ALONE — never combine T08 with T01-T07.
3. T01 is catch-all — use ONLY when charged language does not fit T02-T07.
4. T02 requires explicit TARGET + DEROGATORY LABEL.
5. T03 requires explicit TARGET + SPECIFIC NEGATIVE CLAIM.
6. T04 requires a deliberately constructed THREAT or FEAR.
7. T05 requires clear evidence of substantial overstatement or downplay.
8. T06 requires a short, catchy, rallying phrase substituting for reasoning.
9. T07 requires intense NON-FEAR emotion (rage, pity, pride, hatred, admiration).
10. Do NOT infer author intent. Label only what is observably present.
11. Do NOT fact-check. Label based on propagandistic presentation.
12. Political content alone != propaganda. Criticism alone != propaganda.
13. Banglish text: annotate normally.
14. If confidence_score is below 0.75, or if you cannot determine the technique with certainty, or if context is ambiguous: MUST set needs_review=true and provide an explicit review_reason string.

CONFIDENCE SCORES:
  0.90-1.0 : Strong unambiguous evidence
  0.75-0.89: Clear with minor nuance
  0.50-0.74: Uncertain, needs human verification — set needs_review=true
  <0.50    : Highly ambiguous or insufficient evidence — set needs_review=true

EXAMPLES:

Example 1 - Name Calling (T02):
OCR: "এই দালাল সরকার দেশ বেচে দিচ্ছে"
-> labels: [{label:T02, modality:M1, confidence_score:0.95, rationale_span:"দালাল সরকার", reasoning:"Derogatory label (দালাল) applied to government as target."}]

Example 2 - No Propaganda (T08):
OCR: "আজ সংসদে নতুন বাজেট পেশ হয়েছে।"
-> labels: [{label:T08, modality:M1, confidence_score:0.92, rationale_span:null, reasoning:"Neutral factual statement, no propaganda technique present."}]

Example 3 - Loaded Language + Fear (T01 + T04):
OCR: "এই ভয়ংকর সরকার ক্ষমতায় থাকলে দেশ শেষ হয়ে যাবে!"
-> labels: [
     {label:T01, modality:M1, confidence_score:0.88, rationale_span:"ভয়ংকর সরকার", reasoning:"Emotionally charged adjective provoking negative perception."},
     {label:T04, modality:M1, confidence_score:0.91, rationale_span:"দেশ শেষ হয়ে যাবে", reasoning:"Existential threat deliberately constructed."}
   ]

Return ONLY valid JSON matching the required schema. No preamble or explanation outside the JSON."""


# ──────────────────────────────────────────────────────────────────────────────
# DATABASE HELPERS
# ──────────────────────────────────────────────────────────────────────────────
def get_unprocessed_posts(conn, limit=None, model_name=None):
    sql = """
        SELECT p.post_id, p.caption,
               i.image_id, i.reconstructed_text, i.fb_alt_text, i.file_path
        FROM POST p
        LEFT JOIN IMAGE i ON p.post_id = i.post_id
        WHERE p.post_id NOT IN (
            SELECT DISTINCT post_id FROM LLM_PREANNOTATION
            WHERE prompt_version = ? AND model_name = ?
        )
    """
    params = [PROMPT_VERSION, model_name or DEFAULT_MODEL]
    if limit:
        sql += " LIMIT ?"
        params.append(limit)
    return conn.execute(sql, params).fetchall()


def store_preannotation(conn, post_id, image_id, run_id, model_name, raw_json_str):
    try:
        data = json.loads(raw_json_str)
    except json.JSONDecodeError as e:
        print(f"    [!] JSON parse error: {e}")
        return 0

    labels = data.get("labels", [])
    if not labels:
        print("    [!] Empty labels list in response.")
        return 0

    cur = conn.cursor()
    inserted = 0
    for item in labels:
        cur.execute("""
            INSERT INTO LLM_PREANNOTATION
              (post_id, image_id, model_name, prompt_version, run_id,
               predicted_label, modality, confidence_score,
               rationale_span, reasoning, raw_response,
               needs_review, review_reason, overall_confidence)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            post_id,
            image_id,
            model_name,
            PROMPT_VERSION,
            run_id,
            item.get("label", "UNKNOWN"),
            item.get("modality", "M1"),
            item.get("confidence_score"),
            item.get("rationale_span"),
            item.get("reasoning"),
            raw_json_str,
            1 if data.get("needs_review") else 0,
            data.get("review_reason"),
            data.get("overall_confidence"),
        ))
        inserted += 1

    conn.commit()
    return inserted


# ──────────────────────────────────────────────────────────────────────────────
# OLLAMA CALL
# ──────────────────────────────────────────────────────────────────────────────
def build_user_message(post_id, ocr_text, caption, alt_text):
    return f"""POST_ID: {post_id}

OCR_TEXT:
{ocr_text or '(no OCR text available)'}

CAPTION:
{caption or '(no caption)'}

ALT_TEXT:
{alt_text or '(no alt text)'}"""


def is_vision_model(model_name):
    """Check if model supports multimodal image input."""
    name = (model_name or "").lower()
    return any(k in name for k in ["llava", "vision", "moondream", "minicpm", "-vl", "vl:"])


def call_ollama(client, model_name, user_message, image_path=None):
    """Call Ollama with JSON schema enforcement, passing image if model is vision-capable."""
    user_msg_dict = {"role": "user", "content": user_message}
    if image_path and os.path.exists(image_path) and is_vision_model(model_name):
        user_msg_dict["images"] = [image_path]

    response = client.chat(
        model=model_name,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            user_msg_dict,
        ],
        format=OUTPUT_SCHEMA,
        options={
            "temperature": TEMPERATURE,
            "num_predict": 350,
        },
    )
    return response.message.content


def check_ollama_running():
    """Check if Ollama service is reachable."""
    try:
        urllib.request.urlopen(OLLAMA_HOST, timeout=3)
        return True
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def check_model_available(client, model_name):
    """Check if the model is already pulled."""
    try:
        models = client.list()
        available = [m.model for m in models.models]
        return any(model_name in m for m in available)
    except (AttributeError, KeyError, OSError, RuntimeError):
        return False


# ──────────────────────────────────────────────────────────────────────────────
# HARDWARE DETECTION & AUTO MODEL SELECTION
# ──────────────────────────────────────────────────────────────────────────────

# Model tier definitions: (model_name, min_free_ram_gb, min_vram_gb, description)
MODEL_TIERS = [
    # (model,              min_sys_ram, min_vram, label)
    ("qwen2.5:14b", 14.0, 10.0, "Best quality text — RTX 10-12GB+ VRAM"),
    ("qwen2.5:7b", 7.0, 5.0, "Good balance text  — RTX 6-8GB+ VRAM"),
    ("llava-phi3", 6.0, 3.5, "Multimodal Vision  — RTX 4GB+ VRAM (image + text)"),
    ("qwen2.5:3b", 3.0, 0.0, "Lightweight text   — CPU-only or low RAM"),
]


def get_system_info():
    """
    Returns (total_ram_gb, free_ram_gb, vram_gb, gpu_name).
    Works on Windows via WMI/psutil; falls back gracefully.
    """
    # --- System RAM ---
    try:
        import psutil
        mem = psutil.virtual_memory()
        total_ram_gb = mem.total / 1e9
        free_ram_gb = mem.available / 1e9
    except ImportError:
        # Fallback: use WMI via PowerShell
        try:
            out = subprocess.check_output(
                ["powershell", "-Command",
                 "(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory"],
                timeout=5, text=True
            ).strip()
            free_ram_gb = int(out) / 1024 / 1024  # KB -> GB
            out2 = subprocess.check_output(
                ["powershell", "-Command",
                 "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory"],
                timeout=5, text=True
            ).strip()
            total_ram_gb = int(out2) / 1e9
        except (subprocess.SubprocessError, OSError, ValueError):
            total_ram_gb, free_ram_gb = 0.0, 0.0

    # --- GPU VRAM (NVIDIA only via nvidia-smi) ---
    vram_gb = 0.0
    gpu_name = "Unknown GPU"
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            timeout=5, text=True
        ).strip().splitlines()[0]
        parts = out.split(",")
        gpu_name = parts[0].strip()
        vram_gb = int(parts[1].strip()) / 1024  # MiB -> GiB
    except (FileNotFoundError, subprocess.CalledProcessError, IndexError, ValueError):
        # No NVIDIA GPU or nvidia-smi not in PATH
        pass

    return total_ram_gb, free_ram_gb, vram_gb, gpu_name


def auto_select_model():
    """Detect hardware and return the recommended Ollama model name."""
    total_ram, free_ram, vram, gpu_name = get_system_info()

    print("  Hardware detected:")
    print(f"    System RAM : {total_ram:.1f} GB total, {free_ram:.1f} GB free")
    if vram > 0:
        print(f"    GPU        : {gpu_name}")
        print(f"    VRAM       : {vram:.1f} GB")
    else:
        print("    GPU        : No NVIDIA GPU detected (CPU-only inference)")
    print()

    # Walk tiers from best to smallest
    for model, min_ram, min_vram, desc in MODEL_TIERS:
        has_gpu = (min_vram > 0) and (vram >= min_vram)
        has_cpu = (min_vram == 0) and (vram == 0)
        has_ram = (free_ram >= min_ram) or (total_ram >= min_ram)

        if (has_gpu or has_cpu) and has_ram:
            print(f"  [AUTO] Selected: {model}")
            print(f"         Reason  : {desc}")
            print()
            return model

    # Absolute fallback
    print("  [AUTO] Selected: qwen2.5:3b")
    print("         Reason  : Fallback (minimum viable)")
    return "qwen2.5:3b"


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Ollama Local LLM Pre-Annotator for Bangla Meme Propaganda",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Hardware tiers:
  qwen2.5:3b   -- CPU-only, 6GB RAM          (your laptop)
  qwen2.5:7b   -- RTX 6-8GB VRAM / 10GB RAM  (team RTX)
  qwen2.5:14b  -- RTX 10-12GB VRAM           (team mid-high RTX)
"""
    )
    parser.add_argument("--model", default=None, help="Ollama model to use (overrides --auto)")
    parser.add_argument("--auto", action="store_true", help="Auto-detect hardware and pick best model")
    parser.add_argument("--info", action="store_true", help="Show hardware info and recommended model, then exit")
    parser.add_argument("--limit", type=int, default=None, help="Max posts to process")
    parser.add_argument("--runs", type=int, default=1, help="Number of runs per post (default: 1)")
    parser.add_argument("--dry-run", action="store_true", help="Print prompts without calling model")
    args = parser.parse_args()

    # ── Hardware detection ───────────────────────────────────────────────────
    sep = "=" * 62
    print(f"\n{sep}")
    print("  Bangla Meme Propaganda -- Ollama Pre-Annotator")
    print(f"{sep}\n")

    if args.info:
        auto_select_model()
        print("Tip: pull the model with:  ollama pull <model-name>")
        return

    if args.auto or args.model is None:
        selected_model = auto_select_model()
        # --model overrides --auto
        model_name = args.model if args.model else selected_model
    else:
        model_name = args.model

    print(f"  Model: {model_name}  |  Prompt: {PROMPT_VERSION}  |  Runs: {args.runs}")
    print()

    # ── Pre-flight checks ────────────────────────────────────────────────────
    if not args.dry_run:
        if not check_ollama_running():
            print("[ERROR] Ollama is not running.")
            print("  1. Make sure Ollama is installed: https://ollama.com/download")
            print("  2. Start it: just open the Ollama app, or run: ollama serve")
            sys.exit(1)

        try:
            import ollama as ollama_sdk
            client = ollama_sdk.Client(host=OLLAMA_HOST)
        except ImportError:
            print("[ERROR] ollama Python SDK not installed.")
            print("  Run: py -3 -m pip install ollama")
            sys.exit(1)

        if not check_model_available(client, model_name):
            print(f"[ERROR] Model '{model_name}' is not pulled yet.")
            print(f"  Run: ollama pull {model_name}")
            sys.exit(1)
    else:
        client = None

    # ── Load posts ───────────────────────────────────────────────────────────
    conn = sqlite3.connect(DB_PATH)
    posts = get_unprocessed_posts(conn, limit=args.limit, model_name=model_name)

    if not posts:
        print(f"[INFO] No unprocessed posts found for model='{model_name}', prompt='{PROMPT_VERSION}'.")
        print("       All posts have already been annotated with this model/prompt combination.")
        conn.close()
        return

    print(f"  Posts to process: {len(posts)}")
    if args.dry_run:
        print("  *** DRY RUN -- no model calls will be made ***\n")

    # ── Annotate ─────────────────────────────────────────────────────────────
    total_labels = 0
    for idx, (post_id, caption, image_id, reconstructed_text, fb_alt_text, file_path) in enumerate(posts, 1):
        short_id = post_id[:30] + "..."
        print(f"[{idx}/{len(posts)}] {short_id}")

        user_msg = build_user_message(post_id, reconstructed_text, caption, fb_alt_text)

        if args.dry_run:
            print("  --- PROMPT PREVIEW ---")
            print(user_msg[:500])
            if file_path and is_vision_model(model_name):
                print(f"  [VISION IMAGE ATTACHED]: {file_path}")
            print("  ---\n")
            continue

        for run_id in range(1, args.runs + 1):
            run_label = f" (run {run_id}/{args.runs})" if args.runs > 1 else ""
            try:
                raw = call_ollama(client, model_name, user_msg, image_path=file_path)
                inserted = store_preannotation(conn, post_id, image_id, run_id, model_name, raw)
                total_labels += inserted

                # Display result
                try:
                    parsed = json.loads(raw)
                    labels_str = ", ".join(
                        f"{lbl['label']}({lbl.get('modality', '?')}, {lbl.get('confidence_score', 0):.2f})"
                        for lbl in parsed.get("labels", [])
                    )
                    review = " [NEEDS REVIEW]" if parsed.get("needs_review") else ""
                    print(f"  -> {labels_str}{review}{run_label}")
                except (json.JSONDecodeError, KeyError, TypeError):
                    print(f"  -> (raw: {raw[:100]})")

            except (RuntimeError, ValueError, OSError) as e:
                print(f"  [!] Error on run {run_id}: {e}")

    conn.close()

    if not args.dry_run:
        sep = "=" * 62
        print(f"\n{sep}")
        print(f"  Done! {total_labels} label(s) stored in LLM_PREANNOTATION.")
        print("  Run: py -3 view_results.py")
        print(f"{sep}\n")


if __name__ == "__main__":
    main()

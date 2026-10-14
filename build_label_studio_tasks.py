#!/usr/bin/env python3
"""Build a reproducible CampNet pilot and two Label Studio import files.

Only stdlib is required. The frozen manifest and DB are read-only.
"""
import argparse
import csv
import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote


def csv_rows(path):
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fields):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def select_pilot(manifest, output, count):
    rows = csv_rows(manifest)
    frequency = Counter(r["post_id"] for r in rows)
    # One image per post under the present codebook. Do not silently pick one
    # photo from a gallery or create multiple examples from the same post.
    eligible = [r for r in rows if r["readable"] == "1" and frequency[r["post_id"]] == 1]
    buckets = defaultdict(list)
    for row in eligible:
        buckets[row["source_key"]].append(row)
    for source in buckets:
        buckets[source].sort(key=lambda r: (r["timestamp_utc"], r["image_id"]))
    sources = sorted(buckets)
    selected = []
    while len(selected) < count and any(buckets.values()):
        for source in sources:
            if buckets[source] and len(selected) < count:
                selected.append(buckets[source].pop(len(buckets[source]) // 2))
    fields = ["pilot_order", "image_id", "post_id", "relative_path", "source_key",
              "timestamp_utc", "caption_present", "sha256", "split_group"]
    audit = [dict(pilot_order=i, image_id=r["image_id"], post_id=r["post_id"],
                  relative_path=r["relative_path"], source_key=r["source_key"],
                  timestamp_utc=r["timestamp_utc"],
                  caption_present=int(bool(r["caption_clean"].strip())),
                  sha256=r["sha256"], split_group=r["split_group"])
             for i, r in enumerate(selected, 1)]
    write_csv(output, audit, fields)
    print(f"Selected {len(selected)} images from {len(set(r['source_key'] for r in selected))} sources; "
          f"{sum(not r['caption_clean'].strip() for r in selected)} without captions. "
          "Pilot source mix is provisional: visually review eligibility, satire and format before annotation.")


def build(manifest, pilot, images_root, ocr_csv, output_dir, preview=False, ocr_source="verified"):
    manifest_rows = {r["image_id"]: r for r in csv_rows(manifest)}
    pilot_rows = csv_rows(pilot)
    ocr_rows = csv_rows(ocr_csv)
    draft = preview or ocr_source == "draft"
    ocr_column = "ocr_draft" if draft else "ocr_corrected"
    ocr_status = "AUTHOR_VERIFICATION_PENDING" if draft else "AUTHOR_VERIFIED"
    ocr_values = {}
    for row in ocr_rows:
        key = row["image_id"]
        if key in ocr_values:
            raise ValueError(f"Duplicate OCR row for image_id {key}")
        ocr_values[key] = row[ocr_column]
    if not pilot_rows:
        raise ValueError("Pilot selection is empty")
    if len({r["image_id"] for r in pilot_rows}) != len(pilot_rows):
        raise ValueError("Duplicate image_id in pilot selection")
    a_tasks, b_tasks, errors = [], [], []
    base = Path(images_root).resolve()
    for selection in pilot_rows:
        image_id = selection["image_id"]
        if not draft and ocr_values.get(image_id, '').strip() == '#excluded':
            continue
        row = manifest_rows.get(image_id)
        if not row:
            errors.append(f"{image_id}: absent from manifest"); continue
        rel = Path(row["relative_path"])
        if rel.is_absolute() or ".." in rel.parts:
            errors.append(f"{image_id}: unsafe relative_path"); continue
        file_path = (base / rel).resolve()
        if not file_path.is_relative_to(base) or not file_path.is_file():
            errors.append(f"{image_id}: image missing at {file_path}"); continue
        digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
        if digest != row["sha256"]:
            errors.append(f"{image_id}: image checksum differs from freeze"); continue
        if image_id not in ocr_values:
            kind = "machine OCR draft" if draft else "author-reviewed OCR"
            errors.append(f"{image_id}: no {kind} row (empty string allowed)"); continue
        caption = row["caption_clean"]
        # Put only task content/IDs in annotator-facing data. Do not expose
        # source, URL, engagement, Facebook alt text, or future labels.
        common = {"item_id": image_id, "image_id": image_id,
                  "caption": caption, "ocr": ocr_values[image_id],
                  "ocr_status": ocr_status}
        a_tasks.append({"data": common.copy()})
        b_tasks.append({"data": {**common,
            "image": "/data/local-files/?d=" + quote(rel.as_posix(), safe="/")}})
    if errors:
        raise ValueError("Cannot build import files; fix these issues first:\n" + "\n".join(errors))
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, tasks in (("stage_a_text.json", a_tasks), ("stage_b_full_post.json", b_tasks)):
        (output_dir / name).write_text(json.dumps(tasks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if preview:
        config_root = Path(__file__).resolve().parent
        warning = '<Header value="PREVIEW ONLY: machine OCR is unverified. Do not treat these annotations as final."/>'
        for source, target in (("stage_a_text.xml", "stage_a_preview.xml"),
                               ("stage_b_full_post.xml", "stage_b_preview.xml")):
            config = (config_root / source).read_text(encoding="utf-8")
            config = config.replace("<View>", "<View>\n  " + warning, 1)
            (output_dir / target).write_text(config, encoding="utf-8")
    kind = "PREVIEW" if preview else ocr_status
    print(f"Wrote {len(a_tasks)} matching {kind} Stage A/B tasks to {output_dir}")
    print(f"Set LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT={base}")


def audit_ocr(pilot, draft_csv, reviewed_csv, output):
    def keyed(path, column):
        result = {}
        for row in csv_rows(path):
            key = row["image_id"]
            if key in result:
                raise ValueError(f"Duplicate image_id {key} in {path}")
            result[key] = row[column].strip()
        return result

    selected = [row["image_id"] for row in csv_rows(pilot)]
    draft = keyed(draft_csv, "ocr_draft")
    reviewed = keyed(reviewed_csv, "ocr_corrected")
    missing = [image_id for image_id in selected if image_id not in draft or image_id not in reviewed]
    if missing:
        raise ValueError("Missing OCR rows for selected images: " + ", ".join(missing))
    rows = [
        {"image_id": image_id, "changed": int(draft[image_id] != reviewed[image_id]),
         "ocr_draft": draft[image_id], "ocr_corrected": reviewed[image_id]}
        for image_id in selected
    ]
    write_csv(output, rows, ["image_id", "changed", "ocr_draft", "ocr_corrected"])
    print(f"Compared {len(rows)} images; {sum(row['changed'] for row in rows)} OCR values changed.")
    print(f"Review Stage A/B text spans and decisions for changed images: {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    pilot17 = sub.add_parser("pilot17", help="Build the fixed 17-image pilot from latest corrected OCR and explicit exclusions")
    pilot17.add_argument('--output-dir', type=Path, default=Path(__file__).resolve().parent / 'pilot_17')
    select = sub.add_parser("select", help="Create a provisional 20-image pilot audit list")
    select.add_argument("--manifest", type=Path, required=True)
    select.add_argument("--output", type=Path, required=True)
    select.add_argument("--count", type=int, default=20)
    build_cmd = sub.add_parser("build", help="Generate validated two-stage import JSON")
    for key in ("manifest", "pilot", "images-root", "output-dir"):
        build_cmd.add_argument("--" + key, type=Path, required=True)
    ocr_input = build_cmd.add_mutually_exclusive_group(required=True)
    ocr_input.add_argument("--ocr-csv", type=Path, help="Author-reviewed image text")
    ocr_input.add_argument("--ocr-draft-csv", type=Path,
                           help="Machine OCR draft; author verification remains pending")
    preview_cmd = sub.add_parser("preview", help="Generate separate, unverified OCR preview imports")
    for key in ("manifest", "pilot", "images-root", "ocr-draft-csv", "output-dir"):
        preview_cmd.add_argument("--" + key, type=Path, required=True)
    audit_cmd = sub.add_parser("audit-ocr", help="Compare later author-reviewed OCR against task OCR")
    for key in ("pilot", "ocr-draft-csv", "ocr-csv", "output"):
        audit_cmd.add_argument("--" + key, type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'pilot17':
        from campnet_pilot.build import build_pilot
        build_pilot(output=args.output_dir)
    elif args.command == "select":
        select_pilot(args.manifest, args.output, args.count)
    elif args.command == "build":
        draft = args.ocr_draft_csv is not None
        build(args.manifest, args.pilot, args.images_root,
              args.ocr_draft_csv if draft else args.ocr_csv, args.output_dir,
              ocr_source="draft" if draft else "verified")
    elif args.command == "preview":
        build(args.manifest, args.pilot, args.images_root, args.ocr_draft_csv, args.output_dir,
              preview=True)
    else:
        audit_ocr(args.pilot, args.ocr_draft_csv, args.ocr_csv, args.output)


if __name__ == "__main__":
    main()

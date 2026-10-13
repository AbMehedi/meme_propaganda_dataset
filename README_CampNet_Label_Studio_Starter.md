# CampNet: start annotating the frozen 406-image dataset

## Current 17-image pilot (14 October 2026)

The author-corrected OCR is now available. The current pilot uses the original
selection minus three explicit `#excluded` records: exactly 17 images. Use
`python build_label_studio_tasks.py pilot17` and follow
[the 17-image workflow](docs/PILOT_17_WORKFLOW.md), including the real Label Studio
configs, validated exports, independent manual annotation and separate experimental
model assistance. Results and remaining limitations are in
[the experimental report](pilot_17/EXPERIMENTAL_REPORT.md).

The instructions below describe the earlier 20-image draft workflow and are kept
for provenance. They are superseded for the current pilot.

This starter uses the **provided** `manifest.csv` and `camp_rg.db` as a read-only freeze. It does not update the database. The freeze has 406 readable image rows, 393 distinct posts, 16 sources, zero annotation rows and zero OCR rows. Four posts have multiple images (17 image rows total) and are kept out of this single-image pilot. The 20-item provisional audit list samples 16 sources and includes six posts with no caption. Recheck inclusion and format by looking at the actual images before giving the tasks to annotators.

**OCR verification is scheduled for later:** this local copy has `data/manifest.csv`, `data/images/...`, and an EasyOCR draft for the selected 20 images. The database's `ocr_run` still has zero rows. The Facebook `alt_text` field is generated description, sometimes paraphrased text, **not** verified OCR. The task builder can now use `ocr_draft_20.csv` to start annotation. It marks every task `AUTHOR_VERIFICATION_PENDING`; the author must compare the draft with each image later, then recheck annotations affected by OCR changes.

## Files in this starter

- `pilot_20_audit.csv`: provisional selection. Keep source and timestamps here for research audit; **do not show this file to annotators**. Change the rows if manual eligibility review finds a problem; preserve the manifest IDs.
- `ocr_corrections_template.csv`: the author later fills `image_id,ocr_corrected` for **all selected images**. An image with no readable text gets an empty OCR value only after visual review. Keep raw OCR and polygons separately in your preprocessing records.
- `build_label_studio_tasks.py`: verifies images against SHA-256 from the freeze and produces matching two-stage task files, or stops with actionable errors.
- `stage_a_text.xml` and `stage_b_full_post.xml`: configurations to paste into two Label Studio projects.
- `prepare_ocr_review.py`: runs Bengali/English EasyOCR and creates `ocr_draft_20.csv`, `ocr_raw_20.json` (including polygons), and `ocr_review_20.html`. The draft is not a reviewed correction file.

## 1. Put the image files in place

On your own computer, arrange files under a project directory as in the freeze:

```text
campnet/
  manifest.csv
  data/images/<image_id>.jpg
  CampNet_Label_Studio_Starter/
```

Here `campnet/` is the **images root**, and `data/images/...` is the path recorded by the manifest. You may instead point `--images-root` at another directory that contains that relative tree. Verify the first 20 images open; the builder also checks each file's SHA-256. If your archived images were transformed since the freeze, recover the original bytes or document/re-freeze the changed files, rather than bypassing the checksum check.

In this local copy, the starter directory itself contains `data/manifest.csv` and `data/images/`. Run the commands below from the starter directory and use `--images-root .`.

## 2. Prepare image text for annotation

The supplied `ocr_draft_20.csv` is a Bengali/English EasyOCR draft. It allows annotation to begin before author review, but contains recognition errors. Keep caption text separately: the script takes `caption_clean` from `manifest.csv`. The raw predictions and polygons are in `ocr_raw_20.json` for later text masking and grounding.

Later, the author should save the completed review as `ocr_corrected_20.csv`, with one row for every `image_id` in the pilot list. Do not put a literal `NA` in an image with no text; leave the field empty after visual review.

When the author is ready, open `ocr_review_20.html` to compare each pilot image with its EasyOCR draft. Correct every field and check each image as reviewed. The download button is enabled after all 20 are checked; save the downloaded `ocr_corrected_20.csv` beside this README. If you need to regenerate the draft, run `.\.ocr-venv\Scripts\python.exe .\prepare_ocr_review.py` after installing `easyocr` in `.ocr-venv`. Keep `ocr_raw_20.json` as the separate raw OCR and polygon record.

## 3. Generate tasks (Windows PowerShell example)

Open PowerShell in this starter directory and run:

```powershell
.\.venv\Scripts\python.exe .\build_label_studio_tasks.py build --manifest .\data\manifest.csv --pilot .\pilot_20_audit.csv --images-root . --ocr-draft-csv .\ocr_draft_20.csv --output-dir .\imports
```

This creates `imports/stage_a_text.json` and `imports/stage_b_full_post.json` with `ocr_status=AUTHOR_VERIFICATION_PENDING`. The image URLs refer to the files beneath the **same absolute** images root from `--images-root`. If any images or OCR draft rows are missing, the script stops and does not write a partial task set. Do not annotate from the audit CSV, post URL or generated `alt_text`.

After the author later creates `ocr_corrected_20.csv`, compare it with the imported OCR using:

```powershell
.\.venv\Scripts\python.exe .\build_label_studio_tasks.py audit-ocr --pilot .\pilot_20_audit.csv --ocr-draft-csv .\ocr_draft_20.csv --ocr-csv .\ocr_corrected_20.csv --output .\ocr_author_review_changes.csv
```

For each row marked `changed=1`, revisit its Stage A/B text spans, technique choices, and rationale before treating the annotation as gold. Label Studio does not automatically replace text in tasks already imported. Keep the original draft and both annotation exports for audit. A newly built JSON from `--ocr-csv .\ocr_corrected_20.csv` can be used for a fresh project if needed.

## 4. Start Label Studio on the same computer

Install using the [official Label Studio quick start](https://labelstud.io/guide/install). In this local copy, Label Studio is already installed in `.venv`. Start it from this directory in PowerShell with:

```powershell
$env:LABEL_STUDIO_LOCAL_FILES_SERVING_ENABLED = 'true'
$env:LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT = (Resolve-Path .).Path
.\.venv\Scripts\label-studio.exe start --port 8081 --no-browser
```

Open `http://localhost:8081`. The document root must resolve to the same starter directory passed to `--images-root`, **on the computer running Label Studio**. The generated image references look like `/data/local-files/?d=data/images/<image_id>.jpg`. Test one image inside Stage B; if it fails to render, check your document root and file location before proceeding. [Local-file reference format](https://labelstud.io/guide/storage_local), [starting the server](https://labelstud.io/guide/start).

### Share Label Studio with teammates on the same LAN

On the host computer, run the included LAN launcher from this directory instead of the command above:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\start_label_studio_lan.ps1
```

It detects the host computer's Wi-Fi IPv4 address, serves the same local image files, and sets `LABEL_STUDIO_HOST` so Label Studio generates invitation links with that address. If you use a different network adapter, pass its IPv4 address with `-LanAddress 192.168.1.23` (replace this example with the current address). Keep the PowerShell window running while teammates annotate.

On this computer, Windows Firewall has an inbound TCP 8081 rule restricted to the local subnet. On another host, run `allow_label_studio_lan.ps1` once in an Administrator PowerShell window to create that rule. Teammates should connect to `http://<host-LAN-IP>:8081` while on the same LAN, then use a newly copied invitation link from **Organization → Add Members**. A link containing `127.0.0.1` or `localhost` points to the teammate's own computer and will fail. The host's IPv4 address can change after reconnecting to Wi-Fi; use the address printed by the launcher each time. See Label Studio's [server host setting](https://labelstud.io/guide/start) and [member invitation instructions](https://labelstud.io/guide/signup).

Label Studio 1.23.2 also requires a **Local Files source storage connection in each project that displays images**. In the Stage B project, open **Settings → Cloud Storage → Add Source Storage → Local Files**. Set **Absolute local path** to this starter directory's `data\images` folder, choose **Import Method: Tasks**, and click **Save** without syncing. The JSON import already created the tasks; syncing the image folder would create unwanted additional tasks. The source storage grants that project access to the `/data/local-files/?d=data/images/...` URLs. See the [official local storage setup](https://labelstud.io/guide/storage_local).

If Label Studio runs in Docker or on another machine, mount the images into that server and set its document root to the mounted parent of `data/images/`. The JSON URL does not point back to the laptop that generated it. Follow the [official Docker/local-storage guide](https://labelstud.io/guide/start#Run-Label-Studio-on-Docker-and-use-Local-Storage).

## 5. Create two projects

1. Create **CampNet A — text only**. Under project settings, choose custom labeling setup and paste `stage_a_text.xml`. Import `imports/stage_a_text.json` as JSON tasks; **do not import the CSV directly**.
2. Create **CampNet B — full post**. Paste `stage_b_full_post.xml`, import `imports/stage_b_full_post.json`, and add the Local Files source storage described above. Open one task and confirm the original image, caption and draft OCR match the same `image_id`; its OCR status should read `AUTHOR_VERIFICATION_PENDING`.
3. Give annotators Stage A first. Export their Stage A JSON and keep it as the frozen first decision **before** they see Stage B. Then assign the corresponding Stage B tasks. A separate project alone does not enforce a lock; control permissions/work assignment and keep immutable exports.
4. Each of two annotators submits an independent judgment; do not expose another person's results or preannotations during the pilot. An adjudicator later resolves disagreements. Label Studio exports are intermediate annotation records, not yet the final `CampNet_Annotation_Schema.json` research format.

The `Text` span labels identify exact words; the image rectangles are **technique-specific visual evidence**, not every object in the photo. For each selected final technique, enter one line in `instance_evidence`, e.g. `T03 | NON_TEXT_VISUAL | visual_contribution=REQUIRED | text_sufficient=false | target=depicted official | evidence=official shown taking donations`. Draw a T03 box around each necessary region and add a region note. For text-only T06, write `visual_contribution=NOT_USED`, and draw no visual box. Use no core checkboxes for `No Propaganda Technique`, set `COMPLETE`, and explain `NONE` in the note. Satire is assessed under the same evidence rules.

**Evidence limitation:** this starter captures core technique choices, text spans, boxes, region notes and structured instance text. It does **not** automatically verify that each selected technique has a complete contribution line or that text span offsets match the project JSON schema. Before any model training, export Label Studio's native JSON, map `item_id=image_id` and the Stage A/B decisions to the gold schema, convert image boxes from displayed percentages to normalized coordinates, inspect Unicode text offsets (emoji can require UTF-16 to code-point conversion), and validate the technique-to-box links. Save source IDs and duplicate groups in the audit/join file, not the annotator view.

## 6. After the first 20

Resolve codebook disagreements and OCR errors first, then extend the same process to ~80 additional single-image posts. Group images from the same post/content family together for later splits. Do not treat the current 20 as a random or label-balanced sample: its source diversity is automatic, but its actual technique/format mix requires manual inspection.
